"""The three commands: what they move, and what they refuse to move."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "project-hub" / "scripts" / "project_hub.py"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}

STUB_DOCTOR = '''
def doctor(target, stale_days=30):
    issues = [
        {"severity": "warning", "code": "stub", "path": "owners_window/notes.md"},
        {"severity": "warning", "code": "stub", "path": "global/SUMMARY.md"},
    ]
    return {"target": str(target), "status": "warning",
            "summary": {"errors": 0, "warnings": len(issues)}, "issues": issues}
'''

FAILING_DOCTOR = '''
def doctor(target, stale_days=30):
    issues = [{"severity": "error", "code": "stub-error", "path": "global/GOALS.md"}]
    return {"target": str(target), "status": "error",
            "summary": {"errors": 1, "warnings": 0}, "issues": issues}
'''

# Stands in for the Project Context initializer. The contract under test is the
# invocation, not the installer: this records how it was called and creates the
# marker the real one would.
STUB_INSTALLER = '''
import json, pathlib, sys
target = pathlib.Path(sys.argv[sys.argv.index("--target") + 1])
(target / "project-context").mkdir(parents=True, exist_ok=True)
(target / "project-context" / ".project-context.json").write_text(
    json.dumps({"schema": "project-context/1"}) + "\\n", encoding="utf-8")
(target / "installer-was-called.json").write_text(json.dumps(sys.argv[1:]), encoding="utf-8")
'''


def git(cwd: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=check, capture_output=True, text=True,
        env={**os.environ, **GIT_ENV},
    )
    return result.stdout.strip()


class HubCase(unittest.TestCase):
    """A throwaway Hub and a throwaway repository, side by side."""

    maxDiff = None

    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix="project-hub-test-"))
        self.addCleanup(shutil.rmtree, self.workspace, ignore_errors=True)
        self.hub = self.workspace / "hub"
        shutil.copytree(
            ROOT, self.hub,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        self.repo = self.workspace / "notes-api"

    # -- fixtures ---------------------------------------------------------

    def make_repo(self, *, installed: bool = False, branch: str = "main",
                  remote: bool = False) -> Path:
        self.repo.mkdir(parents=True, exist_ok=True)
        (self.repo / "src").mkdir(exist_ok=True)
        (self.repo / "src" / "main.py").write_text("def main():\n    return 0\n", encoding="utf-8")
        git(self.repo, "init", "-q", "-b", branch, ".")
        if installed:
            self.install_marker()
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "seed")
        if remote:
            # A bare repository on disk, wired up as `origin`. `push` now
            # completes the round trip, so tests that apply exercise the real
            # command rather than a rehearsal — and still touch no network.
            # Off by default: a local origin path is absolute, and the registry
            # would then hold one, which `test_no_absolute_path...` rightly
            # refuses. Real remotes are URLs, so only push-apply tests want it.
            self.origin = self.workspace / "origin.git"
            git(self.workspace, "init", "-q", "--bare", str(self.origin))
            git(self.repo, "remote", "add", "origin", str(self.origin))
            git(self.repo, "push", "-q", "--set-upstream", "origin", branch)
        return self.repo

    def origin_branches(self) -> set[str]:
        """Branch names that actually arrived in the bare origin."""
        out = subprocess.run(["git", "for-each-ref", "--format=%(refname:short)", "refs/heads/"],
                             cwd=self.origin, capture_output=True, text=True, check=False)
        return {line.strip() for line in out.stdout.splitlines() if line.strip()}

    def install_marker(self) -> None:
        context = self.repo / "project-context"
        context.mkdir(parents=True, exist_ok=True)
        (context / ".project-context.json").write_text(
            json.dumps({"schema": "project-context/1", "version": "0.7.0"}, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_global(self, name: str, text: str) -> None:
        (self.hub / "global" / name).write_text(text, encoding="utf-8")

    def write_blueprint(self, project_id: str, name: str, text: str) -> None:
        folder = self.hub / "projects" / project_id / "blueprint"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text, encoding="utf-8")

    def opt_in_global(self, *entries: str) -> None:
        """Add entries to this Hub's push.global_include, as an owner would."""
        marker = self.hub / ".project-hub.json"
        data = json.loads(marker.read_text(encoding="utf-8"))
        current = data.setdefault("push", {}).setdefault("global_include", [])
        for entry in entries:
            if entry not in current:
                current.append(entry)
        marker.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def seed_global(self) -> None:
        """Two filled global records, so there is something to push."""
        self.write_global("SUMMARY.md", "# Global\n\nWe build small tools that keep context.\n")
        self.write_global("GUARDRAILS.md", "# Guardrails\n\n- G-001 Never commit a credential.\n")

    def stub(self, name: str, source: str) -> Path:
        path = self.workspace / name
        path.write_text(source, encoding="utf-8")
        return path

    # -- runner -----------------------------------------------------------

    def run_cli(self, *args: str, expected: int | None = 0, stdin: str = "") -> dict:
        result = subprocess.run(
            [sys.executable, str(CLI), "--hub", str(self.hub), *args],
            check=False, capture_output=True, text=True, input=stdin,
            env={**os.environ, **GIT_ENV},
        )
        if expected is not None:
            self.assertEqual(expected, result.returncode, result.stdout + result.stderr)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail(f"non-JSON output:\n{result.stdout}\n{result.stderr}")

    def kinds(self, report: dict) -> dict[str, str]:
        return {Path(action["path"]).name: action["kind"] for action in report["actions"]}


class InitTests(HubCase):
    def test_dry_run_writes_nothing_and_apply_writes_the_mark(self) -> None:
        self.make_repo()
        dry = self.run_cli("init", str(self.repo), "--dry-run")
        self.assertEqual("notes-api", dry["project_id"])
        self.assertEqual({"create": 2}, dry["summary"])
        self.assertFalse((self.hub / "projects" / "notes-api").exists())

        installer = self.stub("installer.py", STUB_INSTALLER)
        report = self.run_cli("init", str(self.repo), "--apply", "--installer", str(installer),
                              "--no-push", "--skip-doctor", "--yes")
        mark = (self.hub / "projects" / "notes-api" / "MARK.md").read_text(encoding="utf-8")
        self.assertIn("Project id: `notes-api`", mark)
        self.assertIn("Python", mark)
        self.assertIn("`src/main.py`", mark)
        self.assertTrue((self.hub / "projects" / "notes-api" / "SUMMARY.md").is_file())
        self.assertIn("notes-api", (self.hub / "registry.md").read_text(encoding="utf-8"))
        self.assertTrue(report["install"]["ran"])
        called = json.loads((self.repo / "installer-was-called.json").read_text(encoding="utf-8"))
        self.assertIn("init", called)
        self.assertIn("--apply", called)

    def test_re_running_preserves_an_edited_mark(self) -> None:
        self.make_repo()
        installer = self.stub("installer.py", STUB_INSTALLER)
        self.run_cli("init", str(self.repo), "--apply", "--installer", str(installer),
                     "--no-push", "--skip-doctor", "--yes")
        mark = self.hub / "projects" / "notes-api" / "MARK.md"
        mark.write_text("# Mark — notes-api\n\nCorrected by the owner.\n", encoding="utf-8")
        # Project Context is now installed, so init refuses outright; that is
        # the stronger of the two guarantees and it fires first.
        report = self.run_cli("init", str(self.repo), "--dry-run", expected=2)
        self.assertTrue(any("already installed" in reason for reason in report["blocked"]))
        self.assertIn("Corrected by the owner", mark.read_text(encoding="utf-8"))

    def test_refused_when_project_context_is_already_installed(self) -> None:
        self.make_repo(installed=True)
        report = self.run_cli("init", str(self.repo), "--dry-run", expected=2)
        self.assertTrue(any("use `push` instead" in reason for reason in report["blocked"]))

    def test_refused_when_the_target_is_not_a_git_repository(self) -> None:
        plain = self.workspace / "plain"
        plain.mkdir()
        report = self.run_cli("init", str(plain), "--dry-run", expected=2)
        self.assertTrue(any("not a git repository" in reason for reason in report["blocked"]))

    def test_missing_installer_stops_at_the_install_step(self) -> None:
        self.make_repo()
        report = self.run_cli("init", str(self.repo), "--apply", "--installer",
                              str(self.workspace / "nope.py"), "--skip-doctor", "--yes", expected=3)
        self.assertFalse(report["install"]["ran"])
        self.assertIn("PROJECT_CONTEXT_INIT", report["install"]["reason"])
        # The mark it did write is correct and stays; nothing reached the repo.
        self.assertTrue((self.hub / "projects" / "notes-api" / "MARK.md").is_file())
        self.assertFalse((self.repo / "project-context").exists())


class PushAllowListTests(HubCase):
    def test_the_owners_window_is_never_sent(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        (self.hub / "owners_window" / "next-quarter.md").write_text(
            "# A half-formed idea\n", encoding="utf-8")
        report = self.run_cli("push", str(self.repo), "--dry-run")
        sent = [action["path"] for action in report["actions"]]
        self.assertFalse(any("owners_window" in path for path in sent))
        self.assertFalse(any("next-quarter" in path for path in sent))

    def test_readmes_owners_and_unfilled_seeds_are_skipped_with_a_reason(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        report = self.run_cli("push", str(self.repo), "--dry-run")
        skipped = {entry["path"]: entry["reason"] for entry in report["skipped"]}
        self.assertIn("global/skills/README.md", skipped)
        self.assertIn("README", skipped["global/skills/README.md"])
        self.assertIn("global/WORKFLOWS.md", skipped)
        self.assertIn("seed", skipped["global/WORKFLOWS.md"])
        sent = " ".join(action["path"] for action in report["actions"])
        self.assertNotIn("OWNERS.md", sent)

    def test_identity_is_never_pushed_even_when_the_marker_asks(self) -> None:
        """Decision D9: identity never reaches a project repo, at any setting."""
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        self.write_global("IDENTITY.md", "# Identity\n\nWe write plainly.\n")
        self.opt_in_global("IDENTITY.md")
        report = self.run_cli("push", str(self.repo), "--dry-run")
        sent = " ".join(action["path"] for action in report["actions"])
        self.assertNotIn("IDENTITY.md", sent)

    def test_only_named_entries_leave_global(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        (self.hub / "global" / "drafts").mkdir()
        (self.hub / "global" / "drafts" / "idea.md").write_text("# Not on the list\n", encoding="utf-8")
        report = self.run_cli("push", str(self.repo), "--dry-run")
        self.assertFalse(any("drafts" in action["path"] for action in report["actions"]))

    def test_a_blueprint_readme_is_skipped_like_a_global_one(self) -> None:
        """`docs/CLI.md` says the blueprint is sent "minus the same two
        filters", and for a while only the unfilled-seed one ran. A README in
        a blueprint folder explains the folder to the owner who wrote it; it
        has no more business in someone else's checkout than a README in
        `global/` does, and a project repository may have collaborators
        outside the organisation."""
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        self.write_blueprint("notes-api", "EPIC.md", "# Epic\n\n- **E-001 — One store.**\n")
        self.write_blueprint("notes-api", "README.md", "# What this folder is for\n\nNotes to myself.\n")
        report = self.run_cli("push", str(self.repo), "--dry-run")
        sent = [action["path"] for action in report["actions"]]
        self.assertTrue(any(path.endswith("project-context/blueprint/EPIC.md") for path in sent))
        self.assertFalse(any(path.endswith("blueprint/README.md") for path in sent))
        skipped = {entry["path"]: entry["reason"] for entry in report["skipped"]}
        self.assertIn("blueprint/README.md", skipped)
        self.assertIn("README", skipped["blueprint/README.md"])

    def test_blueprint_is_sent_and_lands_under_project_context(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        self.write_blueprint("notes-api", "EPIC.md", "# Epic\n\n- **E-001 — One store.**\n")
        report = self.run_cli("push", "notes-api", "--dry-run") if False else \
            self.run_cli("push", str(self.repo), "--dry-run")
        paths = [action["path"] for action in report["actions"]]
        self.assertTrue(any(path.endswith("project-context/blueprint/EPIC.md") for path in paths))


class PushBudgetTests(HubCase):
    def test_an_over_budget_file_is_refused_and_named(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        self.opt_in_global("GOALS.md")
        self.write_global("GOALS.md", "# Goals\n\n" + "word " * 500)
        report = self.run_cli("push", str(self.repo), "--dry-run", expected=2)
        self.assertTrue(any("global/GOALS.md" in reason for reason in report["blocked"]))
        self.assertTrue(any("trim" in reason for reason in report["blocked"]))
        over = {finding["path"] for finding in report["budget"]["over"]}
        self.assertIn("global/GOALS.md", over)

    def test_the_whole_subset_has_a_ceiling_that_names_what_to_trim_first(self) -> None:
        self.make_repo(installed=True)
        self.opt_in_global("GOALS.md", "RESOURCES.md")
        for name in ("WORKFLOWS.md", "GOALS.md", "RESOURCES.md", "GUARDRAILS.md", "SUMMARY.md"):
            self.write_global(name, "# T\n\n" + "word " * 399)
        report = self.run_cli("push", str(self.repo), "--dry-run", expected=2)
        total = next(f for f in report["budget"]["over"] if f["path"] == "global/")
        self.assertGreater(total["words"], total["limit"])
        self.assertTrue(total["trim_first"])

    def test_frontmatter_and_code_do_not_count_against_the_budget(self) -> None:
        self.make_repo(installed=True)
        fence = "```\n" + "code " * 500 + "\n```\n"
        self.write_global("SUMMARY.md", "---\nid: C-1\n---\n\n# S\n\nShort.\n" + fence)
        report = self.run_cli("push", str(self.repo), "--dry-run")
        self.assertEqual([], report["budget"]["over"])


class PushConflictTests(HubCase):
    def push_once(self) -> dict:
        self.seed_global()
        return self.run_cli("push", str(self.repo), "--apply", "--yes", "--skip-doctor")

    def test_apply_commits_and_pushes_the_sync_branch(self) -> None:
        self.make_repo(installed=True, remote=True)
        report = self.push_once()
        gate = report["gate"]
        self.assertTrue(gate["applied"])
        self.assertTrue(gate["committed"])
        self.assertTrue(gate["pushed"])
        self.assertEqual("hub-sync", gate["branch"])
        self.assertNotEqual("main", gate["branch"])
        # It reached the bare origin, and left the default branch alone.
        self.assertIn("hub-sync", self.origin_branches())
        self.assertEqual(gate["branch"], git(self.repo, "rev-parse", "--abbrev-ref", "HEAD"))
        self.assertIn("Source-Commit:", git(self.repo, "log", "-1", "--format=%B"))
        self.assertTrue((self.repo / "project-context" / "global" / "GUARDRAILS.md").is_file())

    def test_a_second_sync_stacks_a_commit_on_the_same_branch(self) -> None:
        """One long-lived branch, so an open pull request keeps its place."""
        self.make_repo(installed=True, remote=True)
        self.push_once()
        first = git(self.repo, "rev-parse", "HEAD")
        self.write_global("GUARDRAILS.md", "# Guardrails\n\nA second revision.\n")
        report = self.run_cli("push", str(self.repo), "--apply", "--yes", "--skip-doctor")
        self.assertEqual("hub-sync", report["gate"]["branch"])
        second = git(self.repo, "rev-parse", "HEAD")
        self.assertNotEqual(first, second)
        # Stacked, not rewritten: the first commit is still an ancestor.
        self.assertIn(first[:7], git(self.repo, "log", "--format=%h", "hub-sync"))
        self.assertEqual({"main", "hub-sync"}, self.origin_branches())

    def test_stamps_follow_the_contract_and_a_second_push_is_a_no_op(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.push_once()
        marker = json.loads((self.repo / "project-context" / ".project-context.json").read_text(encoding="utf-8"))
        stamp = marker["pushed"]["global/GUARDRAILS.md"]
        self.assertEqual({"sha256", "source_commit", "pushed_at"}, set(stamp))
        self.assertEqual(64, len(stamp["sha256"]))
        self.assertEqual("project-context/1", marker["schema"])

        again = self.run_cli("push", str(self.repo), "--dry-run", "--skip-doctor")
        self.assertEqual(0, again["changes"])
        self.assertEqual({"unchanged"}, set(again["summary"]))

    def test_a_copy_edited_in_the_repository_is_a_conflict(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.push_once()
        copy = self.repo / "project-context" / "global" / "GUARDRAILS.md"
        copy.write_text(copy.read_text(encoding="utf-8") + "- G-002 Snuck in.\n", encoding="utf-8")
        report = self.run_cli("push", str(self.repo), "--dry-run", "--skip-doctor", expected=2)
        conflict = next(a for a in report["actions"] if a["kind"] == "conflict")
        self.assertIn("the place to change it is the Hub", conflict["reason"])

    def test_an_unstamped_file_at_the_destination_is_a_conflict(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        landing = self.repo / "project-context" / "global"
        landing.mkdir(parents=True)
        (landing / "GUARDRAILS.md").write_text("# Someone else put this here\n", encoding="utf-8")
        report = self.run_cli("push", str(self.repo), "--dry-run", "--skip-doctor", expected=2)
        self.assertTrue(any(a["kind"] == "conflict" and "no stamp" in a["reason"] for a in report["actions"]))

    def test_push_refuses_a_repository_without_project_context(self) -> None:
        self.make_repo(installed=False)
        self.seed_global()
        report = self.run_cli("push", str(self.repo), "--dry-run", "--skip-doctor", expected=2)
        self.assertTrue(any("not installed" in reason for reason in report["blocked"]))

    def test_push_refuses_the_default_branch(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        report = self.run_cli("push", str(self.repo), "--apply", "--yes", "--skip-doctor",
                              "--branch", "main", expected=2)
        self.assertIn("default branch", report["gate"]["reason"])
        self.assertEqual("main", git(self.repo, "rev-parse", "--abbrev-ref", "HEAD"))

    def test_push_refuses_a_dirty_target(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        (self.repo / "src" / "main.py").write_text("def main():\n    return 1\n", encoding="utf-8")
        report = self.run_cli("push", str(self.repo), "--apply", "--yes", "--skip-doctor", expected=2)
        self.assertIn("uncommitted", report["gate"]["reason"])

    def test_push_refuses_a_dirty_hub_because_the_stamp_would_lie(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        git(self.hub, "init", "-q", "-b", "main", ".")
        git(self.hub, "add", "-A")
        git(self.hub, "commit", "-qm", "hub")
        self.write_global("GUARDRAILS.md", "# Guardrails\n\n- G-002 Uncommitted here.\n")
        report = self.run_cli("push", str(self.repo), "--dry-run", "--skip-doctor", expected=2)
        self.assertTrue(any("uncommitted changes" in reason for reason in report["blocked"]))
        allowed = self.run_cli("push", str(self.repo), "--dry-run", "--skip-doctor", "--allow-dirty")
        self.assertGreater(allowed["changes"], 0)

    def test_a_non_interactive_apply_without_yes_is_declined(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        report = self.run_cli("push", str(self.repo), "--apply", "--skip-doctor", expected=1)
        self.assertFalse(report["gate"]["applied"])
        self.assertIn("declined", report["gate"]["reason"])
        self.assertFalse((self.repo / "project-context" / "global").exists())

    def test_doctor_errors_block_a_push(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        doctor = self.stub("failing_doctor.py", FAILING_DOCTOR)
        report = self.run_cli("push", str(self.repo), "--dry-run", "--doctor", str(doctor), expected=2)
        self.assertTrue(any("doctor reports" in reason for reason in report["blocked"]))


class PullTests(HubCase):
    def authored_repo(self) -> Path:
        self.make_repo(installed=True)
        context = self.repo / "project-context"
        for folder in ("tasks", "sessions", "inbox", "global", "blueprint"):
            (context / folder).mkdir(parents=True, exist_ok=True)
        (context / "NOW.md").write_text("# Now\n\nBuilding.\n", encoding="utf-8")
        (context / "PLAN.md").write_text("# Plan\n\n- Search. Serves: E-002\n", encoding="utf-8")
        (context / "QUESTIONS.md").write_text("# Questions\n\n- Q-001 open\n", encoding="utf-8")
        (context / "tasks" / "T-001.md").write_text("# T-001\n", encoding="utf-8")
        (context / "inbox" / "C-1.md").write_text("# capsule\n", encoding="utf-8")
        (context / "SKILL.md").write_text("# protocol\n", encoding="utf-8")
        (context / "sessions" / "log.jsonl").write_text('{"secret": true}\n', encoding="utf-8")
        (context / "global" / "GUARDRAILS.md").write_text("# pushed here earlier\n", encoding="utf-8")
        (context / "blueprint" / "EPIC.md").write_text("# pushed here earlier\n", encoding="utf-8")
        git(self.repo, "add", "-A", "-f")
        git(self.repo, "commit", "-qm", "records")
        return self.repo

    def test_pull_takes_the_authored_set_and_nothing_else(self) -> None:
        self.authored_repo()
        self.run_cli("pull", str(self.repo), "--apply")
        pulled = self.hub / "projects" / "notes-api" / "pulled"
        got = sorted(path.relative_to(pulled).as_posix() for path in pulled.rglob("*") if path.is_file())
        self.assertEqual(
            ["NOW.md", "PLAN.md", "QUESTIONS.md", "STAMP.json", "inbox/C-1.md", "tasks/T-001.md"],
            got,
        )
        # The three exclusions that matter, checked as absences.
        self.assertFalse((pulled / "sessions").exists())
        self.assertFalse((pulled / "global").exists())
        self.assertFalse((pulled / "blueprint").exists())
        self.assertFalse((pulled / "SKILL.md").exists())
        self.assertFalse((pulled / ".project-context.json").exists())

    def test_the_stamp_records_repository_branch_commit_and_time(self) -> None:
        self.authored_repo()
        self.run_cli("pull", str(self.repo), "--apply")
        stamp = json.loads((self.hub / "projects" / "notes-api" / "pulled" / "STAMP.json").read_text(encoding="utf-8"))
        self.assertEqual("main", stamp["branch"])
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), stamp["commit"])
        self.assertRegex(stamp["pulled_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(64, len(stamp["files"]["NOW.md"]["sha256"]))

    def test_pull_never_writes_to_the_repository(self) -> None:
        self.authored_repo()
        before_head = git(self.repo, "rev-parse", "HEAD")
        before_status = git(self.repo, "status", "--porcelain")
        before_tree = sorted(
            (path.relative_to(self.repo).as_posix(), path.stat().st_mtime_ns)
            for path in self.repo.rglob("*") if path.is_file() and ".git" not in path.parts
        )
        self.run_cli("pull", str(self.repo), "--apply")
        self.assertEqual(before_head, git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(before_status, git(self.repo, "status", "--porcelain"))
        self.assertEqual(before_tree, sorted(
            (path.relative_to(self.repo).as_posix(), path.stat().st_mtime_ns)
            for path in self.repo.rglob("*") if path.is_file() and ".git" not in path.parts
        ))

    def test_a_second_pull_with_no_change_rewrites_nothing(self) -> None:
        self.authored_repo()
        self.run_cli("pull", str(self.repo), "--apply")
        again = self.run_cli("pull", str(self.repo), "--dry-run")
        self.assertEqual({"unchanged"}, set(again["summary"]))

    def test_a_removed_record_is_reported_and_pruned_only_on_request(self) -> None:
        self.authored_repo()
        self.run_cli("pull", str(self.repo), "--apply")
        git(self.repo, "rm", "-q", "project-context/QUESTIONS.md")
        git(self.repo, "commit", "-qm", "drop questions")
        stale = self.run_cli("pull", str(self.repo), "--dry-run")
        self.assertTrue(any(a["kind"] == "stale" for a in stale["actions"]))
        self.assertTrue((self.hub / "projects" / "notes-api" / "pulled" / "QUESTIONS.md").is_file())
        self.run_cli("pull", str(self.repo), "--apply", "--prune")
        self.assertFalse((self.hub / "projects" / "notes-api" / "pulled" / "QUESTIONS.md").exists())

    def test_pull_reads_the_default_branch_not_the_checked_out_one(self) -> None:
        self.authored_repo()
        git(self.repo, "switch", "-q", "--create", "side")
        (self.repo / "project-context" / "NOW.md").write_text("# Now\n\nSide branch only.\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "side work")
        self.run_cli("pull", str(self.repo), "--apply")
        pulled = (self.hub / "projects" / "notes-api" / "pulled" / "NOW.md").read_text(encoding="utf-8")
        self.assertIn("Building.", pulled)
        self.assertNotIn("Side branch only.", pulled)

    def test_pull_refreshes_the_registry_and_the_managed_state_line(self) -> None:
        self.authored_repo()
        summary = self.hub / "projects" / "notes-api" / "SUMMARY.md"
        summary.parent.mkdir(parents=True, exist_ok=True)
        summary.write_text(
            "# notes-api\n\nOwner prose above.\n\n"
            "<!-- project-hub:state:start -->\nLast pull: never · Last push: never\n"
            "<!-- project-hub:state:end -->\n\nOwner prose below.\n",
            encoding="utf-8",
        )
        self.run_cli("pull", str(self.repo), "--apply")
        text = summary.read_text(encoding="utf-8")
        self.assertIn("Owner prose above.", text)
        self.assertIn("Owner prose below.", text)
        self.assertNotIn("Last pull: never", text)
        self.assertIn("| notes-api |", (self.hub / "registry.md").read_text(encoding="utf-8"))


class RegistryAndPathTests(HubCase):
    def test_no_absolute_path_is_written_into_a_tracked_file(self) -> None:
        self.make_repo()
        installer = self.stub("installer.py", STUB_INSTALLER)
        self.run_cli("init", str(self.repo), "--apply", "--installer", str(installer),
                     "--no-push", "--skip-doctor", "--yes")
        registry = (self.hub / "registry.md").read_text(encoding="utf-8")
        self.assertNotIn(str(self.workspace), registry)
        self.assertIn("| notes-api |", registry)
        # The real location is remembered, but only in the ignored side file.
        local = json.loads((self.hub / ".project-hub.local.json").read_text(encoding="utf-8"))
        self.assertEqual(str(self.repo.resolve()), local["paths"]["notes-api"])

    def test_the_table_is_rewritten_and_the_prose_around_it_survives(self) -> None:
        self.make_repo()
        installer = self.stub("installer.py", STUB_INSTALLER)
        self.run_cli("init", str(self.repo), "--apply", "--installer", str(installer),
                     "--no-push", "--skip-doctor", "--yes")
        registry = (self.hub / "registry.md").read_text(encoding="utf-8")
        self.assertIn("# Registry", registry)
        self.assertIn("## How a row is filled", registry)

    def test_a_project_can_be_addressed_by_id_after_it_is_registered(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        self.run_cli("push", str(self.repo), "--apply", "--yes", "--skip-doctor")
        by_id = self.run_cli("push", "notes-api", "--dry-run", "--skip-doctor")
        self.assertEqual("notes-api", by_id["project_id"])

    def test_a_push_by_path_teaches_the_registry_where_the_repository_is(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        self.run_cli("push", str(self.repo), "--apply", "--yes", "--skip-doctor")
        row = [line for line in (self.hub / "registry.md").read_text(encoding="utf-8").splitlines()
               if line.startswith("| notes-api |")]
        self.assertEqual(1, len(row))
        self.assertIn("main", row[0])

    def test_none_of_another_workstreams_files_are_ever_created(self) -> None:
        """README.md, AGENTS.md and the rest belong to a different workstream."""
        self.make_repo(remote=True)
        installer = self.stub("installer.py", STUB_INSTALLER)
        self.seed_global()
        self.run_cli("init", str(self.repo), "--apply", "--installer", str(installer),
                     "--skip-doctor", "--yes")
        # init installs on a branch, so the whole flow ran: install, then push.
        self.assertTrue((self.repo / "project-context" / "global" / "SUMMARY.md").is_file())
        for name in ("README.md", "AGENTS.md", "CLAUDE.md", "ADAPTER-PROMPT.md",
                     "CHANGELOG-MIGRATION.md"):
            self.assertFalse((self.repo / name).exists(), f"the repo gained {name}")
            self.assertFalse((self.hub / "projects" / "notes-api" / name).exists(), name)

    def test_an_unknown_project_is_a_refusal_not_a_guess(self) -> None:
        report = self.run_cli("push", "no-such-project", "--dry-run", expected=2)
        self.assertIn("unknown project", report["error"])


class DoctorTests(HubCase):
    def test_the_owners_window_is_excluded_from_the_shared_doctor(self) -> None:
        doctor = self.stub("stub_doctor.py", STUB_DOCTOR)
        report = self.run_cli("doctor", "--doctor", str(doctor))
        self.assertTrue(report["available"])
        self.assertEqual(1, report["excluded_issues"])
        self.assertEqual(["owners_window/"], report["excluded_prefixes"])
        paths = [issue["path"] for issue in report["issues"]]
        self.assertEqual(["global/SUMMARY.md"], paths)
        self.assertEqual(1, report["summary"]["warnings"])

    def test_a_missing_doctor_is_reported_not_replaced(self) -> None:
        report = self.run_cli("doctor", "--doctor", str(self.workspace / "absent.py"))
        self.assertFalse(report["available"])
        self.assertIn("Project Context install", report["reason"])

    def test_a_doctor_that_raises_does_not_take_the_tool_down(self) -> None:
        doctor = self.stub("boom.py", "def doctor(target, stale_days=30):\n    raise RuntimeError('boom')\n")
        report = self.run_cli("doctor", "--doctor", str(doctor))
        self.assertFalse(report["available"])
        self.assertIn("RuntimeError", report["reason"])


class SafetyTests(HubCase):
    def test_running_outside_a_hub_is_refused(self) -> None:
        outside = self.workspace / "elsewhere"
        outside.mkdir()
        result = subprocess.run(
            [sys.executable, str(CLI), "--hub", str(outside), "doctor"],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn(".project-hub.json", result.stderr)

    def test_a_symlinked_destination_is_never_followed(self) -> None:
        self.make_repo(installed=True, remote=True)
        self.seed_global()
        landing = self.repo / "project-context" / "global"
        landing.mkdir(parents=True)
        outside = self.workspace / "outside.md"
        outside.write_text("# not ours\n", encoding="utf-8")
        (landing / "GUARDRAILS.md").symlink_to(outside)
        report = self.run_cli("push", str(self.repo), "--dry-run", "--skip-doctor", expected=2)
        self.assertTrue(any(a["kind"] == "conflict" and "symlink" in a["reason"] for a in report["actions"]))
        self.assertEqual("# not ours\n", outside.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

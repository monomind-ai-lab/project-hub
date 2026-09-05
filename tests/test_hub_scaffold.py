"""The scaffold itself: the invariants a Hub must ship with."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_repository.py"
CLI = ROOT / "skills" / "project-hub" / "scripts" / "project_hub.py"
UNFILLED = "<!-- project-hub:unfilled -->"

# Owned by another workstream. This tree must not create them. The onboarding
# surface used to be on this list; slice 8 moved it into what the scaffold
# ships, because a Hub is a folder a person opens for the first time and
# activation is part of the product rather than a thing bolted on after.
NOT_OURS = ("README.md", "AGENTS.md")

PLACEHOLDERS = {
    "project_id", "remote", "host", "default_branch", "visibility", "languages",
    "entry_points", "tracker", "ci", "deployment", "installed", "today",
    "file_count", "shape",
}


def load_cli():
    import importlib.util
    spec = importlib.util.spec_from_file_location("project_hub", CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ValidatorTests(unittest.TestCase):
    def test_the_repository_validates(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR)], check=False, capture_output=True, text=True
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


class LicenceAndVersionTests(unittest.TestCase):
    def test_the_licence_is_mit_plus_commons_clause_for_monomind(self) -> None:
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT + Commons Clause License Condition v1.0", text)
        self.assertIn("Copyright (c) 2026 MonoMind AI Lab", text)
        self.assertIn("Commons Clause Restriction", text)

    def test_one_version_number_agrees_with_the_marker(self) -> None:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        marker = json.loads((ROOT / ".project-hub.json").read_text(encoding="utf-8"))
        self.assertEqual(version, marker["version"])
        self.assertEqual("project-context/1", marker["schema"])


class OwnersWindowTests(unittest.TestCase):
    def test_it_ships_with_a_readme_and_nothing_else(self) -> None:
        files = sorted(p.name for p in (ROOT / "owners_window").iterdir() if p.is_file())
        self.assertEqual(["README.md"], files)

    def test_the_readme_states_the_three_negatives_and_stays_short(self) -> None:
        text = (ROOT / "owners_window" / "README.md").read_text(encoding="utf-8")
        for negative in ("never pushed", "never linted", "never pulled into"):
            self.assertIn(negative, text.casefold())
        prose = [line for line in text.splitlines() if line.strip() and not line.startswith("#")]
        self.assertLessEqual(len(prose), 14, "the owner's window README should get out of the way")

    def test_the_allow_list_cannot_reach_it(self) -> None:
        marker = json.loads((ROOT / ".project-hub.json").read_text(encoding="utf-8"))
        for entry in marker["push"]["global_include"]:
            self.assertNotIn("owners_window", entry)
            self.assertFalse(entry.startswith(("/", "..", ".")))

    def test_it_is_excluded_from_linting_and_from_graph_builds(self) -> None:
        marker = json.loads((ROOT / ".project-hub.json").read_text(encoding="utf-8"))
        self.assertIn("owners_window/", marker["lint"]["exclude"])
        self.assertIn("owners_window/", (ROOT / ".graphifyignore").read_text(encoding="utf-8"))


class SeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cli = load_cli()

    def test_every_unwritten_global_record_is_marked_unfilled(self) -> None:
        for path in sorted((ROOT / "global").glob("*.md")):
            if path.name == "README.md":
                continue
            self.assertIn(UNFILLED, path.read_text(encoding="utf-8"), path.name)

    def test_the_seeded_records_already_fit_their_budgets(self) -> None:
        """A seed that is over budget teaches the wrong length from day one."""
        limits = self.cli.budgets({})
        for path in sorted((ROOT / "global").rglob("*.md")):
            if path.name == "README.md":
                continue
            relative = path.relative_to(ROOT / "global").as_posix()
            limit = limits.get(relative, limits["global_file"])
            words = self.cli.word_count(path.read_text(encoding="utf-8"))
            self.assertLessEqual(words, limit, f"{relative} is {words} words, limit {limit}")

    def test_the_worked_examples_blueprint_fits_the_contract_budgets(self) -> None:
        limits = self.cli.budgets({})
        for name, key in (("EPIC.md", "blueprint/EPIC.md"), ("ARCHITECTURE.md", "blueprint/ARCHITECTURE.md")):
            path = ROOT / "projects" / "_example" / "blueprint" / name
            words = self.cli.word_count(path.read_text(encoding="utf-8"))
            self.assertLessEqual(words, limits[key], f"{name} is {words} words")

    def test_the_example_epic_has_ids_a_plan_can_serve(self) -> None:
        text = (ROOT / "projects" / "_example" / "blueprint" / "EPIC.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(len(re.findall(r"\bE-\d{3}\b", text)), 3)

    def test_the_example_is_skipped_by_the_commands(self) -> None:
        self.assertNotIn("_example", self.cli.known_projects(ROOT))
        self.assertNotIn("_example", (ROOT / "registry.md").read_text(encoding="utf-8"))


class TemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cli = load_cli()

    def test_project_templates_use_only_known_placeholders(self) -> None:
        for path in sorted((ROOT / "templates" / "project").rglob("*.md")):
            found = set(re.findall(r"\{\{([a-z_]+)\}\}", path.read_text(encoding="utf-8")))
            self.assertTrue(found <= PLACEHOLDERS, f"{path.name}: unknown {found - PLACEHOLDERS}")

    def test_an_unanswered_placeholder_becomes_a_visible_tbd(self) -> None:
        filled = self.cli.fill_template("a {{project_id}} b {{nonesuch}}", {"project_id": "x"})
        self.assertEqual("a x b TBD", filled)

    def test_global_templates_carry_the_six_required_keys(self) -> None:
        required = ("id:", "kind:", "status:", "title:", "created:", "asserted_by:")
        for path in sorted((ROOT / "templates" / "global").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), path.name)
            frontmatter = text.split("---\n", 2)[1]
            for key in required:
                self.assertIn(key, frontmatter, f"{path.name} is missing {key}")

    def test_global_templates_use_only_lifecycle_vocabulary_from_the_contract(self) -> None:
        allowed = {"proposed", "accepted", "superseded", "rejected"}
        for path in sorted((ROOT / "templates" / "global").glob("*.md")):
            frontmatter = path.read_text(encoding="utf-8").split("---\n", 2)[1]
            status = re.search(r"^status:\s*(\S+)", frontmatter, re.MULTILINE).group(1)
            self.assertIn(status, allowed, path.name)

    def test_the_summary_template_carries_the_managed_state_block(self) -> None:
        text = (ROOT / "templates" / "project" / "SUMMARY.md").read_text(encoding="utf-8")
        self.assertIn(self.cli.STATE_START, text)
        self.assertIn(self.cli.STATE_END, text)


class BoundaryTests(unittest.TestCase):
    def test_this_tree_neither_ships_nor_requires_another_workstreams_files(self) -> None:
        """They appear beside this tree. Nothing here creates or depends on one."""
        validator = (ROOT / "scripts" / "validate_repository.py").read_text(encoding="utf-8")
        required = validator.split("REQUIRED = (", 1)[1].split(")", 1)[0]
        for name in NOT_OURS:
            self.assertNotIn(f'"{name}"', required, f"the validator requires {name}")

    def test_the_commands_know_nothing_about_the_onboarding_surface(self) -> None:
        """Activation and operation are separate, and the CLI is the operation half.

        The scaffold now ships the onboarding surface, but `project_hub.py`
        still must not read, write, or name any of it: a command that knew
        about `guides/` or `.obsidian/` would be a second thing to keep in step
        with the prompt.
        """
        cli = CLI.read_text(encoding="utf-8")
        # The CLI reports whether the two managed instruction files exist; it
        # never writes one, because that text has a single owner elsewhere.
        self.assertIn("instruction_blocks_present", cli)
        for name in ("ADAPTER-PROMPT", "CHANGELOG-MIGRATION", ".obsidian", "guides", "hub-onboarding"):
            self.assertNotIn(name, cli, f"the CLI must not touch {name}")

    def test_the_cli_never_initialises_a_repository(self) -> None:
        """The constraint is on the code, not on this directory.

        An earlier version of this test asserted the tree was not a git
        repository at all. That was the right check while the scaffold was
        being built and the wrong one for the shipped product: a Hub *is* a git
        repository in use, and the design depends on it — commits carry the
        stamps, and `source_commit` names a real revision. What must stay true
        is that no command here ever creates a repository, a remote, or a
        branch in a tree the owner did not ask about.
        """
        text = CLI.read_text(encoding="utf-8")
        for forbidden in ('"init"', '"clone"', '"remote"'):
            self.assertNotIn(f"run_git(hub, {forbidden}", text)
            self.assertNotIn(f"run_git(repo, {forbidden}", text)

    def test_the_cli_imports_nothing_outside_the_standard_library(self) -> None:
        imported = {
            line.split()[1].split(".")[0]
            for line in CLI.read_text(encoding="utf-8").splitlines()
            if line.startswith(("import ", "from "))
        }
        self.assertTrue(imported <= set(sys.stdlib_module_names) | {"__future__"}, imported)

    def test_the_network_step_is_bounded_rather_than_absent(self) -> None:
        """`push` completes the round trip; what constrains it is narrower now.

        This test used to assert the CLI never pushed at all. That changed by
        instruction: push writes the sync branch and opens a pull request. The
        boundary did not disappear, it moved — so these are the properties that
        replace it, and merging is still nobody's job but a human's.
        """
        text = CLI.read_text(encoding="utf-8")
        # It pushes one named branch, with upstream set, and nothing else.
        self.assertIn('"push", "--set-upstream", "origin", branch', text)
        self.assertIn('SYNC_BRANCH = "hub-sync"', text)
        # Never rewriting history, never inventing a repository or a remote.
        for forbidden in ('"--force"', '"--force-with-lease"',
                          'run_git(repo, "init"', '"remote", "add"'):
            self.assertNotIn(forbidden, text)
        # Never merging, and never touching the default branch.
        self.assertNotIn('"pr", "merge"', text)
        self.assertIn("refusing to write on the default branch", text)


if __name__ == "__main__":
    unittest.main()

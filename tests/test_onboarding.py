"""The onboarding surface: the agent, the prompt it follows, and the guides.

A Hub is a folder a person opens for the first time, so activation is part of
what ships. None of it was under test: the agent file could be renamed away,
its promised report could drift from the report the prompt defines, and the
"no plugin code in this repository" rule was a sentence in a document rather
than a fact anything checked. These are the invariants that make the discipline
the agent is held to — check, skip, report; two layers, never three — apply to
the agent itself.
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "ADAPTER-PROMPT.md"
AGENT = ROOT / ".claude" / "agents" / "hub-onboarding.md"
GUIDES = ROOT / "guides"

# The seven steps of 2.9, in order. The agent does not restate them — it points
# at the prompt — so this is the only place the order is asserted.
STEPS = (
    "Identify the host",
    "Personalise",
    "Write the host pointer",
    "Seed `global/`",
    "Register the first project",
    "Offer Obsidian",
    "Report back",
)
STEP_HEADING = re.compile(r"^## Step (\d) — (.+)$", re.M)
# Fields step 7 requires. The agent promises to return this block in full, so a
# field added to one and not the other is a report with a hole in it.
REPORT_FIELDS = (
    "HOST", "SUBAGENTS", "PERSONALISATION", "POINTER FILE", "GLOBAL SEEDED",
    "PROJECT REGISTERED", "OBSIDIAN", "FILES WRITTEN", "FILES SKIPPED",
    "AGENTS.md", "NEXT",
)
# One guide per question 2.9 names. The migration changelog is the seventh and
# lives at the root, because an agent applying an upgrade reads it before it
# has any reason to open `guides/`.
GUIDE_QUESTIONS = {
    "what-the-hub-is.md": "what am I looking at",
    "authored-and-pushed.md": "which files may I edit",
    "add-a-project.md": "how do I get a repository into the Hub",
    "obsidian.md": "should I open the Hub in Obsidian",
    "bring-in-a-builder.md": "someone else is joining a project",
    "owners-window.md": "where do I put an idea that is not a project yet",
}


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    block = text.split("---\n", 2)[1]
    found: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith((" ", "-")):
            key, value = line.split(":", 1)
            found[key.strip()] = value.strip()
    return found


class OnboardingAgentTests(unittest.TestCase):
    def test_the_agent_ships_with_the_scaffold(self) -> None:
        self.assertTrue(AGENT.is_file(), f"{AGENT.relative_to(ROOT)} is the activation entry point")

    def test_its_frontmatter_names_it_and_says_when_to_use_it(self) -> None:
        front = frontmatter(AGENT)
        self.assertEqual("hub-onboarding", front.get("name"))
        description = front.get("description", "")
        self.assertGreater(len(description), 80, "a description too short to dispatch on")
        for trigger in ("set this up", "onboard me", "activate the hub"):
            self.assertIn(trigger, description.lower(), trigger)

    def test_it_has_no_shell_and_no_network(self) -> None:
        """"Never run `git init`, never push" is a fact about its tools.

        A promise in prose is worth what the model's compliance is worth. An
        agent with no Bash cannot run `git init` on its worst day, and that is
        the difference between a rule and a guarantee.
        """
        tools = {tool.strip() for tool in frontmatter(AGENT).get("tools", "").split(",")}
        self.assertEqual({"Read", "Write", "Edit", "Glob", "Grep"}, tools)
        for forbidden in ("Bash", "WebFetch", "WebSearch", "NotebookEdit"):
            self.assertNotIn(forbidden, tools)

    def test_it_points_at_the_prompt_rather_than_restating_it(self) -> None:
        """Two layers, never three — the rule the agent enforces, enforced on it.

        The agent may name a step; it may not carry a step's procedure, because
        a copy is how the two drift apart.
        """
        body = AGENT.read_text(encoding="utf-8").split("---\n", 2)[2]
        self.assertIn("ADAPTER-PROMPT.md", body)
        self.assertIn("AGENTS.md", body)
        self.assertEqual([], STEP_HEADING.findall(body), "the agent restates the prompt's steps")
        self.assertLess(len(body.split()), 700, "an agent long enough to be a second copy of the prompt")

    def test_it_reads_the_contract_before_anything_else(self) -> None:
        body = AGENT.read_text(encoding="utf-8").split("---\n", 2)[2]
        self.assertLess(body.index("AGENTS.md"), body.index("ADAPTER-PROMPT.md"))

    def test_it_never_opens_the_owners_private_space(self) -> None:
        body = AGENT.read_text(encoding="utf-8")
        self.assertIn("owners_window/", body)
        self.assertRegex(body, r"[Dd]o not open `owners_window/`")


class AdapterPromptTests(unittest.TestCase):
    def steps(self) -> list[tuple[str, str]]:
        return STEP_HEADING.findall(PROMPT.read_text(encoding="utf-8"))

    def test_the_seven_steps_are_present_numbered_and_in_order(self) -> None:
        steps = self.steps()
        self.assertEqual([str(n) for n in range(1, 8)], [number for number, _ in steps])
        for (_, title), expected in zip(steps, STEPS):
            self.assertIn(expected, title)

    def test_the_report_names_every_field_the_agent_returns(self) -> None:
        report = PROMPT.read_text(encoding="utf-8").split("## Step 7")[1]
        for field in REPORT_FIELDS:
            self.assertIn(f"**{field}:**", report, field)

    def test_the_hard_rules_survive_as_hard_rules(self) -> None:
        """Each of these was a decision; a deletion should fail, not pass quietly."""
        text = PROMPT.read_text(encoding="utf-8")
        for rule in (
            "Do not modify, rename, or replace `AGENTS.md`",
            "Two layers, never three",
            "Check, skip, report",
            "Never run `git init`",
        ):
            self.assertIn(rule, text, rule)

    def test_activation_state_is_never_shipped(self) -> None:
        """`HUB-OWNER.md` *is* the statement that activation has run.

        The contract's read order, the onboarding agent, and the validator all
        treat its presence as that fact, so a scaffold carrying one would
        assert an activation nobody performed. A host pointer is different:
        shipping one is fine, because step 3 checks for an existing pointer and
        skips it, and the scaffold is itself worked on in Claude Code.
        """
        self.assertFalse((ROOT / "HUB-OWNER.md").exists())

    def test_the_shipped_pointer_is_a_pointer(self) -> None:
        pointer = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("AGENTS.md", pointer)
        self.assertLess(len(pointer.splitlines()), 40, "a pointer this long is a second contract")
        # The rules live in AGENTS.md once. A pointer that repeats one is the
        # bug "two layers, never three" exists to prevent.
        for rule in ("Read order", "Canonical paths", "allow-list"):
            self.assertNotIn(rule, pointer, f"the pointer restates {rule!r}")

    def test_step_three_leaves_an_existing_pointer_alone(self) -> None:
        step = PROMPT.read_text(encoding="utf-8").split("## Step 3")[1].split("## Step 4")[0]
        self.assertIn("do not overwrite it", step)
        self.assertIn("count a skip", step)

    def test_the_validator_does_not_fail_a_hub_that_has_been_activated(self) -> None:
        """It ships inside the scaffold, so it runs in both places.

        The scaffold must not carry `HUB-OWNER.md` or vendored plugins, and a
        working Hub has both — activation wrote the first and Obsidian
        installed the second. Applying the scaffold's rule to a real Hub would
        fail it for doing exactly what it was told. A second host pointer, for
        a second tool the owner opened the Hub in, must pass too.
        """
        import shutil, subprocess, sys, tempfile
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory) / "hub"
            shutil.copytree(
                ROOT, hub,
                ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".venv"),
            )
            (hub / "HUB-OWNER.md").write_text("# Hub owner\n\n- OWNER_NAME: Example\n", encoding="utf-8")
            (hub / "GEMINI.md").write_text(
                "# Project Hub — host pointer\n\nThe contract is `AGENTS.md`.\n", encoding="utf-8"
            )
            (hub / ".obsidian" / "plugins" / "realclaudian").mkdir(parents=True)
            result = subprocess.run(
                [sys.executable, str(hub / "scripts" / "validate_repository.py")],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_the_scaffold_itself_still_refuses_to_ship_them(self) -> None:
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_repository.py")],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertFalse((ROOT / "HUB-OWNER.md").exists())

    def test_the_prompt_and_the_agent_agree_on_where_activation_state_lives(self) -> None:
        self.assertIn("HUB-OWNER.md", PROMPT.read_text(encoding="utf-8"))
        self.assertIn("HUB-OWNER.md", AGENT.read_text(encoding="utf-8"))


class ObsidianTests(unittest.TestCase):
    def test_no_plugin_code_is_vendored(self) -> None:
        """Claudian's `main.js` alone is over 3 MB and stales on every release.

        Obsidian installs plugins, updates them, and holds their licences. This
        repository recommends ids and nothing more.
        """
        self.assertFalse((ROOT / ".obsidian" / "plugins").exists())
        self.assertEqual([], [p for p in ROOT.rglob("main.js") if ".git" not in p.parts])

    def test_the_recommended_plugins_lead_with_the_in_vault_agent(self) -> None:
        import json
        plugins = json.loads((ROOT / ".obsidian" / "community-plugins.json").read_text(encoding="utf-8"))
        self.assertEqual("realclaudian", plugins[0], "Claudian is what makes the vault agentic")

    def test_the_core_plugins_enable_what_records_are_read_with(self) -> None:
        import json
        core = json.loads((ROOT / ".obsidian" / "core-plugins.json").read_text(encoding="utf-8"))
        for name in ("backlink", "outgoing-link", "graph", "global-search"):
            self.assertTrue(core.get(name), f"{name} is the reason to open a Hub as a vault")
        for name in ("sync", "publish"):
            self.assertFalse(core.get(name), f"{name} would move a private Hub off the owner's machine")


class GuideTests(unittest.TestCase):
    def test_every_question_2_9_names_has_a_guide(self) -> None:
        for name in GUIDE_QUESTIONS:
            self.assertTrue((GUIDES / name).is_file(), name)
        self.assertTrue((ROOT / "CHANGELOG-MIGRATION.md").is_file())

    def test_each_guide_answers_exactly_one_question_and_says_which(self) -> None:
        for name, question in GUIDE_QUESTIONS.items():
            text = (GUIDES / name).read_text(encoding="utf-8")
            self.assertIn("**One question:", text, name)
            self.assertIn(question, text, name)

    def test_guides_stay_short_enough_to_be_read(self) -> None:
        """A guide nobody finishes is a guide nobody read."""
        for path in sorted(GUIDES.glob("*.md")):
            words = len(path.read_text(encoding="utf-8").split())
            self.assertLess(words, 700, f"{path.name} is {words} words")

    def test_no_guide_is_orphaned_from_the_guide_set(self) -> None:
        shipped = {path.name for path in GUIDES.glob("*.md")}
        self.assertEqual(set(GUIDE_QUESTIONS), shipped, "a guide exists that nothing indexes")


class MigrationChangelogTests(unittest.TestCase):
    """The changelog is applied by an agent, so its shape is an interface.

    An entry missing a section is an upgrade an agent cannot complete, and the
    file itself promises all seven are present. That promise is checkable.
    """

    SECTIONS = (
        "Summary", "Added", "Changed", "Removed",
        "Path mappings", "Migration recipe", "Verification",
    )
    ENTRY = re.compile(r"^## (\d+\.\d+\.\d+) \((\d{4}-\d{2}-\d{2})\)$", re.M)

    def text(self) -> str:
        return (ROOT / "CHANGELOG-MIGRATION.md").read_text(encoding="utf-8")

    def entries(self) -> list[tuple[str, str]]:
        return self.ENTRY.findall(self.text())

    def test_there_is_an_entry_for_the_version_that_ships(self) -> None:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(version, self.entries()[0][0], "the newest entry is not this version")

    def test_entries_are_newest_first(self) -> None:
        versions = [tuple(int(part) for part in v.split(".")) for v, _ in self.entries()]
        self.assertEqual(sorted(versions, reverse=True), versions)

    def test_every_entry_carries_all_seven_sections_in_order(self) -> None:
        text = self.text()
        bounds = [match.start() for match in self.ENTRY.finditer(text)] + [len(text)]
        for index, (version, _) in enumerate(self.entries()):
            body = text[bounds[index]:bounds[index + 1]]
            found = re.findall(r"^### (.+)$", body, re.M)
            self.assertEqual(list(self.SECTIONS), found, f"{version} sections")

    def test_every_recipe_step_is_numbered_out_of_its_own_total(self) -> None:
        """`Step 2/4` when there are three steps sends an agent looking for a fourth."""
        text = self.text()
        bounds = [match.start() for match in self.ENTRY.finditer(text)] + [len(text)]
        for index, (version, _) in enumerate(self.entries()):
            body = text[bounds[index]:bounds[index + 1]]
            steps = re.findall(r"^#### Step (\d+)/(\d+) — ", body, re.M)
            self.assertTrue(steps, f"{version} has no numbered recipe steps")
            totals = {total for _, total in steps}
            self.assertEqual(1, len(totals), f"{version} disagrees with itself about its step count")
            self.assertEqual([str(n) for n in range(1, int(steps[0][1]) + 1)],
                             [number for number, _ in steps], f"{version} step numbering")


class GlobalTierDocumentationTests(unittest.TestCase):
    """`global/README.md` is where an owner learns what travels.

    It shipped saying `IDENTITY.md` was pushed, which decision D9 forbids at
    any setting, and that four opt-in paths were pushed by default. An owner
    reading it would have put the organisation's voice and its roster of people
    into files they believed builders could see. The table has to agree with the
    code that enforces it, so this reads both.
    """

    def table(self) -> dict[str, str]:
        text = (ROOT / "global" / "README.md").read_text(encoding="utf-8")
        found: dict[str, str] = {}
        for line in text.splitlines():
            match = re.match(r"^\| `([^`]+)` \| .* \| (.+?) \|$", line)
            if match:
                found[match.group(1)] = match.group(2).strip().strip("*")
        return found

    def cli(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "project_hub", ROOT / "skills" / "project-hub" / "scripts" / "project_hub.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_the_table_agrees_with_the_code_about_what_is_pushed(self) -> None:
        table, cli = self.table(), self.cli()
        for name in cli.GLOBAL_NEVER_PUSHED:
            self.assertEqual("never", table.get(name), f"{name} is D9; the table must not say otherwise")
        for name in cli.GLOBAL_OPT_IN:
            self.assertEqual("opt-in", table.get(name), f"{name} is opt-in, not a default")
        for name in cli.DEFAULT_GLOBAL_INCLUDE:
            self.assertEqual("yes", table.get(name), f"{name} is pushed by default")

    def test_the_readme_explains_the_difference_between_never_and_opt_in(self) -> None:
        text = (ROOT / "global" / "README.md").read_text(encoding="utf-8")
        self.assertIn("decision D9", text)
        self.assertIn("are not the same thing", text)

    def test_identity_cannot_be_pushed_even_when_a_marker_asks(self) -> None:
        cli = self.cli()
        marker = {"push": {"global_include": ["SUMMARY.md", "IDENTITY.md"]}}
        self.assertNotIn("IDENTITY.md", cli.global_include(marker))
        self.assertEqual(["IDENTITY.md"], cli.refused_global_entries(marker))


if __name__ == "__main__":
    unittest.main()

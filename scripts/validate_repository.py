#!/usr/bin/env python3
"""Validate the Project Hub scaffold's structure and public-safety invariants."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    "LICENSE",
    "VERSION",
    ".gitignore",
    ".graphifyignore",
    ".project-hub.json",
    "registry.md",
    "global/README.md",
    "global/SUMMARY.md",
    "global/IDENTITY.md",
    "global/GUARDRAILS.md",
    "global/WORKFLOWS.md",
    "global/GOALS.md",
    "global/RESOURCES.md",
    "global/OWNERS.md",
    "global/people/README.md",
    "global/agents/README.md",
    "global/skills/README.md",
    "global/shared/README.md",
    "owners_window/README.md",
    "projects/README.md",
    "projects/_example/MARK.md",
    "projects/_example/SUMMARY.md",
    "projects/_example/blueprint/EPIC.md",
    "projects/_example/blueprint/ARCHITECTURE.md",
    "projects/_example/pulled/README.md",
    "templates/README.md",
    "templates/project/MARK.md",
    "templates/project/SUMMARY.md",
    "templates/project/blueprint/EPIC.md",
    "templates/project/blueprint/ARCHITECTURE.md",
    "templates/global/PERSON.md",
    "templates/global/AGENT.md",
    "templates/global/SKILL.md",
    "templates/global/SHARED.md",
    "skills/project-hub/SKILL.md",
    "skills/project-hub/agents/openai.yaml",
    "skills/project-hub/scripts/project_hub.py",
    "docs/CLI.md",
    "scripts/validate_repository.py",
    "tests/test_project_hub.py",
    "tests/test_hub_scaffold.py",
    "tests/test_onboarding.py",
    # The onboarding surface. A Hub is a folder a person opens for the first
    # time, so activation is part of what ships, not a thing bolted on after.
    "ADAPTER-PROMPT.md",
    # The Claude Code pointer. This scaffold is itself worked on in Claude
    # Code, so a session opening it with no `CLAUDE.md` gets no contract at
    # all — the delivery-path failure Project Context errors on. Shipping the
    # pointer activation would have written costs nothing: step 3 checks
    # whether one exists, finds this one already naming `AGENTS.md`, and counts
    # a skip. What must never ship is `HUB-OWNER.md`, below.
    "CLAUDE.md",
    ".claude/agents/hub-onboarding.md",
    ".obsidian/community-plugins.json",
    ".obsidian/core-plugins.json",
    "guides/what-the-hub-is.md",
    "guides/authored-and-pushed.md",
    "guides/add-a-project.md",
    "guides/obsidian.md",
    "guides/bring-in-a-builder.md",
    "guides/owners-window.md",
    "CHANGELOG-MIGRATION.md",
)

# Files another workstream owns. This validator must neither require them nor
# be surprised by them: they appear alongside this tree, not from it.
NOT_OURS = ("README.md", "AGENTS.md")
# `HUB-OWNER.md` records the answers the owner gave at activation, and its
# presence is what "this Hub has been activated" means — to the contract's read
# order, to the onboarding agent, and to the check below. A scaffold that
# shipped one would assert an activation that never happened.
NEVER_SHIPPED = ("HUB-OWNER.md",)
# Obsidian installs plugins; the scaffold only recommends ids. Vendoring one
# would put a third-party binary and its licence into this distribution.
NEVER_SHIPPED_DIRECTORIES = (".obsidian/plugins",)
# ...and both are exactly what a *working* Hub has, because activation wrote the
# first and Obsidian installed the second. This validator ships inside the
# scaffold, so it runs in both places and must tell them apart.
ACTIVATION_MARKER = "HUB-OWNER.md"
# Host pointer files. Shipping one is fine and required for Claude Code;
# shipping a *fat* one is the bug, because a pointer that restates a rule is
# how two layers become three. Whichever are present are held to the shape the
# contract and ADAPTER-PROMPT step 3 both describe.
POINTER_FILES = ("CLAUDE.md", "GEMINI.md", ".cursor/rules/project-hub.mdc")
POINTER_MAX_LINES = 40

TEXT_SUFFIXES = {".html", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml", ""}
SKIP_PARTS = {".git", "__pycache__", ".venv", "node_modules"}

PRIVATE_PATTERNS = (
    # A home directory, a machine name, or anything shaped like a credential.
    re.compile(r"/Users/(?!example|your-name|username)[^/\s`\"']+"),
    re.compile(r"/home/(?!example|your-name|username|runner)[^/\s`\"']+"),
    re.compile(r"C:\\\\Users\\\\(?!Example|Public)[^\\\s]+"),
    re.compile(r"sk-(?:proj-|or-v1-)?[A-Za-z0-9_-]{16,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)

LICENSE_CLAUSES = (
    "MIT + Commons Clause License Condition v1.0",
    "Copyright (c) 2026 MonoMind AI Lab",
    "Permission is hereby granted",
    "Commons Clause Restriction",
    "do not sell, sublicense, or redistribute the components themselves",
)

# The invariants this product would be a different product without. Each is
# checked against the file that is supposed to guarantee it, not against prose
# that merely mentions it.
CLI_INVARIANTS = (
    ("DEFAULT_GLOBAL_INCLUDE", "push works from an allow-list"),
    ('"--set-upstream", "origin", branch', "push sets upstream on the sync branch"),
    ('SYNC_BRANCH = "hub-sync"', "the sync branch has one name, reused across pushes"),
    ("refusing to write on the default branch", "push never writes on the default branch"),
    ("AUTHORED_SET", "pull works from an allow-list"),
    ("the place to change it is the Hub", "an edited copy is a conflict, not an overwrite"),
    ("def atomic_write", "writes are atomic"),
    ("is_symlink", "symlinks are refused, never followed"),
)


def validate_skill(path: Path) -> list[str]:
    errors: list[str] = []
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return [f"{path.relative_to(ROOT)}: missing YAML frontmatter"]
    frontmatter = content.split("---\n", 2)[1]
    for key in ("name:", "description:"):
        if key not in frontmatter:
            errors.append(f"{path.relative_to(ROOT)}: missing {key[:-1]}")
    if "TODO" in content or "Replace with" in content:
        errors.append(f"{path.relative_to(ROOT)}: unfinished scaffold text")
    return errors


def main() -> int:
    errors: list[str] = []

    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    # NOT_OURS is present-is-fine: another workstream writes those and this
    # validator neither requires them nor is surprised by them.
    activated = (ROOT / ACTIVATION_MARKER).exists()
    if not activated:
        for relative in NEVER_SHIPPED:
            if (ROOT / relative).exists():
                errors.append(
                    f"{relative} is shipped in the scaffold; activation writes it, so shipping one "
                    "makes that step a permanent skip"
                )
        for relative in NEVER_SHIPPED_DIRECTORIES:
            if (ROOT / relative).exists():
                errors.append(f"{relative} exists; Obsidian installs plugins, the scaffold only recommends ids")

    for relative in POINTER_FILES:
        path = ROOT / relative
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if "AGENTS.md" not in "\n".join(lines):
            errors.append(f"{relative}: a host pointer must name AGENTS.md")
        if len(lines) > POINTER_MAX_LINES:
            errors.append(
                f"{relative}: {len(lines)} lines; a pointer over {POINTER_MAX_LINES} is a second copy "
                "of the contract, which is the bug two layers exist to prevent"
            )

    for skill in ROOT.glob("skills/*/SKILL.md"):
        errors.extend(validate_skill(skill))

    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        if path == Path(__file__).resolve():
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name != "LICENSE":
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for pattern in PRIVATE_PATTERNS:
            if pattern.search(content):
                errors.append(f"{path.relative_to(ROOT)}: possible private path, machine name, or credential")
                break

    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8") if (ROOT / "LICENSE").is_file() else ""
    for clause in LICENSE_CLAUSES:
        if clause not in license_text:
            errors.append(f"LICENSE is not the MIT + Commons Clause grant: missing {clause!r}")

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").is_file() else ""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append(f"VERSION is not a semantic version: {version!r}")

    marker_path = ROOT / ".project-hub.json"
    marker: dict = {}
    if marker_path.is_file():
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            errors.append(f".project-hub.json is not valid JSON: {error}")
        if marker.get("schema") != "project-context/1":
            errors.append(".project-hub.json must carry schema project-context/1 (record model v1 section 1)")
        if version and marker.get("version") != version:
            errors.append("VERSION and .project-hub.json version do not match")
        if marker.get("registry") != "registry.md":
            errors.append(".project-hub.json must point at registry.md")

    # The owner's window, checked as a mechanism rather than as a promise. If
    # the allow-list ever names it, the three negatives stop being true.
    include = marker.get("push", {}).get("global_include", [])
    if not include:
        errors.append(".project-hub.json declares no push allow-list")
    for entry in include:
        if "owners_window" in entry or entry.startswith(("/", "..")) or entry.startswith("."):
            errors.append(f"push allow-list must not name {entry!r}")
    if "owners_window/" not in marker.get("lint", {}).get("exclude", []):
        errors.append(".project-hub.json must exclude owners_window/ from linting")

    window = ROOT / "owners_window" / "README.md"
    if window.is_file():
        text = window.read_text(encoding="utf-8")
        for expected in ("Never pushed", "Never linted", "never pulled into"):
            if expected.casefold() not in text.casefold():
                errors.append(f"owners_window/README.md does not state: {expected}")
    for stray in (ROOT / "owners_window").rglob("*"):
        if stray.is_file() and stray.name != "README.md":
            errors.append(f"owners_window/ ships with content it should not: {stray.relative_to(ROOT)}")

    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").is_file() else ""
    for expected in ("sessions/", ".DS_Store", "*.sqlite", ".project-hub.local.json"):
        if expected not in ignore:
            errors.append(f".gitignore is missing {expected}")

    graphify = (ROOT / ".graphifyignore").read_text(encoding="utf-8") if (ROOT / ".graphifyignore").is_file() else ""
    if "owners_window/" not in graphify:
        errors.append(".graphifyignore must exclude owners_window/")

    cli_path = ROOT / "skills" / "project-hub" / "scripts" / "project_hub.py"
    if cli_path.is_file():
        cli = cli_path.read_text(encoding="utf-8")
        for needle, invariant in CLI_INVARIANTS:
            if needle not in cli:
                errors.append(f"the CLI no longer guarantees: {invariant}")
        # Zero runtime dependencies means the standard library and nothing else.
        third_party = {
            line.split()[1].split(".")[0]
            for line in cli.splitlines()
            if line.startswith(("import ", "from ")) and len(line.split()) > 1
        } - set(sys.stdlib_module_names) - {"__future__"}
        if third_party:
            errors.append(f"the CLI imports something outside the standard library: {sorted(third_party)}")
        # `push` now completes the round trip: it pushes the sync branch and
        # opens a pull request. What must stay true is narrower, and these are
        # the checks that carry it. Merging is still nobody's job but a human's.
        if '"push", "--set-upstream", "origin", branch' not in cli:
            errors.append("push no longer sets upstream on the sync branch by name")
        if "refusing to write on the default branch" not in cli:
            errors.append("push no longer refuses the default branch")
        for forbidden in ('run_git(repo, "init"', '"--force"', '"--force-with-lease"',
                          'remote", "add"', '"pr", "merge"'):
            if forbidden in cli:
                errors.append(f"the CLI contains a forbidden git operation: {forbidden}")

    registry = (ROOT / "registry.md").read_text(encoding="utf-8") if (ROOT / "registry.md").is_file() else ""
    if "| Project | Path | Remote | Branch | Last pull | Last push |" not in registry:
        errors.append("registry.md is missing the header the CLI reads and writes")

    example = ROOT / "projects" / "_example"
    if example.is_dir() and "E-001" not in (example / "blueprint" / "EPIC.md").read_text(encoding="utf-8"):
        errors.append("the worked example's epic has no E-NNN items for PLAN.md to serve")

    if errors:
        print("Repository validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Repository validation passed ({len(REQUIRED)} required files checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

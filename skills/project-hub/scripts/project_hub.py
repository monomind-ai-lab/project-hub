#!/usr/bin/env python3
"""Mark, pull, and push the projects a Project Hub administers.

Three commands and one delegation:

    init <repo>    mark a repository, summarise it, install Project Context
                   into it, then push the owner-authored tier down
    pull [repo]    copy that repository's authored set up into the Hub
    push [repo]    copy the Hub's global tier and that project's blueprint down
    doctor         the shared Project Context doctor, with the owner's window
                   excluded

The record model, the record parser, and the doctor are Project Context's, not
this file's. A Hub is an ordinary Project Context install, so that code arrives
through the ordinary create-only install and is called from here rather than
copied into here. This file owns exactly what is Hub-shaped: the marks, the
registry, the allow-lists, the budgets, and the single gated write path into a
repository the Hub does not live in.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any


SCHEMA = "project-context/1"
HUB_MARKER = ".project-hub.json"
LOCAL_CONFIG = ".project-hub.local.json"
REPO_MARKER = "project-context/.project-context.json"
REGISTRY = "registry.md"

# The owner's summary of a project carries one line this tool maintains.
# Nothing outside these two markers is ever read or written, which is the same
# rule the managed instruction block follows in a repository.
STATE_START = "<!-- project-hub:state:start -->"
STATE_END = "<!-- project-hub:state:end -->"

# A seeded record that nobody has written yet. Pushing one would put an empty
# guardrail in front of every agent in every repository, which is worse than
# having no guardrail, so push skips it and says it did.
UNFILLED = "<!-- project-hub:unfilled -->"

# Record model v1 section 5. Both of these are allow-lists on purpose: a folder
# that appears in the Hub or in a repository later is excluded by default and
# stays excluded until someone adds it here deliberately.
AUTHORED_SET = (
    "SUMMARY.md", "NOW.md", "PLAN.md", "DECISIONS.md", "LEARNINGS.md",
    "QUESTIONS.md", "tasks/", "decisions/", "questions/", "inbox/", "indexes/",
)
DEFAULT_GLOBAL_INCLUDE = (
    "SUMMARY.md",
    "GUARDRAILS.md",
    "WORKFLOWS.md",
    "skills/",
    "shared/",
)

# Deliberately absent from the default, and why.
#
# `IDENTITY.md` is never pushed, under any configuration. Decision D9: identity
# is the owner's or the organisation's voice and defaults, and a project
# repository may have collaborators who are not in the organisation. It belongs
# in the owner's own context, not committed into someone else's checkout.
#
# `GOALS.md`, `RESOURCES.md`, `people/` and `agents/` are opt-in per project,
# not default. Objectives across every project, internal dashboards and
# environments, and a roster of people are each more sensitive than the
# guardrails a builder actually needs to do the work. An owner who wants one of
# them in a given repository names it in that project's `push.global_include`.
GLOBAL_NEVER_PUSHED = ("IDENTITY.md",)
GLOBAL_OPT_IN = ("GOALS.md", "RESOURCES.md", "people/", "agents/")
# Record model v1 section 8, plus the two numbers it leaves to this side: a
# per-file ceiling for a global record and a ceiling for the whole subset,
# since "the pushed set stays under the global budget" needs a number.
DEFAULT_BUDGETS = {
    "global_total": 2000,
    "global_file": 400,
    "SUMMARY.md": 150,
    "blueprint/EPIC.md": 600,
    "blueprint/ARCHITECTURE.md": 1200,
}
DEFAULT_LINT_EXCLUDE = ("owners_window/",)

REGISTRY_COLUMNS = ("Project", "Path", "Remote", "Branch", "Last pull", "Last push")
REGISTRY_HEADER = "| " + " | ".join(REGISTRY_COLUMNS) + " |"
REGISTRY_RULE = "| " + " | ".join("---" for _ in REGISTRY_COLUMNS) + " |"
EMPTY = "—"

PROJECT_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
FENCE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
GIT_MODE_SYMLINK = "120000"
GIT_MODE_SUBMODULE = "160000"

LANGUAGE_BY_SUFFIX = {
    ".c": "C", ".cc": "C++", ".cpp": "C++", ".cs": "C#", ".css": "CSS",
    ".go": "Go", ".java": "Java", ".js": "JavaScript", ".jsx": "JavaScript",
    ".kt": "Kotlin", ".lua": "Lua", ".php": "PHP", ".py": "Python",
    ".rb": "Ruby", ".rs": "Rust", ".scala": "Scala", ".sh": "Shell",
    ".sql": "SQL", ".swift": "Swift", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".vue": "Vue",
}
ENTRY_POINT_NAMES = (
    "main.py", "__main__.py", "app.py", "manage.py", "main.go", "main.rs",
    "index.js", "index.ts", "server.js", "server.ts", "Makefile", "Justfile",
    "docker-compose.yml", "Dockerfile", "pyproject.toml", "package.json",
    "Cargo.toml", "go.mod",
)


# --------------------------------------------------------------------------
# Locating the Hub, and reading its configuration
# --------------------------------------------------------------------------


def find_hub(start: Path) -> Path | None:
    """The nearest ancestor of `start` that carries the Hub marker."""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / HUB_MARKER).is_file():
            return candidate
    return None


def load_marker(hub: Path) -> dict[str, Any]:
    try:
        data = json.loads((hub / HUB_MARKER).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def hub_version(hub: Path) -> str:
    """One version number, read from `VERSION` (record model v1 section 1)."""
    path = hub / "VERSION"
    if path.is_file():
        text = path.read_text(encoding="utf-8").strip()
        if text:
            return text
    return str(load_marker(hub).get("version", "unknown"))


def global_include(marker: dict[str, Any]) -> list[str]:
    entries = marker.get("push", {}).get("global_include")
    if isinstance(entries, list) and all(isinstance(item, str) for item in entries):
        chosen = list(entries)
    else:
        chosen = list(DEFAULT_GLOBAL_INCLUDE)
    # D9 is not a default a marker may override. A Hub that lists IDENTITY.md
    # does not get to push it; the entry is dropped and the caller is told.
    return [entry for entry in chosen if entry not in GLOBAL_NEVER_PUSHED]


def refused_global_entries(marker: dict[str, Any]) -> list[str]:
    """Entries a marker asked to push that D9 forbids. For honest reporting."""
    entries = marker.get("push", {}).get("global_include")
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, str) and e in GLOBAL_NEVER_PUSHED]


def budgets(marker: dict[str, Any]) -> dict[str, int]:
    merged = dict(DEFAULT_BUDGETS)
    declared = marker.get("push", {}).get("budget_words")
    if isinstance(declared, dict):
        for key, value in declared.items():
            if isinstance(value, int) and value > 0:
                merged[str(key)] = value
    return merged


def lint_exclude(marker: dict[str, Any]) -> list[str]:
    entries = marker.get("lint", {}).get("exclude")
    if isinstance(entries, list) and all(isinstance(item, str) for item in entries):
        return list(entries)
    return list(DEFAULT_LINT_EXCLUDE)


def load_local_config(hub: Path) -> dict[str, Any]:
    """Paths that must not be committed live here, and this file is ignored.

    A working copy on the owner's machine is a home path, and a home path in a
    tracked file is exactly what the repository must never carry. The registry
    keeps a relative path when there is one and a dash when there is not; the
    real location lives here.
    """
    path = hub / LOCAL_CONFIG
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def remember_path(hub: Path, project_id: str, repo: Path) -> str:
    """Record where a repository is, and return what the registry should show."""
    relative = os.path.relpath(repo, hub)
    if not relative.startswith(".."):
        return relative.replace(os.sep, "/")
    config = load_local_config(hub)
    paths = config.get("paths")
    if not isinstance(paths, dict):
        paths = {}
    paths[project_id] = str(repo)
    config["paths"] = paths
    atomic_write(hub / LOCAL_CONFIG, json.dumps(config, indent=2, sort_keys=True) + "\n")
    return EMPTY


def recall_path(hub: Path, project_id: str, registry_path: str) -> Path | None:
    if registry_path and registry_path != EMPTY:
        candidate = (hub / registry_path).resolve()
        if candidate.is_dir():
            return candidate
    remembered = load_local_config(hub).get("paths", {})
    if isinstance(remembered, dict):
        value = remembered.get(project_id)
        if isinstance(value, str) and Path(value).is_dir():
            return Path(value).resolve()
    return None


# --------------------------------------------------------------------------
# Writing, hashing, counting
# --------------------------------------------------------------------------


def atomic_write(path: Path, content: str) -> None:
    """Write `content` to `path` without ever leaving a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def word_count(text: str) -> int:
    """Words a reader would count: no frontmatter, no code blocks, no comments.

    The budget exists to keep what an agent loads small, and frontmatter and
    fenced code are not prose. Counting them would make a record with one
    example look over budget while a wall of text stayed under it.
    """
    body = FRONTMATTER.sub("", text)
    body = FENCE.sub("", body)
    body = COMMENT.sub("", body)
    return len(body.split())


def unfilled(text: str) -> bool:
    return UNFILLED in text


def read_text(path: Path) -> str | None:
    """The file's text, or None when it is not a readable regular file.

    A symlink is refused rather than followed: this tool copies bytes between
    repositories, and following a link is how a copy escapes the tree it was
    supposed to stay inside.
    """
    if path.is_symlink() or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------
# Git, read-only unless the push gate says otherwise
# --------------------------------------------------------------------------


def run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    """One git command in `cwd`, or None when it could not run at all.

    Everything that reads a repository funnels through here so a missing git,
    a repository git refuses, or a call that hangs degrades to "unknown"
    instead of a traceback or an invented answer.
    """
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def git_text(cwd: Path, *args: str) -> str | None:
    result = run_git(cwd, *args)
    if result is None or result.returncode != 0:
        return None
    return result.stdout.strip()


def is_git_repository(path: Path) -> bool:
    return git_text(path, "rev-parse", "--is-inside-work-tree") == "true"


def git_remote(repo: Path) -> str | None:
    return git_text(repo, "remote", "get-url", "origin")


def git_default_branch(repo: Path) -> str | None:
    """The default branch, asked for in the order that is cheapest and safest.

    `origin/HEAD` is the truth when the clone has it. Falling back to the
    checked-out branch is a guess, and it is labelled as one by the caller.
    """
    head = git_text(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if head and "/" in head:
        return head.rsplit("/", 1)[1]
    for candidate in ("main", "master"):
        if git_text(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{candidate}"):
            return candidate
    return git_text(repo, "rev-parse", "--abbrev-ref", "HEAD")


# The branch every push lands on, in the target repository. Named for where the
# content comes from rather than the direction it travels: a builder seeing
# `hub-sync` in their branch list can tell at a glance who wrote it and why,
# and the name is unlikely to collide with anything the project already uses.
SYNC_BRANCH = "hub-sync"


def gh_available() -> bool:
    """`gh` is an optional resolver, never a dependency.

    Everything up to the pull request works with git alone. When `gh` is
    absent we push and hand back the exact command and compare URL, which is
    strictly more useful than refusing.
    """
    return shutil.which("gh") is not None


def gh_open_pr(repo: Path, branch: str) -> str | None:
    """URL of an open pull request already tracking `branch`, if any."""
    if not gh_available():
        return None
    found = subprocess.run(
        ["gh", "pr", "list", "--head", branch, "--state", "open",
         "--json", "url", "--jq", ".[0].url"],
        cwd=repo, capture_output=True, text=True, check=False,
    )
    if found.returncode != 0:
        return None
    url = found.stdout.strip()
    return url or None


def compare_url(remote: str, branch: str, base: str | None) -> str | None:
    """A browser URL for opening the pull request by hand."""
    match = re.match(r"(?:git@github\.com:|https://github\.com/)([^/]+/[^/.]+)", remote or "")
    if not match:
        return None
    slug = match.group(1)
    return f"https://github.com/{slug}/compare/{base or 'main'}...{branch}?expand=1"


def git_head(repo: Path, ref: str = "HEAD") -> str | None:
    return git_text(repo, "rev-parse", ref)


def git_current_branch(repo: Path) -> str | None:
    name = git_text(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return None if name in (None, "HEAD") else name


def git_is_clean(repo: Path) -> bool | None:
    result = run_git(repo, "status", "--porcelain")
    if result is None or result.returncode != 0:
        return None
    return not result.stdout.strip()


def git_dirty_paths(repo: Path, *relatives: str) -> list[str]:
    """Which of `relatives` are modified or untracked in `repo`."""
    result = run_git(repo, "status", "--porcelain", "--", *relatives)
    if result is None or result.returncode != 0:
        return []
    dirty = []
    for line in result.stdout.splitlines():
        if len(line) > 3:
            dirty.append(line[3:].strip().strip('"'))
    return sorted(dirty)


def git_tree(repo: Path, ref: str, prefix: str) -> dict[str, str] | None:
    """`{path: mode}` for everything under `prefix` at `ref`, or None.

    `ls-tree` reads the object database. It does not touch the working tree,
    the index, or any file in the repository, which is what makes a pull
    honestly read-only against someone else's repository.
    """
    result = run_git(repo, "ls-tree", "-r", "-z", ref, "--", prefix)
    if result is None or result.returncode != 0:
        return None
    entries: dict[str, str] = {}
    for record in result.stdout.split("\0"):
        if not record or "\t" not in record:
            continue
        meta, path = record.split("\t", 1)
        parts = meta.split()
        if len(parts) >= 3:
            entries[path] = parts[0]
    return entries


def git_blob(repo: Path, ref: str, path: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            cwd=repo, check=False, capture_output=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        return result.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None


# --------------------------------------------------------------------------
# The registry
# --------------------------------------------------------------------------


def read_registry(hub: Path) -> list[dict[str, str]]:
    path = hub / REGISTRY
    text = read_text(path)
    if text is None:
        return []
    rows: list[dict[str, str]] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.replace(" ", "") == REGISTRY_HEADER.replace(" ", ""):
            in_table = True
            continue
        if not in_table:
            continue
        if not stripped.startswith("|"):
            break
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(set(cell) <= {"-", ":"} for cell in cells if cell):
            continue
        if len(cells) != len(REGISTRY_COLUMNS):
            continue
        rows.append(dict(zip(REGISTRY_COLUMNS, cells)))
    return rows


def write_registry(hub: Path, rows: list[dict[str, str]]) -> None:
    """Rewrite only the table. Everything a person wrote around it survives."""
    path = hub / REGISTRY
    text = read_text(path) or f"# Registry\n\n{REGISTRY_HEADER}\n{REGISTRY_RULE}\n"
    lines = text.splitlines()
    start = end = None
    for index, line in enumerate(lines):
        if line.strip().replace(" ", "") == REGISTRY_HEADER.replace(" ", ""):
            start = index
            end = index + 1
            while end < len(lines) and lines[end].strip().startswith("|"):
                end += 1
            break
    table = [REGISTRY_HEADER, REGISTRY_RULE]
    for row in sorted(rows, key=lambda item: item["Project"]):
        table.append("| " + " | ".join(row.get(name, EMPTY) or EMPTY for name in REGISTRY_COLUMNS) + " |")
    if start is None:
        lines.extend(["", *table])
    else:
        lines[start:end] = table
    atomic_write(path, "\n".join(lines).rstrip("\n") + "\n")


def upsert_registry(hub: Path, project_id: str, **fields: str) -> None:
    rows = read_registry(hub)
    for row in rows:
        if row["Project"] == project_id:
            row.update({key: value for key, value in fields.items() if value})
            break
    else:
        row = {name: EMPTY for name in REGISTRY_COLUMNS}
        row["Project"] = project_id
        row.update({key: value for key, value in fields.items() if value})
        rows.append(row)
    write_registry(hub, rows)


# --------------------------------------------------------------------------
# Projects
# --------------------------------------------------------------------------


def derive_project_id(repo: Path, remote: str | None) -> str:
    """The one name every clone of a repository agrees on.

    The working directory's name comes first, and the remote is only a
    fallback. Taking the remote first looks equivalent — for a GitHub URL the
    two usually match — but it is wrong in the cases that matter: a bare
    mirror, a fork whose remote keeps the upstream name, or any remote whose
    last path segment is not the project (`.../origin.git` yields `origin`).
    A wrong id here is not cosmetic: it names the Hub folder the project's
    records live in.
    """
    candidates = [repo.name]
    if remote:
        tail = remote.rstrip("/").rsplit("/", 1)[-1]
        candidates.append(tail[:-4] if tail.endswith(".git") else tail)
    for name in candidates:
        slug = re.sub(r"[^a-z0-9._-]+", "-", (name or "").casefold()).strip("-._")
        if slug and slug not in {"origin", "git", "repo", "repository"}:
            return slug
    return "project"


def project_dir(hub: Path, project_id: str) -> Path:
    return hub / "projects" / project_id


def known_projects(hub: Path) -> list[str]:
    """Every project folder, ignoring the worked examples."""
    root = hub / "projects"
    if not root.is_dir():
        return []
    return sorted(
        entry.name for entry in root.iterdir()
        if entry.is_dir() and not entry.is_symlink() and not entry.name.startswith("_")
    )


def refresh_state_line(path: Path, pulled: str, pushed: str) -> dict[str, Any] | None:
    """Update the managed state line in a project summary, if there is one."""
    text = read_text(path)
    if text is None:
        return None
    starts, ends = text.count(STATE_START), text.count(STATE_END)
    if starts != 1 or ends != 1:
        return {
            "kind": "skip", "path": str(path),
            "reason": f"state markers are missing or duplicated ({starts} start, {ends} end)",
        }
    head = text.index(STATE_START)
    tail = text.index(STATE_END) + len(STATE_END)
    if tail < head:
        return {"kind": "skip", "path": str(path), "reason": "state end marker precedes start"}
    block = f"{STATE_START}\nLast pull: {pulled} · Last push: {pushed}\n{STATE_END}"
    if text[head:tail] == block:
        return {"kind": "unchanged", "path": str(path), "reason": "state line is current"}
    return {"kind": "update_state", "path": str(path), "content": text[:head] + block + text[tail:]}


# --------------------------------------------------------------------------
# Plan actions
# --------------------------------------------------------------------------


WRITING_KINDS = {"create", "update", "mirror", "update_state", "update_marker", "delete"}


def add_create(actions: list[dict[str, Any]], destination: Path, content: str) -> None:
    """Create-only: an existing file is preserved and reported, never replaced."""
    if destination.is_symlink():
        actions.append({"kind": "conflict", "path": str(destination), "reason": "destination is a symlink"})
        return
    if not destination.exists():
        actions.append({"kind": "create", "path": str(destination), "content": content})
        return
    if not destination.is_file():
        actions.append({"kind": "conflict", "path": str(destination), "reason": "destination is not a regular file"})
        return
    current = read_text(destination)
    if current == content:
        actions.append({"kind": "unchanged", "path": str(destination), "reason": "matches source"})
    else:
        actions.append({
            "kind": "preserve_existing", "path": str(destination),
            "reason": "existing content differs; this tool never rewrites an authored file",
        })


def unified(before: str, after: str, label: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile=f"a/{label}", tofile=f"b/{label}", n=2,
        )
    )


def summarise(actions: list[dict[str, Any]]) -> dict[str, int]:
    return {kind: sum(action["kind"] == kind for action in actions) for kind in sorted({a["kind"] for a in actions})}


def public_report(report: dict[str, Any]) -> dict[str, Any]:
    clean = json.loads(json.dumps(report))
    for action in clean.get("actions", []):
        action.pop("content", None)
    return clean


def apply_actions(actions: list[dict[str, Any]]) -> list[str]:
    written: list[str] = []
    for action in actions:
        if action["kind"] == "delete":
            try:
                Path(action["path"]).unlink()
                written.append(action["path"])
            except OSError:
                pass
        elif action["kind"] in WRITING_KINDS:
            atomic_write(Path(action["path"]), action["content"])
            written.append(action["path"])
    return written


# --------------------------------------------------------------------------
# Reading a repository
# --------------------------------------------------------------------------


def inspect_repository(repo: Path) -> dict[str, Any]:
    """What `init` writes a mark from. Read-only, and cheap enough to re-run."""
    remote = git_remote(repo)
    host = None
    if remote:
        match = re.search(r"(?:https?://|git@|ssh://git@)([^/:]+)", remote)
        host = match.group(1) if match else None
    tracked = git_text(repo, "ls-files")
    files = tracked.splitlines() if tracked else []
    if not files:
        files = [
            str(path.relative_to(repo)) for path in repo.rglob("*")
            if path.is_file() and not path.is_symlink() and ".git" not in path.parts
        ]
    counts: dict[str, int] = {}
    for name in files:
        language = LANGUAGE_BY_SUFFIX.get(Path(name).suffix.casefold())
        if language:
            counts[language] = counts.get(language, 0) + 1
    languages = [name for name, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))][:4]
    entry_points = sorted(
        name for name in files
        if Path(name).name in ENTRY_POINT_NAMES and name.count("/") <= 2
    )[:5]
    return {
        "path": str(repo),
        "remote": remote,
        "host": host,
        "default_branch": git_default_branch(repo),
        # A private repository is the assumption this product is built around.
        # Nothing here can see a host's visibility flag without the network and
        # a credential, so the mark records the assumption and says it is one.
        "visibility": "unknown (assumed private)",
        "languages": languages,
        "entry_points": entry_points,
        "file_count": len(files),
        "is_git": is_git_repository(repo),
        "project_context_installed": (repo / REPO_MARKER).is_file(),
    }


def fill_template(text: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        return values.get(match.group(1), "TBD")
    return re.sub(r"\{\{([a-z_]+)\}\}", replace, text)


def mark_values(facts: dict[str, Any], project_id: str) -> dict[str, str]:
    return {
        "project_id": project_id,
        "remote": facts["remote"] or "TBD",
        "host": facts["host"] or "TBD",
        "default_branch": facts["default_branch"] or "TBD",
        "visibility": facts["visibility"],
        "languages": ", ".join(facts["languages"]) or "TBD",
        "entry_points": ", ".join(f"`{name}`" for name in facts["entry_points"]) or "TBD",
        "tracker": "TBD",
        "ci": "TBD",
        "deployment": "TBD",
        "installed": "yes" if facts["project_context_installed"] else "no",
        "today": today(),
        "file_count": str(facts["file_count"]),
        "shape": ", ".join(facts["languages"]) + " repository" if facts["languages"] else "TBD",
    }


# --------------------------------------------------------------------------
# init
# --------------------------------------------------------------------------


def find_installer(hub: Path, override: str | None) -> str | None:
    """Where the Project Context initializer is, or None.

    A Hub carries the protocol skill, not the installer: a consuming repository
    never needs its own copy of the thing that installed it. So `init` has to
    be told where the initializer lives, and it asks in the order that puts the
    owner's explicit answer first.
    """
    candidates = [
        override,
        os.environ.get("PROJECT_CONTEXT_INIT"),
        load_marker(hub).get("tools", {}).get("project_context_init"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if not path.is_absolute():
            path = (hub / path).resolve()
        if path.is_file():
            return str(path)
    found = shutil.which("project-context")
    return found


def run_installer(installer: str, repo: Path) -> dict[str, Any]:
    command = (
        [sys.executable, installer, "init", "--target", str(repo), "--install-skills", "--apply"]
        if installer.endswith(".py")
        else [installer, "init", "--target", str(repo), "--apply"]
    )
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as error:
        return {"ran": False, "reason": str(error), "command": command}
    return {
        "ran": True,
        "returncode": result.returncode,
        "command": command,
        "stderr": result.stderr.strip()[-2000:],
    }


def plan_init(hub: Path, repo: Path, project_id: str | None) -> dict[str, Any]:
    facts = inspect_repository(repo)
    identifier = project_id or derive_project_id(repo, facts["remote"])
    actions: list[dict[str, Any]] = []
    blocked: list[str] = []
    if not PROJECT_ID.match(identifier):
        blocked.append(f"project id {identifier!r} is not a slug of lowercase letters, digits, dot, dash, underscore")
    if identifier.startswith("_"):
        blocked.append("a project id may not start with an underscore; that prefix marks a worked example")
    if facts["project_context_installed"]:
        blocked.append(
            "Project Context is already installed in this repository "
            f"({REPO_MARKER} exists); use `push` instead"
        )
    if not facts["is_git"]:
        blocked.append("target is not a git repository; this tool never runs `git init` on someone else's tree")
    destination = project_dir(hub, identifier)
    if not blocked:
        values = mark_values(facts, identifier)
        for template, name in (("project/MARK.md", "MARK.md"), ("project/SUMMARY.md", "SUMMARY.md")):
            source = read_text(hub / "templates" / template)
            if source is None:
                blocked.append(f"missing template: templates/{template}")
                continue
            add_create(actions, destination / name, fill_template(source, values))
    return {
        "command": "init",
        "hub": str(hub),
        "project_id": identifier,
        "repository": facts,
        "blocked": blocked,
        "actions": actions,
        "summary": summarise(actions),
        "has_conflicts": bool(blocked) or any(a["kind"] == "conflict" for a in actions),
        "next": [
            f"copy templates/project/blueprint/ into projects/{identifier}/blueprint/ when you are ready to author the epic",
            f"project_hub.py push {identifier} --apply",
        ],
    }


def command_init(args: argparse.Namespace, hub: Path) -> tuple[int, dict[str, Any]]:
    repo = args.repo.resolve()
    if not repo.is_dir():
        return 2, {"command": "init", "error": f"not a directory: {repo}"}
    report = plan_init(hub, repo, args.id)
    if args.dry_run or report["has_conflicts"]:
        return (2 if report["has_conflicts"] else 0), report

    apply_actions(report["actions"])
    identifier = report["project_id"]
    upsert_registry(
        hub, identifier,
        **{
            "Path": remember_path(hub, identifier, repo),
            "Remote": report["repository"]["remote"] or EMPTY,
            "Branch": report["repository"]["default_branch"] or EMPTY,
        },
    )
    report["actions"] = plan_init(hub, repo, identifier)["actions"]
    report["summary"] = summarise(report["actions"])

    installer = find_installer(hub, args.installer)
    if installer is None:
        report["install"] = {
            "ran": False,
            "reason": (
                "the Project Context initializer was not found. The mark and the summary are "
                "written and the project is registered; nothing was written to the repository. "
                "Point at it with --installer <path>, the PROJECT_CONTEXT_INIT environment "
                "variable, or tools.project_context_init in .project-hub.json, then re-run."
            ),
        }
        return 3, report

    # Steps 3 and 4 both write to someone else's repository, so they share one
    # gate, one branch, and one confirmation. Installing and then pushing on
    # separate branches would leave the install uncommitted and the push
    # refusing the tree it just dirtied.
    branch = args.branch or f"project-hub/init-{identifier}-{today().replace('-', '')}"
    code, report["install"] = gated_install(repo, branch, installer, args.yes)
    if code != 0:
        return code, report

    if args.no_push:
        report["push"] = {"ran": False, "reason": "--no-push"}
        return 0, report
    push_args = argparse.Namespace(
        repo=identifier, all=False, apply=True, dry_run=False,
        branch=branch, yes=True, allow_dirty=False, skip_doctor=args.skip_doctor,
        prune=False, doctor=args.doctor,
    )
    code, push_report = command_push(push_args, hub)
    report["push"] = push_report
    return code, report


def gated_install(repo: Path, branch: str, installer: str, yes: bool) -> tuple[int, dict[str, Any]]:
    """Create the branch, install Project Context on it, commit that install.

    The same preconditions `push` applies, because this is the same kind of
    write: a clean tree, a new branch that is not the default one, and a person
    who said yes. `git add -A` is exact rather than broad here — the tree was
    clean one line earlier, so everything it stages is the installer's output.
    """
    clean = git_is_clean(repo)
    if clean is None:
        return 2, {"ran": False, "reason": "could not read the repository's status"}
    if not clean:
        return 2, {"ran": False, "reason": "the repository has uncommitted changes; commit or stash them first"}
    default_branch = git_default_branch(repo)
    if default_branch and branch == default_branch:
        return 2, {"ran": False, "reason": f"refusing to write on the default branch ({default_branch})"}
    if git_text(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"):
        return 2, {"ran": False, "reason": f"branch {branch} already exists; pass --branch <name>"}
    if not yes:
        print(
            f"\nThis installs Project Context into {repo} on a new branch {branch}, "
            "then pushes the Hub's global tier and this project's blueprint onto the same branch.",
            file=sys.stderr,
        )
        if not confirm("Go ahead?"):
            return 1, {"ran": False, "reason": "declined at the confirmation prompt", "branch": branch}

    started_on = git_current_branch(repo)
    created = run_git(repo, "switch", "--create", branch)
    if created is None or created.returncode != 0:
        return 2, {"ran": False, "reason": "could not create the branch", "branch": branch}
    result = run_installer(installer, repo)
    result["branch"] = branch
    result["started_on"] = started_on
    if not result["ran"] or result["returncode"] != 0:
        result["reason"] = f"the initializer failed; the repository is on {branch} with whatever it wrote"
        return 3, result
    add = run_git(repo, "add", "--all")
    commit = run_git(repo, "commit", "--quiet", "--message",
                     "chore(project-context): install Project Context\n")
    result["committed"] = bool(add and add.returncode == 0 and commit and commit.returncode == 0)
    return 0, result


# --------------------------------------------------------------------------
# pull
# --------------------------------------------------------------------------


def authored(path: str) -> bool:
    """Is this repository-relative path inside `project-context/` authored?

    An allow-list, so `sessions/`, the marker, the protocol text, and the whole
    pushed set are excluded because they are not on it — not because anyone
    remembered to exclude them.
    """
    if not path.startswith("project-context/"):
        return False
    relative = path[len("project-context/"):]
    for entry in AUTHORED_SET:
        if entry.endswith("/"):
            if relative.startswith(entry):
                return True
        elif relative == entry:
            return True
    return False


def plan_pull(hub: Path, project_id: str, repo: Path, branch: str | None, prune: bool) -> dict[str, Any]:
    facts = inspect_repository(repo)
    actions: list[dict[str, Any]] = []
    blocked: list[str] = []
    skipped: list[dict[str, str]] = []
    ref = branch or facts["default_branch"]
    if not facts["is_git"]:
        blocked.append("source is not a git repository; pull reads the default branch from git history")
    if not ref:
        blocked.append("could not determine the default branch; pass --branch")
    commit = git_head(repo, ref) if ref else None
    if ref and commit is None:
        blocked.append(f"branch {ref!r} does not resolve in that repository")
    destination = project_dir(hub, project_id) / "pulled"
    stamp_files: dict[str, dict[str, str]] = {}
    if not blocked:
        tree = git_tree(repo, ref, "project-context") or {}
        if not tree:
            blocked.append(f"no project-context/ at {ref}; is Project Context installed there?")
        for path in sorted(tree):
            mode = tree[path]
            if mode in (GIT_MODE_SYMLINK, GIT_MODE_SUBMODULE):
                skipped.append({"path": path, "reason": "symlink or submodule; never followed"})
                continue
            if not authored(path):
                continue
            content = git_blob(repo, ref, path)
            if content is None:
                skipped.append({"path": path, "reason": "not readable as UTF-8 text"})
                continue
            relative = path[len("project-context/"):]
            target = destination / relative
            current = read_text(target)
            stamp_files[relative] = {"sha256": digest(content)}
            if current == content:
                actions.append({"kind": "unchanged", "path": str(target), "reason": "mirror is current"})
            else:
                actions.append({"kind": "mirror", "path": str(target), "content": content,
                                "diff": unified(current or "", content, relative)})
        if destination.is_dir():
            for existing in sorted(destination.rglob("*")):
                if not existing.is_file() or existing.is_symlink():
                    continue
                relative = existing.relative_to(destination).as_posix()
                if relative in stamp_files or relative in ("STAMP.json", "README.md"):
                    continue
                actions.append(
                    {"kind": "delete", "path": str(existing)} if prune
                    else {"kind": "stale", "path": str(existing),
                          "reason": "no longer in the repository's authored set; --prune removes it"}
                )
    stamp = {
        "repository": facts["remote"] or str(repo),
        "branch": ref,
        "commit": commit,
        "pulled_at": utc_now(),
        "hub_version": hub_version(hub),
        "files": stamp_files,
    }
    if not blocked:
        text = json.dumps(stamp, indent=2, sort_keys=True) + "\n"
        current = read_text(destination / "STAMP.json")
        # A stamp whose file hashes are unchanged is not rewritten: a pull that
        # found nothing new should leave no trace, or every run is a diff.
        if current is not None and json.loads(current).get("files") == stamp_files:
            actions.append({"kind": "unchanged", "path": str(destination / "STAMP.json"), "reason": "stamp is current"})
        else:
            actions.append({"kind": "mirror", "path": str(destination / "STAMP.json"), "content": text})
    return {
        "command": "pull",
        "hub": str(hub),
        "project_id": project_id,
        "ref": ref,
        "commit": commit,
        "read_only": True,
        "blocked": blocked,
        "skipped": skipped,
        "actions": actions,
        "summary": summarise(actions),
        "has_conflicts": bool(blocked),
        "stamp": {key: value for key, value in stamp.items() if key != "files"},
    }


def command_pull(args: argparse.Namespace, hub: Path) -> tuple[int, dict[str, Any]]:
    targets, error = resolve_targets(hub, args)
    if error:
        return 2, {"command": "pull", "error": error}
    reports: list[dict[str, Any]] = []
    worst = 0
    for project_id, repo in targets:
        if args.fetch:
            # A fetch writes only to the owner's own clone's remote-tracking
            # refs. It never touches the working tree, the index, or a branch.
            run_git(repo, "fetch", "--quiet", "origin")
        report = plan_pull(hub, project_id, repo, args.branch, args.prune)
        if report["has_conflicts"]:
            worst = max(worst, 2)
        elif args.apply:
            destination = project_dir(hub, project_id)
            destination.mkdir(parents=True, exist_ok=True)
            apply_actions(report["actions"])
            facts = inspect_repository(repo)
            source = read_text(hub / "templates" / "project" / "MARK.md")
            if source is not None:
                extra: list[dict[str, Any]] = []
                add_create(extra, destination / "MARK.md", fill_template(source, mark_values(facts, project_id)))
                apply_actions(extra)
                report["actions"].extend(extra)
            row = next((r for r in read_registry(hub) if r["Project"] == project_id), {})
            state = refresh_state_line(
                destination / "SUMMARY.md", report["stamp"]["pulled_at"], row.get("Last push", EMPTY) or EMPTY
            )
            if state:
                apply_actions([state])
                report["actions"].append(state)
            upsert_registry(
                hub, project_id,
                **{
                    "Path": remember_path(hub, project_id, repo),
                    "Remote": facts["remote"] or EMPTY,
                    "Branch": report["ref"] or EMPTY,
                    "Last pull": report["stamp"]["pulled_at"],
                },
            )
            report["summary"] = summarise(report["actions"])
        reports.append(report)
    if len(reports) == 1:
        return worst, reports[0]
    return worst, {"command": "pull", "hub": str(hub), "projects": reports}


# --------------------------------------------------------------------------
# push
# --------------------------------------------------------------------------


def shareable(hub: Path, marker: dict[str, Any]) -> tuple[list[tuple[str, str]], list[dict[str, str]]]:
    """The global subset that may leave the Hub, plus why anything was left out.

    Three filters, in order of how load-bearing they are. The allow-list is the
    mechanism: a path not named in `push.global_include` is not pushed, so a
    folder added to the Hub later — `owners_window/` being the one that already
    exists — is non-pushed by default and needs no rule to keep it that way.
    A README explains the Hub to its owner and has no business in a repository.
    An unfilled seed is a placeholder, and a placeholder guardrail is worse
    than none.
    """
    root = hub / "global"
    selected: list[tuple[str, str]] = []
    skipped: list[dict[str, str]] = []
    for entry in global_include(marker):
        base = root / entry.rstrip("/")
        if entry.endswith("/"):
            if not base.is_dir() or base.is_symlink():
                skipped.append({"path": f"global/{entry}", "reason": "not a directory in the Hub"})
                continue
            candidates = sorted(path for path in base.rglob("*.md"))
        else:
            candidates = [base]
        for path in candidates:
            relative = f"global/{path.relative_to(root).as_posix()}"
            if path.name == "README.md":
                skipped.append({"path": relative, "reason": "a README explains the Hub, not the organisation"})
                continue
            text = read_text(path)
            if text is None:
                skipped.append({"path": relative, "reason": "missing, a symlink, or not UTF-8 text"})
                continue
            if unfilled(text):
                skipped.append({"path": relative, "reason": "still a seed; delete the unfilled marker to push it"})
                continue
            selected.append((relative, text))
    return selected, skipped


def blueprint_files(hub: Path, project_id: str) -> tuple[list[tuple[str, str]], list[dict[str, str]]]:
    root = project_dir(hub, project_id) / "blueprint"
    selected: list[tuple[str, str]] = []
    skipped: list[dict[str, str]] = []
    if not root.is_dir() or root.is_symlink():
        return selected, skipped
    for path in sorted(root.rglob("*.md")):
        relative = f"blueprint/{path.relative_to(root).as_posix()}"
        text = read_text(path)
        if text is None:
            skipped.append({"path": relative, "reason": "missing, a symlink, or not UTF-8 text"})
            continue
        if unfilled(text):
            skipped.append({"path": relative, "reason": "still a seed; delete the unfilled marker to push it"})
            continue
        selected.append((relative, text))
    return selected, skipped


def check_budgets(files: list[tuple[str, str]], limits: dict[str, int]) -> list[dict[str, Any]]:
    """Over-budget files, named so the owner knows which one to trim."""
    findings: list[dict[str, Any]] = []
    global_total = 0
    for relative, text in files:
        count = word_count(text)
        if relative.startswith("global/"):
            global_total += count
            name = relative[len("global/"):]
            limit = limits.get(name, limits["global_file"])
        else:
            limit = limits.get(relative, limits["global_file"])
        if count > limit:
            findings.append({"path": relative, "words": count, "limit": limit, "over_by": count - limit})
    total_limit = limits["global_total"]
    if global_total > total_limit:
        widest = sorted(
            ((relative, word_count(text)) for relative, text in files if relative.startswith("global/")),
            key=lambda item: -item[1],
        )
        findings.append({
            "path": "global/", "words": global_total, "limit": total_limit,
            "over_by": global_total - total_limit,
            "trim_first": [name for name, _ in widest[:3]],
        })
    return findings


def load_doctor(hub: Path, override: str | None) -> Any:
    """Import the shared doctor from where the Project Context install put it.

    There is one doctor and it belongs to Project Context. A Hub is an ordinary
    install of that product, so the health check it runs on itself is the same
    code every repository runs, called rather than copied.
    """
    candidates = [
        override,
        os.environ.get("PROJECT_CONTEXT_DOCTOR"),
        str(hub / ".agents" / "skills" / "project-context" / "scripts" / "context_doctor.py"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if not path.is_absolute():
            path = (hub / path).resolve()
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location("context_doctor", path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except (OSError, SyntaxError, ImportError):
            continue
        return module
    return None


def run_doctor(hub: Path, override: str | None) -> dict[str, Any]:
    module = load_doctor(hub, override)
    if module is None:
        return {
            "available": False,
            "reason": (
                "the shared Project Context doctor was not found. A Hub is a Project Context "
                "install; run the initializer here, or pass --doctor <path>."
            ),
        }
    try:
        report = module.doctor(hub)
    except Exception as error:  # a diagnostic that crashes is worse than one that abstains
        return {"available": False, "reason": f"the doctor raised {type(error).__name__}: {error}"}
    excluded = lint_exclude(load_marker(hub))
    kept, dropped = [], 0
    for issue in report.get("issues", []):
        raw = str(issue.get("path", ""))
        path = Path(raw) if os.path.isabs(raw) else hub / raw
        try:
            relative = path.resolve().relative_to(hub).as_posix()
        except (OSError, ValueError):
            relative = raw
        if any(relative == prefix.rstrip("/") or relative.startswith(prefix) for prefix in excluded):
            dropped += 1
            continue
        kept.append(issue)
    errors = sum(issue.get("severity") == "error" for issue in kept)
    warnings = sum(issue.get("severity") == "warning" for issue in kept)
    return {
        "available": True,
        "status": "error" if errors else ("warning" if warnings else "healthy"),
        "summary": {"errors": errors, "warnings": warnings},
        "excluded_prefixes": excluded,
        "excluded_issues": dropped,
        "issues": kept,
    }


def plan_push(hub: Path, project_id: str, repo: Path, prune: bool, doctor_override: str | None,
              skip_doctor: bool, allow_dirty: bool) -> dict[str, Any]:
    marker = load_marker(hub)
    actions: list[dict[str, Any]] = []
    blocked: list[str] = []
    repo_marker_path = repo / REPO_MARKER
    if not is_git_repository(repo):
        blocked.append("target is not a git repository")
    if not repo_marker_path.is_file():
        blocked.append(
            f"Project Context is not installed in that repository (no {REPO_MARKER}); run `init` first"
        )
    globals_, global_skipped = shareable(hub, marker)
    blueprints, blueprint_skipped = blueprint_files(hub, project_id)
    files = globals_ + blueprints
    over_budget = check_budgets(files, budgets(marker))
    if over_budget:
        for finding in over_budget:
            blocked.append(
                f"over budget: {finding['path']} is {finding['words']} words, "
                f"limit {finding['limit']}; trim {finding['over_by']} words"
            )

    dirty: list[str] = []
    if is_git_repository(hub):
        dirty = git_dirty_paths(hub, "global", f"projects/{project_id}/blueprint")
        if dirty and not allow_dirty:
            blocked.append(
                "the Hub has uncommitted changes in what would be pushed "
                f"({', '.join(dirty[:5])}); a stamp would name a commit that does not "
                "contain these bytes. Commit them, or pass --allow-dirty"
            )
    source_commit = git_head(hub) or "unversioned"

    doctor_report: dict[str, Any] = {"available": False, "reason": "--skip-doctor"}
    if not skip_doctor:
        doctor_report = run_doctor(hub, doctor_override)
        if doctor_report.get("available") and doctor_report.get("summary", {}).get("errors"):
            blocked.append(
                f"the Hub's doctor reports {doctor_report['summary']['errors']} error(s); "
                "fix them or pass --skip-doctor"
            )

    stamps: dict[str, Any] = {}
    if repo_marker_path.is_file():
        try:
            stamps = json.loads(repo_marker_path.read_text(encoding="utf-8")).get("pushed", {})
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            blocked.append(f"{REPO_MARKER} is not readable JSON")
        if not isinstance(stamps, dict):
            stamps = {}

    pushed: dict[str, Any] = {}
    if not blocked:
        for relative, content in files:
            destination = repo / "project-context" / relative
            pushed[relative] = {
                "sha256": digest(content), "source_commit": source_commit, "pushed_at": utc_now(),
            }
            if destination.is_symlink():
                actions.append({"kind": "conflict", "path": str(destination), "reason": "destination is a symlink"})
                continue
            current = read_text(destination)
            if current is None and destination.exists():
                actions.append({"kind": "conflict", "path": str(destination),
                                "reason": "destination exists and is not readable UTF-8 text"})
                continue
            if current is None:
                actions.append({"kind": "create", "path": str(destination), "content": content,
                                "relative": relative, "diff": unified("", content, relative)})
                continue
            if current == content:
                pushed[relative]["pushed_at"] = stamps.get(relative, {}).get("pushed_at", pushed[relative]["pushed_at"])
                actions.append({"kind": "unchanged", "path": str(destination), "relative": relative,
                                "reason": "copy matches the Hub"})
                continue
            recorded = stamps.get(relative, {}).get("sha256")
            if recorded is None:
                actions.append({"kind": "conflict", "path": str(destination), "relative": relative,
                                "reason": "a file is already there with no stamp; this push did not put it there"})
                continue
            if recorded != digest(current):
                actions.append({"kind": "conflict", "path": str(destination), "relative": relative,
                                "reason": "the copy was edited in the repository; the place to change it is the Hub"})
                continue
            actions.append({"kind": "update", "path": str(destination), "content": content,
                            "relative": relative, "diff": unified(current, content, relative)})
        for relative in sorted(set(stamps) - set(pushed)):
            destination = repo / "project-context" / relative
            if not destination.is_file():
                continue
            actions.append(
                {"kind": "delete", "path": str(destination), "relative": relative} if prune
                else {"kind": "orphan", "path": str(destination), "relative": relative,
                      "reason": "the Hub no longer publishes this file; --prune removes it"}
            )

        marker_text = repo_marker_path.read_text(encoding="utf-8") if repo_marker_path.is_file() else "{}"
        try:
            marker_data = json.loads(marker_text)
        except json.JSONDecodeError:
            marker_data = {}
        merged = dict(marker_data)
        kept = {k: v for k, v in stamps.items() if k in pushed or not prune}
        merged["pushed"] = {**kept, **pushed}
        merged.setdefault("schema", SCHEMA)
        merged.setdefault("project_id", project_id)
        new_marker = json.dumps(merged, indent=2, sort_keys=True) + "\n"
        if new_marker == marker_text:
            actions.append({"kind": "unchanged", "path": str(repo_marker_path), "reason": "stamps are current"})
        else:
            actions.append({"kind": "update_marker", "path": str(repo_marker_path), "content": new_marker,
                            "relative": REPO_MARKER})

    changed = [a for a in actions if a["kind"] in ("create", "update", "delete", "update_marker")]
    instruction_blocks = {
        name: (repo / name).is_file() for name in ("CLAUDE.md", "AGENTS.md")
    }
    return {
        "command": "push",
        "hub": str(hub),
        "project_id": project_id,
        "repository": str(repo),
        "source_commit": source_commit,
        "hub_dirty": dirty,
        "doctor": doctor_report,
        "budget": {"over": over_budget, "words": {rel: word_count(text) for rel, text in files}},
        "skipped": global_skipped + blueprint_skipped,
        "instruction_blocks_present": instruction_blocks,
        "blocked": blocked,
        "actions": actions,
        "summary": summarise(actions),
        "changes": len(changed),
        "has_conflicts": bool(blocked) or any(a["kind"] == "conflict" for a in actions),
    }


def render_diff(report: dict[str, Any]) -> str:
    parts = []
    for action in report["actions"]:
        if action.get("diff"):
            parts.append(action["diff"])
        elif action["kind"] == "delete":
            parts.append(f"--- a/{action.get('relative', action['path'])}\n+++ /dev/null\n")
        elif action["kind"] == "update_marker":
            parts.append(f"~ {action.get('relative', action['path'])} (stamps)\n")
    return "".join(parts)


def confirm(prompt: str) -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        return input(f"{prompt} [y/N] ").strip().casefold() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def command_push(args: argparse.Namespace, hub: Path) -> tuple[int, dict[str, Any]]:
    targets, error = resolve_targets(hub, args)
    if error:
        return 2, {"command": "push", "error": error}
    reports: list[dict[str, Any]] = []
    worst = 0
    for project_id, repo in targets:
        report = plan_push(hub, project_id, repo, args.prune, args.doctor, args.skip_doctor, args.allow_dirty)
        if report["has_conflicts"]:
            worst = max(worst, 2)
        elif args.apply:
            code, gate = gated_apply(hub, project_id, repo, report, args)
            report["gate"] = gate
            worst = max(worst, code)
        reports.append(report)
    if len(reports) == 1:
        return worst, reports[0]
    return worst, {"command": "push", "hub": str(hub), "projects": reports}


def gated_apply(hub: Path, project_id: str, repo: Path, report: dict[str, Any],
                args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    """The one write into a repository the Hub does not live in.

    Every precondition is checked before a byte moves: the tree is clean, the
    branch is not the default one, the branch is new, and a person said yes to
    the diff. The last step — sending the branch to the remote — is deliberately
    not taken here. It is printed as the command to run, because a tool that
    pushes to someone else's repository on the strength of its own reasoning is
    a tool nobody should install.
    """
    if report["changes"] == 0:
        return 0, {"applied": False, "reason": "nothing to push; the repository already matches the Hub"}
    clean = git_is_clean(repo)
    if clean is None:
        return 2, {"applied": False, "reason": "could not read the repository's status"}
    if not clean:
        return 2, {"applied": False, "reason": "the repository has uncommitted changes; commit or stash them first"}
    default_branch = git_default_branch(repo)
    # One long-lived branch per repository, not one per push. Repeated syncs
    # stack commits on it and update the same pull request, which is easier to
    # review than a scatter of dated branches — and it means no force-push.
    branch = args.branch or SYNC_BRANCH
    if default_branch and branch == default_branch:
        return 2, {"applied": False, "reason": f"refusing to write on the default branch ({default_branch})"}
    already_here = git_current_branch(repo) == branch
    branch_exists = bool(git_text(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"))

    diff = render_diff(report)
    if not args.yes:
        print(diff, file=sys.stderr)
        remote_preview = git_remote(repo) or "origin"
        print(
            f"\nThis writes {report['changes']} change(s) into {repo} on branch {branch},"
            f"\npushes that branch to {remote_preview}, and opens a pull request against"
            f"\n{default_branch or 'the default branch'}. Merging stays yours.",
            file=sys.stderr,
        )
        if not confirm("Write, push, and open the pull request?"):
            return 1, {"applied": False, "reason": "declined at the confirmation prompt", "branch": branch}

    started_on = git_current_branch(repo)
    if not already_here:
        switch_args = ("switch", branch) if branch_exists else ("switch", "--create", branch)
        created = run_git(repo, *switch_args)
        if created is None or created.returncode != 0:
            return 2, {"applied": False, "reason": "could not check out the branch", "branch": branch}
    written = apply_actions(report["actions"])
    relatives = sorted({
        os.path.relpath(path, repo).replace(os.sep, "/") for path in written
    })
    add = run_git(repo, "add", "--", *relatives)
    if add is None or add.returncode != 0:
        return 2, {"applied": True, "committed": False, "branch": branch,
                   "reason": "files written but `git add` failed; the branch holds them uncommitted"}
    message = (
        f"chore(project-context): push global and blueprint from the Hub\n\n"
        f"Source-Commit: {report['source_commit']}\n"
        f"Project-Id: {project_id}\n"
    )
    commit = run_git(repo, "commit", "--quiet", "--message", message, "--", *relatives)
    committed = commit is not None and commit.returncode == 0
    upsert_registry(
        hub, project_id,
        **{
            "Path": remember_path(hub, project_id, repo),
            "Remote": git_remote(repo) or EMPTY,
            "Branch": default_branch or EMPTY,
            "Last push": utc_now(),
        },
    )
    row = next((r for r in read_registry(hub) if r["Project"] == project_id), {})
    state = refresh_state_line(
        project_dir(hub, project_id) / "SUMMARY.md",
        row.get("Last pull", EMPTY) or EMPTY, row.get("Last push", EMPTY) or EMPTY,
    )
    if state:
        apply_actions([state])
    remote = git_remote(repo) or "origin"
    result: dict[str, Any] = {
        "applied": True,
        "committed": committed,
        "branch": branch,
        "started_on": started_on,
        "files": relatives,
    }
    if not committed:
        result["pushed"] = False
        result["reason"] = "nothing was committed, so there is nothing to push"
        return 2, result

    # Push the sync branch. Never the default branch, never --force: a repeated
    # sync adds a commit to this branch rather than rewriting what is there, so
    # a reviewer's place in an open pull request survives.
    pushed = run_git(repo, "push", "--set-upstream", "origin", branch)
    if pushed is None or pushed.returncode != 0:
        result["pushed"] = False
        result["reason"] = (
            "the branch is committed locally but the push failed; "
            f"run `cd {repo} && git push --set-upstream origin {branch}` to retry"
        )
        return 2, result
    result["pushed"] = True
    result["remote"] = remote

    # The pull request. `gh` is optional: without it we have still done the
    # part that needs credentials, and the owner opens the request by hand.
    existing = gh_open_pr(repo, branch)
    if existing:
        result["pull_request"] = existing
        result["pull_request_state"] = "updated an open pull request"
    elif gh_available():
        title = f"Sync project context from the Hub ({project_id})"
        body = (
            "Pushed by `project-hub push`.\n\n"
            f"- Source commit in the Hub: `{report['source_commit']}`\n"
            f"- Project id: `{project_id}`\n"
            f"- Files: {len(relatives)}\n\n"
            "These files are the pushed set — `global/` and `blueprint/`. They are "
            "read-only in this repository: the doctor errors if one is edited here. "
            "To change any of them, raise a question or a `proposal` capsule in "
            "`project-context/`, and it reaches the owner on their next pull.\n"
        )
        args_pr = ["gh", "pr", "create", "--head", branch, "--title", title, "--body", body]
        if default_branch:
            args_pr += ["--base", default_branch]
        created_pr = subprocess.run(args_pr, cwd=repo, capture_output=True, text=True, check=False)
        if created_pr.returncode == 0:
            result["pull_request"] = created_pr.stdout.strip().splitlines()[-1] if created_pr.stdout.strip() else None
            result["pull_request_state"] = "opened"
        else:
            result["pull_request_state"] = "could not be opened automatically"
            result["pull_request_error"] = (created_pr.stderr or "").strip()[:300]
            url = compare_url(remote, branch, default_branch)
            if url:
                result["pull_request_url_to_open"] = url
    else:
        result["pull_request_state"] = "gh not installed; open it by hand"
        url = compare_url(remote, branch, default_branch)
        if url:
            result["pull_request_url_to_open"] = url

    result["next"] = [
        "review the pull request and merge it; merging stays a human act",
        f"the repository is now on {branch}; `git switch {started_on}` returns it",
    ]
    return 0, result


# --------------------------------------------------------------------------
# Target resolution shared by pull and push
# --------------------------------------------------------------------------


def resolve_targets(hub: Path, args: argparse.Namespace) -> tuple[list[tuple[str, Path]], str | None]:
    rows = read_registry(hub)
    if getattr(args, "all", False):
        targets = []
        missing = []
        for row in rows:
            repo = recall_path(hub, row["Project"], row.get("Path", EMPTY))
            if repo is None:
                missing.append(row["Project"])
            else:
                targets.append((row["Project"], repo))
        if not targets:
            return [], f"no registered repository has a readable path (missing: {', '.join(missing) or 'none registered'})"
        return targets, None
    if not args.repo:
        return [], "name a project id or a path, or pass --all"
    candidate = Path(args.repo)
    if candidate.is_dir():
        repo = candidate.resolve()
        row = next((r for r in rows if recall_path(hub, r["Project"], r.get("Path", EMPTY)) == repo), None)
        project_id = row["Project"] if row else derive_project_id(repo, git_remote(repo))
        return [(project_id, repo)], None
    row = next((r for r in rows if r["Project"] == args.repo), None)
    if row is None:
        return [], f"unknown project {args.repo!r}; it is not in {REGISTRY} and it is not a directory"
    repo = recall_path(hub, row["Project"], row.get("Path", EMPTY))
    if repo is None:
        return [], (
            f"{args.repo} is registered but this machine has no working copy of it. "
            f"Clone it, then re-run with the path, or record it in {LOCAL_CONFIG}."
        )
    return [(row["Project"], repo)], None


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hub", default=".", type=Path, help="a path inside the Hub (default: .)")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    # The same two options after the subcommand, where a person naturally types
    # them. SUPPRESS is the point: without it argparse would overwrite a value
    # given before the subcommand with the subparser's own default.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--hub", type=Path, default=argparse.SUPPRESS)
    common.add_argument("--format", choices=("json", "text"), default=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add(name: str, help_text: str) -> argparse.ArgumentParser:
        return subparsers.add_parser(name, help=help_text, parents=[common])

    init_parser = add("init", "mark a repository, install Project Context, push")
    init_parser.add_argument("repo", type=Path)
    init_parser.add_argument("--id", help="override the derived project id")
    init_parser.add_argument("--installer", help="path to the Project Context initializer")
    init_parser.add_argument("--doctor", help="path to the shared Project Context doctor")
    init_parser.add_argument("--branch", help="branch to create in the target repository")
    init_parser.add_argument("--no-push", action="store_true", help="stop after installing")
    init_parser.add_argument("--skip-doctor", action="store_true")
    init_parser.add_argument("--yes", action="store_true", help="skip the push confirmation prompt")
    mode = init_parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")

    pull_parser = add("pull", "copy a repository's authored set into the Hub")
    pull_parser.add_argument("repo", nargs="?")
    pull_parser.add_argument("--all", action="store_true")
    pull_parser.add_argument("--branch", help="read this branch instead of the default one")
    pull_parser.add_argument("--fetch", action="store_true", help="refresh remote-tracking refs first")
    pull_parser.add_argument("--prune", action="store_true", help="delete mirror files the repository no longer has")
    pull_mode = pull_parser.add_mutually_exclusive_group(required=True)
    pull_mode.add_argument("--dry-run", action="store_true")
    pull_mode.add_argument("--apply", action="store_true")

    push_parser = add("push", "send global/ and blueprint/ into a repository")
    push_parser.add_argument("repo", nargs="?")
    push_parser.add_argument("--all", action="store_true")
    push_parser.add_argument("--branch", help="branch name to create in the target repository")
    push_parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    push_parser.add_argument("--allow-dirty", action="store_true", help="push from an uncommitted Hub")
    push_parser.add_argument("--skip-doctor", action="store_true")
    push_parser.add_argument("--doctor", help="path to the shared Project Context doctor")
    push_parser.add_argument("--prune", action="store_true", help="remove copies the Hub no longer publishes")
    push_mode = push_parser.add_mutually_exclusive_group(required=True)
    push_mode.add_argument("--dry-run", action="store_true")
    push_mode.add_argument("--apply", action="store_true")

    doctor_parser = add("doctor", "the shared doctor, with the owner's window excluded")
    doctor_parser.add_argument("--doctor", help="path to the shared Project Context doctor")

    return parser.parse_args(argv)


def render_text(report: dict[str, Any]) -> str:
    lines = [f"{report.get('command', 'project-hub')}: {report.get('project_id', report.get('hub', ''))}"]
    for message in report.get("blocked", []):
        lines.append(f"  blocked: {message}")
    for entry in report.get("skipped", []):
        lines.append(f"  skipped {entry['path']}: {entry['reason']}")
    for action in report.get("actions", []):
        reason = action.get("reason")
        lines.append(f"  {action['kind']}: {action['path']}" + (f" — {reason}" if reason else ""))
    if report.get("summary"):
        lines.append("  " + ", ".join(f"{kind} {count}" for kind, count in report["summary"].items()))
    diff = render_diff(report)
    if diff:
        lines.append("")
        lines.append(diff)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    start = args.hub.resolve()
    if not start.exists():
        print(f"No such path: {start}", file=sys.stderr)
        return 2
    hub = find_hub(start)
    if hub is None:
        print(f"No {HUB_MARKER} at {start} or above it. Run this inside a Project Hub.", file=sys.stderr)
        return 2

    if args.command == "init":
        code, report = command_init(args, hub)
    elif args.command == "pull":
        code, report = command_pull(args, hub)
    elif args.command == "push":
        code, report = command_push(args, hub)
    else:
        report = {"command": "doctor", "hub": str(hub), **run_doctor(hub, args.doctor)}
        code = 1 if report.get("summary", {}).get("errors") else 0

    if args.format == "text":
        print(render_text(report))
    else:
        print(json.dumps(public_report(report), indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

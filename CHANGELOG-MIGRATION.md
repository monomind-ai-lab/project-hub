# CHANGELOG-MIGRATION

This file is written to be **applied by an agent**, not read by a person. An
agent that has read only this file should be able to bring any older Project Hub
folder up to the current version, deterministically, and say what it did.

## How to use it

1. Read `VERSION` at the root of the Hub being upgraded. That is the installed
   version. If `VERSION` is absent, the folder predates versioning: treat the
   installed version as `0.0.0`.
2. Read `VERSION` in the scaffold you are upgrading to. That is the target.
3. Find every entry below whose version is greater than installed and no greater
   than target. Apply them **oldest first**, in order. Skip the rest.
4. Announce each step before running it, as `Step N/M — <name>`, so the owner can
   stop you.
5. Run the verification block at the end of each entry. Report pass or fail per
   check.
6. Write the target version to `VERSION` only after every check passes.

## How each entry is shaped

Entries appear **newest first**. Every entry has the same seven sections, and an
agent may rely on all seven being present:

| Section | Contains |
| --- | --- |
| Summary | One paragraph. Whether the release is additive or breaking |
| Added | Every path the release introduces |
| Changed | Every path whose content or meaning changes |
| Removed | Every path the release deletes, and what replaces it |
| Path mappings | A table of old path to new path, with the operation |
| Migration recipe | Numbered, named, idempotent steps |
| Verification | Checks with pass conditions, runnable in any order |

## Rules that hold for every entry

- **Idempotent.** Running a recipe twice produces the same result as running it
  once. Every step checks before it writes.
- **Create-only by default.** A step never overwrites a file the owner may have
  edited. If a step must change an existing file, it says so explicitly in
  Changed, and it stops and asks before touching it. A file whose body is
  `<!-- project-hub:unfilled -->` is an untouched seed and may be replaced.
- **Records are never rewritten.** An upgrade may change managed files, the
  contract, and the scaffold's own documents. It never edits a record in
  `global/`, `projects/`, or `owners_window/`.
- **`owners_window/` is out of scope.** No recipe reads it, writes it, moves it,
  or checks it. Ever.
- **No network.** No recipe clones, fetches, pushes, or installs anything. If an
  upgrade needs something from outside the folder, it stops and tells the owner
  what to fetch.
- **Stop on ambiguity.** If a step finds a state the entry does not describe, it
  stops and reports. It does not guess.

---

## 0.2.0 (2026-09-05)

### Summary

Additive, and nothing in an owner's Hub has to change. The onboarding surface
that 0.1.0 shipped was not covered by the scaffold's own validator or tests —
it was carried as another workstream's files, neither required nor checked. It
is now part of what the scaffold guarantees. For an activated Hub this release
is documentation plus a stricter self-check; no record, no `global/` file, and
no project folder is touched.

Two behaviours worth knowing about. `scripts/validate_repository.py` now
refuses a scaffold that ships `HUB-OWNER.md` or vendored plugin code, and skips
both checks once `HUB-OWNER.md` exists, because that is exactly what a working
Hub has. Running the validator in your own Hub stays a pass.

And the scaffold now ships `CLAUDE.md`. It is the thin pointer step 3 would
have written, so activation finds it, sees it already names `AGENTS.md`, and
counts a skip — the step was built to be idempotent and this is that path. Any
host pointer present, shipped or written, is now checked for shape: it must
name `AGENTS.md` and stay under 40 lines. A pointer that grows into a second
copy of the contract is the failure "two layers, never three" exists to
prevent, and it is now caught rather than described.

### Added

- `CLAUDE.md` — the Claude Code host pointer. This scaffold is itself worked on
  in Claude Code, and a session opening it without one got no contract at all.
- `tests/test_onboarding.py` — the onboarding surface under test: the agent's
  tools, the prompt's seven steps and report fields, the guide set, and the
  Obsidian configuration.

### Changed

- `scripts/validate_repository.py` — requires `ADAPTER-PROMPT.md`, `CLAUDE.md`,
  `.claude/agents/hub-onboarding.md`, `.obsidian/community-plugins.json`,
  `.obsidian/core-plugins.json`, `CHANGELOG-MIGRATION.md`, and the six guides.
  Adds the never-shipped check described above, gated on `HUB-OWNER.md`, and
  the host-pointer shape check.
- `tests/test_hub_scaffold.py` — its boundary list narrows to `README.md` and
  `AGENTS.md`; the rule that the CLI must not name the onboarding surface is
  now its own test.
- `README.md`, `owners-guide.md`, `AGENTS.md` — activation now names the
  shipped agent as the first path on a host that dispatches agents from disk,
  with the paste-the-prompt route as the fallback rather than the only way.

### Removed

None.

### Path mappings

| Old path | New path | Operation |
| --- | --- | --- |
| _(none — additive release)_ | | |

### Migration recipe

#### Step 1/3 — Detect the installed version

Read `VERSION`.

- `0.1.0`: continue.
- `0.2.0` or higher: this entry is already applied. Stop, and report "already at
  0.2.0 or newer".
- Absent or lower: apply the `0.1.0` entry first, then return here.

#### Step 2/3 — Refresh the scaffold's own files

Copy these from the target scaffold, replacing what is there. Every one is a
scaffold file with no owner content in it, so this is a replace rather than a
merge — but check each against the list before writing, and skip anything the
owner has edited, reporting the skip:

- `scripts/validate_repository.py`
- `tests/test_hub_scaffold.py`
- `tests/test_onboarding.py`
- `ADAPTER-PROMPT.md`, `.claude/agents/hub-onboarding.md`, `guides/`,
  `.obsidian/community-plugins.json`, `.obsidian/core-plugins.json` — only if
  absent. If present, leave them; 0.2.0 changes none of their content.
- `CLAUDE.md` — **only if absent.** An activated Hub already has one, written
  by step 3 and possibly edited since. Never overwrite it. If it is present and
  does not name `AGENTS.md`, do not fix it: report it, because a pointer aimed
  somewhere else is the owner's decision to explain.

Do not touch `README.md`, `AGENTS.md`, or `owners-guide.md` in an activated
Hub. The owner may have personalised them at activation, and the wording
changes in this release are not worth overwriting that.

#### Step 3/3 — Record the version

Write `0.2.0` to `VERSION` and set `"version": "0.2.0"` in `.project-hub.json`.
The two must agree; a Hub whose marker and `VERSION` disagree cannot be
upgraded deterministically by the next entry.

### Verification

| Check | Passes when |
| --- | --- |
| Validator passes in place | `python3 scripts/validate_repository.py` exits 0 in this folder |
| Activation still recognised | `HUB-OWNER.md` is unchanged, and the validator did not report it |
| Onboarding intact | `.claude/agents/hub-onboarding.md` and `ADAPTER-PROMPT.md` both exist |
| Pointer is a pointer | Every host pointer file present names `AGENTS.md` and is under 40 lines |
| No vendored plugins added | This run created no `.obsidian/plugins/` directory |
| Versions agree | `VERSION` and `.project-hub.json`'s `version` both read `0.2.0` |
| Owner's window untouched | `owners_window/` has the same contents it had before the run |
| Records untouched | `global/`, `projects/`, and `registry.md` are byte-identical to before the run |

---

## 0.1.0 (2026-09-03)

### Summary

First release. Everything is new, so there is nothing to migrate: the recipe
below activates a fresh Hub rather than converting an old one. Recorded here so
that later entries have a floor to start from, and so a folder created at 0.1.0
is recognisable by an agent that finds it later.

### Added

Onboarding surface:

- `README.md` — the front door. What a Hub is, the scaffold-versus-instance
  distinction, and the one-paste start.
- `AGENTS.md` — the canonical contract. Read order, canonical paths, the three
  kinds of content, write rules, what is never touched.
- `ADAPTER-PROMPT.md` — the paste-once activation prompt. Seven steps, each
  idempotent, with a required report.
- `.claude/agents/hub-onboarding.md` — the onboarding subagent for Claude Code
  hosts. Points at `AGENTS.md`; runs `ADAPTER-PROMPT.md`.
- `guides/` — six guides, one question each: `what-the-hub-is.md`,
  `authored-and-pushed.md`, `add-a-project.md`, `owners-window.md`,
  `obsidian.md`, `bring-in-a-builder.md`.
- `.obsidian/` — configuration only: `community-plugins.json`,
  `core-plugins.json`, `app.json`, `appearance.json`. No plugin code.
- `CHANGELOG-MIGRATION.md` — this file.

Written by activation, not shipped:

- `HUB-OWNER.md` — the single source of truth for the placeholder values the
  owner supplies at activation. Lives at the root, outside the push allow-list,
  so the owner's own details can never travel into a project repository.
- A host pointer file, one of `CLAUDE.md`, `GEMINI.md`, or
  `.cursor/rules/project-hub.mdc`, depending on the host. Codex CLI gets none:
  it reads `AGENTS.md`, which is already the contract.

### Changed

None. There is no previous version.

### Removed

None.

### Path mappings

| Old path | New path | Operation |
| --- | --- | --- |
| _(none — first release)_ | | |

### Migration recipe

#### Step 1/4 — Detect the installed version

Read `VERSION`.

- Absent, or `0.0.0`: this is a fresh scaffold. Continue.
- `0.1.0` or higher: this entry is already applied. Stop, and report "already at
  0.1.0 or newer".

#### Step 2/4 — Verify this is a Project Hub

Check that `AGENTS.md` and `.project-hub.json` both exist at the root, and that
`.project-hub.json` contains `"schema": "project-context/1"`.

If either is missing, this is not a Project Hub. Stop and tell the owner what
you found. Do not create the missing file.

#### Step 3/4 — Check whether activation has already run

Check for `HUB-OWNER.md`.

- Present: activation has run. Nothing to do here. Continue to step 4.
- Absent: read `ADAPTER-PROMPT.md` and follow it end to end, then continue.

#### Step 4/4 — Record the version

Write `0.1.0` to `VERSION` if it is absent. If it already holds a value, leave
it alone and report what it holds.

### Verification

| Check | Passes when |
| --- | --- |
| Contract present | `AGENTS.md` exists at the root and is non-empty |
| Marker valid | `.project-hub.json` parses as JSON and its `schema` is `project-context/1` |
| Two layers, not three | Every host pointer file present names `AGENTS.md` and is under 40 lines |
| No vendored plugins | `.obsidian/plugins/` does not exist |
| Guides intact | All six files named under Added exist in `guides/` |
| Version recorded | `VERSION` holds `0.1.0` or higher |
| Owner's window untouched | `owners_window/` has the same contents it had before the run |

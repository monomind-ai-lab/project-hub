# Project Hub — the contract

This is the canonical contract for any agent working in this folder. Read it
before you read anything else here, and before you write anything at all.

Host files (`CLAUDE.md`, `GEMINI.md`, `.cursor/rules/`) are pointers to this
file. A pointer says where the contract is and what the host can do. It never
restates a rule from here. If a pointer and this file disagree, this file is
right and the pointer is the bug.

## What this folder is

A Project Hub: one private Git repository, owned by one person. It holds the
global tier that person authors, one folder per project they oversee, and their
own working space. It is not a project repository, and builders hold no
permission on it — not even read. See `guides/what-the-hub-is.md`.

## Read order

Read only what the task needs, in this order, and stop when you have enough.

1. `AGENTS.md` — this file.
2. `HUB-OWNER.md` — who the owner is. Absent until activation has run.
3. `global/SUMMARY.md` — the global tier in one page.
4. The one `global/` record the task touches: `IDENTITY.md`, `GUARDRAILS.md`,
   `WORKFLOWS.md`, `GOALS.md`, `RESOURCES.md`.
5. `registry.md` — every project this Hub knows about.
6. `projects/<id>/MARK.md`, then `projects/<id>/SUMMARY.md`, for the project in
   hand.
7. `projects/<id>/blueprint/EPIC.md` and `projects/<id>/blueprint/ARCHITECTURE.md`
   before writing or reviewing any plan for that project.
8. `projects/<id>/pulled/` only when you need what the builders themselves wrote.

`owners_window/` is not in the read order. Read it only when the owner names it.

## Canonical paths

| Path | Holds | Who authors it |
| --- | --- | --- |
| `global/` | Identity, guardrails, workflows, goals, resources, people, agents, skills, shared records | Owner, here |
| `projects/<id>/MARK.md` | The repo's identity: remote, default branch, host, visibility, project id, builders, tracker and CI links | Owner, here |
| `projects/<id>/SUMMARY.md` | The owner's summary of that project | Owner, here |
| `projects/<id>/blueprint/` | `EPIC.md` and `ARCHITECTURE.md` | Owner, here |
| `projects/<id>/pulled/` | A stamped copy of the repo's own records | The builders, in their repo |
| `owners_window/` | Future projects, reflections, unfinished arguments | Owner, here |
| `registry.md` | Every known repo, its mark, its last pull | The commands |
| `.project-hub.json` | Marker: schema, version, push allow-list, budgets | The commands |

## The three kinds of content

Every file here is exactly one of three things. Knowing which one tells you
whether you may write it.

| Kind | Paths | Moves | You may write it |
| --- | --- | --- | --- |
| **Pushed** | `global/`, `projects/<id>/blueprint/` | Down into project repos, by `/hub-push` | Yes — this is their authoring home |
| **Pulled** | `projects/<id>/pulled/` | Up from a project repo, by `/hub-pull` | No — it is a copy. Change it in the repo it came from |
| **Owner's own** | `owners_window/`, `projects/<id>/MARK.md`, `projects/<id>/SUMMARY.md` | Nowhere | Yes, when the owner asks |

`owners_window/` is never pushed, never linted, never pulled into. An idea
leaves it by being **promoted** — rewritten as a `blueprint/EPIC.md`, a
`global/` record, or a `MARK.md` for a repo that does not exist yet. That is a
deliberate act and an ordinary edit. See `guides/owners-window.md`.

## Write rules

1. **Create-only.** Never overwrite a record the owner wrote. Never delete one.
   If a file exists and you were going to write it, skip it and say so. The one
   exception is a **seed**: a file whose body is the line
   `<!-- project-hub:unfilled -->` is scaffolding nobody has written yet, and you
   may fill it. Delete that line only when you have put real content in the
   file. `/hub-push` skips a file that still carries it.
2. **Check, skip, report.** Every activation and every command is safe to
   re-run. Report the counts: written, skipped, unchanged.
3. **Push works from an allow-list.** `/hub-push` copies `global/` (the subset
   named in `.project-hub.json`) and `projects/<id>/blueprint/`, and nothing
   else. A folder added to this Hub later is non-pushed until the allow-list
   says otherwise.
4. **Never create a remote, never push to one, never invite anyone.**
   `/hub-push` is the single exception: it works on a branch, never the default
   branch, never force, shows the diff, and asks before it pushes. Merging that
   branch is the owner's act, not yours.
5. **No secrets, no absolute home paths, no machine names** in any file you
   write. A path in a record is repository-relative or a URL.
6. **Budgets are checked, not suggested.** `global/SUMMARY.md` ≤ 150 words,
   `blueprint/EPIC.md` ≤ 600, `blueprint/ARCHITECTURE.md` ≤ 1,200, any single
   `global/` file ≤ 400, the pushed `global/` subset ≤ 2,000 in total. Over
   budget, `/hub-push` refuses and names the file to trim.
7. **Every plan item names the epic item it serves.** A `PLAN.md` item in a
   project repo carries a `Serves:` line naming a `blueprint/EPIC.md` item. When
   you write an epic, give every item a stable ID so a plan can name it.

## What is never touched

- `owners_window/` — by the doctor, by push, by pull. No frontmatter is
  required there, no budget applies, no link is validated.
- `projects/<id>/pulled/` — by hand. It is overwritten by the next pull.
- Anything outside our own markers in a host file. Whatever `CLAUDE.md` already
  said before activation stays exactly as it was.
- `.git/`.

## Commands

| Command | CLI | Does | Writes outside this folder |
| --- | --- | --- | --- |
| `/hub-init <repo>` | `project-hub init <repo>` | Writes the mark and first summary, installs Project Context into the repo, pushes, registers it | Yes, through push |
| `/hub-pull <repo>` | `project-hub pull [repo]` | Copies that repo's own records into `projects/<id>/pulled/`, stamped | No — read-only against the repo |
| `/hub-push <repo>` | `project-hub push [repo]` | Sends `global/` and `blueprint/` into that repo, stamped. `--all` for every registered repo | Yes — branch only, diff shown, confirmation required |

The slash commands and the CLI are the same code. Use whichever the host offers.

They live in `skills/`. If they are absent, the Hub still works: it is a folder
of Markdown, and everything above is still true.

## First time here

If `HUB-OWNER.md` does not exist, this Hub has not been activated. Read
`ADAPTER-PROMPT.md` and follow it.

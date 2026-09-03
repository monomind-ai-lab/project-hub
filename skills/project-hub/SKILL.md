---
name: project-hub
description: "Use when this folder is a Project Hub — it contains .project-hub.json, global/, and projects/ — and a repository needs to be marked and onboarded, a project's records need pulling up into the Hub, or the owner's global tier and a project's blueprint need pushing down into a repository."
---

# Project Hub

This folder is one private repository, administered by the organisation's
owner. It has two jobs: it is the authority for the global tier, and it is the
owner's view of every project.

Builders hold no permission here — not even read. That is the governance model
in full: the Git host's repository permissions, and nothing else. Nothing in a
project repository ever reaches this Hub by itself. Every movement is started
by the owner, from here.

## Before anything else

A Hub is also a **Project Context install**. The record model, the record
parser, the doctor, the reference grammar, and the safe-write layer are that
product's, installed here the ordinary way and never copied into this skill. If
`.agents/skills/project-context/` is missing, install it before working here;
`project_hub.py doctor` will tell you it is missing rather than guessing.

Read `global/README.md` for what the global tier holds, and `projects/README.md`
for what a project folder holds.

## The three directions

| Command | Moves | Writes to |
| --- | --- | --- |
| `init <repo>` | marks a repository, summarises it, installs Project Context into it, pushes | the Hub, then the repository |
| `pull [repo] [--all]` | that repository's authored set → `projects/<id>/pulled/` | the Hub only |
| `push [repo] [--all]` | `global/` shareable subset and `projects/<id>/blueprint/` → the repository's `project-context/` | the repository |

```bash
python3 .agents/skills/project-hub/scripts/project_hub.py init ../some-repo --dry-run
python3 .agents/skills/project-hub/scripts/project_hub.py pull some-repo --apply
python3 .agents/skills/project-hub/scripts/project_hub.py push some-repo --dry-run
```

Every command plans first. `--dry-run` prints exactly what would happen and
writes nothing; `--apply` does it and prints the same report refreshed. Re-runs
are idempotent: a second `push` with nothing to send reports `unchanged` and
creates no branch.

## What is authored where

- **`global/`** is authored here and read-only in every repository. A builder
  who disagrees with a guardrail files a question or a `proposal` capsule in
  their own repo; it arrives here at the next `pull`.
- **`projects/<id>/blueprint/`** — `EPIC.md` and `ARCHITECTURE.md` — is
  authored here and read-only in the repository. The repository's `PLAN.md`
  names epic items with `Serves:` lines, and its doctor enforces the pair.
- **`projects/<id>/pulled/`** is a mirror. Never edit it; the next pull
  overwrites you and the place those records live is the repository.
- **`owners_window/`** is the owner's own space. Never pushed, never linted,
  never pulled into. An idea leaves it only by being promoted by hand.

## Rules this skill will not bend

1. **Push works from an allow-list.** `global/` and `blueprint/`, and within
   `global/` only what `.project-hub.json` names. A folder added here later is
   non-pushed by default. Never add a deny-list.
2. **Push is the only write into a repository the Hub does not live in**, and
   it is gated every time: the target tree must be clean, it works on the
   `pull-sync` branch and never the default branch, it never force-pushes, and
   it prints the diff and asks first. `init` writes through the same gate — its
   install and its push share one branch and one confirmation.
3. **It completes the round trip, and stops at the merge.** After committing it
   pushes `pull-sync` and opens a pull request against the default branch; an
   already-open request is updated rather than duplicated. Merging stays a
   human act, and the tool never merges.
4. **Never create a remote, never `git init`, never invite anyone.**
5. **A copy that was edited where it landed is a conflict, not an overwrite.**
   Push refuses and names the Hub as the place to change it.
6. **No secrets, no home paths, no machine names in a tracked file.** A working
   copy's location goes in `.project-hub.local.json`, which is ignored.

## Before you push

`push` refuses an over-budget subset and names the file to trim: `SUMMARY.md`
≤150 words, any other global record ≤400, the whole global subset ≤2,000,
`blueprint/EPIC.md` ≤600, `blueprint/ARCHITECTURE.md` ≤1,200. It also refuses
when the Hub has uncommitted changes in what would be sent — a stamp naming a
commit that does not contain those bytes is a lie — and when the shared doctor
reports errors here.

A seeded record still carrying `<!-- project-hub:unfilled -->` is skipped and
reported. An empty guardrail in front of every agent is worse than none.

## When something is refused

Read the `blocked` list. Every refusal names the file and what to do about it.
Do not work around it by editing the copy in the repository, by adding a
deny-list entry, or by passing `--allow-dirty` to get past a message about the
Hub being uncommitted — commit the Hub instead.

Full command reference: `docs/CLI.md`.

# Project Hub — Owner's Guide

For the **organisation owner**: the person who administers the Hub. If you work
in a project repository instead, you want the
[builder's guide](https://github.com/monomind-ai-lab/project-context/blob/main/docs/builders-guide.md)
in the Project Context repository.

Written against **0.1.0**. Everything here is built and tested unless it appears
under [Not built yet](#not-built-yet).

---

## Scaffold versus instance — read this first

Two different things share the name, and confusing them is the most common
misreading:

- **The scaffold** is this public repository. Anyone can read it. It holds the
  CLI, the templates, and the onboarding material.
- **Your Hub** is a private repository you create from it. It holds your
  organisation's guardrails and a folder for every project. **Builders have no
  access to it at all** — not write, not read.

That second sentence is the whole governance model. There is no permission
system to configure and no approval gate to trust: a builder cannot change a
guardrail because they cannot see the file. This works on GitHub Free, where
private repositories have no code owners, no protected branches, and no
required reviewers.

---

## What a Hub is for

You administer several repositories. Each has its own Project Context — its own
`NOW.md`, decisions, learnings — and that is right: the people doing the work
own the record of the work.

What you need is the other two halves. **One place to write the things that
apply everywhere** — guardrails, workflows, the skills your agents use. And
**one place to see every project at once**, without cloning six repositories
and reading six `NOW.md` files.

The Hub is both. Everything moves by your hand: you push what you author down
into repositories, and you pull their records up when you want to look.

---

## Setting one up

1. Clone or fork this scaffold into a **private** repository.
2. Open the folder in Claude Code or Codex — that is where the onboarding agent
   runs. No Obsidian plugin is needed to start.
3. Ask it to set the folder up. In Claude Code the agent ships with the
   scaffold at `.claude/agents/hub-onboarding.md`, so "set this up", "activate
   the hub", or "onboard me" dispatches it. In a host with no agent format,
   paste the contents of `ADAPTER-PROMPT.md` as your first message instead —
   it is the same seven steps.

The agent detects its host, personalises the scaffold, writes a thin host
pointer file, walks you through seeding `global/`, registers your first project,
and offers the optional Obsidian pass. Every step checks before it writes, skips
anything you have customised, and reports what it wrote against what it skipped.

The agent runs with file tools only — no shell, no network. It cannot run
`git init`, add a remote, or push, because it has nothing to run them with.
Anything touching Git is yours to run, or belongs to the `/hub-*` commands.

If you would rather read than talk, `guides/` has six short documents, each
answering one question.

### The tree

```text
global/              what reaches project repositories
  SUMMARY.md IDENTITY.md GUARDRAILS.md WORKFLOWS.md GOALS.md RESOURCES.md
  people/ agents/ skills/ shared/ OWNERS.md
owners_window/       your own space — never pushed, never linted
projects/
  <repo-id>/
    MARK.md          the repo's basic info and URLs
    SUMMARY.md       your summary of it
    blueprint/       EPIC.md and ARCHITECTURE.md — authored here, pushed down
    pulled/          a copy of that repo's own records
registry.md          every known repo, its mark, its last pull
templates/  skills/  docs/  tests/
```

---

## What reaches a project repository, and what never does

This is the decision worth understanding, because it is about exposure rather
than convenience.

| | Files | Why |
| --- | --- | --- |
| **Pushed by default** | `SUMMARY.md`, `GUARDRAILS.md`, `WORKFLOWS.md`, `skills/`, `shared/`, and the project's `blueprint/` | What a builder needs to do the work correctly |
| **Opt-in per project** | `GOALS.md`, `RESOURCES.md`, `people/`, `agents/` | Objectives across every project, internal dashboards, and a roster of people are each more sensitive than the guardrails a builder actually needs. Name one in that project's `push.global_include` when you want it there |
| **Never, at any setting** | `IDENTITY.md` | A project repository may have collaborators outside the organisation. A Hub whose configuration lists it does not get to push it — the entry is dropped and you are told |
| **Filtered automatically** | Any `README.md`; any file still carrying `<!-- project-hub:unfilled -->` | A README explains the Hub, not your organisation. An unfilled seed is a placeholder, and an empty guardrail in front of an agent is worse than no guardrail |

Push works from an **allow-list**, never a deny-list. Any folder you add to the
Hub later is non-pushed by default, and needs no special case to stay put.

---

## `owners_window/` — your own room

Where you write about anything: future projects, reflections, ideas, a
half-formed argument with yourself. Three negatives define it:

- **Never pushed.** The allow-list guarantees that structurally, not by a rule
  someone has to remember.
- **Never linted.** The doctor skips it. No frontmatter, no schema, no word
  budget. A place to think stops being one the moment it reports errors.
- **Never pulled into.**

What it does have is a way out. An idea that matures is **promoted** — a
deliberate edit turning it into `blueprint/EPIC.md` for a new project, a record
in `global/`, or a `MARK.md` for a repository that does not exist yet. Freeform
in, structured out.

---

## The commands

Run from inside the Hub. All four take `--hub` and `--format json|text`.
`init`, `pull` and `push` additionally require one of `--dry-run` or `--apply`,
so nothing writes by accident; `doctor` takes neither, because it is read-only.

### `push` — send your work down

```bash
python3 skills/project-hub/scripts/project_hub.py push notes-api --dry-run
```

The only command that writes into a repository the Hub does not live in, so it
is gated every single time:

1. The Hub itself must be clean — a stamp naming a commit that does not contain
   those bytes is a false provenance record. `--allow-dirty` overrides.
2. The target's tree must be clean, and the default branch is refused outright.
3. The unified diff is printed and you are asked. The prompt says plainly that
   this writes, pushes, and opens a pull request. `--yes` skips it; a
   non-interactive session without it is **declined**, not assumed.
4. It switches to `hub-sync`, writes, stages only its own paths, and commits
   with `Source-Commit:` and `Project-Id:` trailers.
5. It pushes `hub-sync` with `--set-upstream`.
6. It opens a pull request against the default branch. An already-open request
   for that branch is **updated, not duplicated**.

**One long-lived branch, not one per push.** Repeated syncs stack a commit on
`hub-sync` and update the same pull request — easier to review than a scatter of
dated branches, and it is why nothing here force-pushes, so a reviewer's place
in an open request survives. `--branch` overrides for a one-off.

**Merging stays with the repository.** The tool has no path to it.

`gh` is optional. Without it the push still happens and you get a compare URL to
open the request by hand.

### `pull` — bring their records up

```bash
python3 skills/project-hub/scripts/project_hub.py pull --all --apply
```

Copies each repository's own records into `projects/<id>/pulled/`, reading the
git object database rather than the working copy. A test asserts the target's
`HEAD`, status, and every file mtime are byte-identical before and after.

It writes a `STAMP.json` with repository, branch, commit, time and per-file
hashes, refreshes the registry, and reports records that disappeared as `stale`.
`--prune` deletes those. `--fetch` refreshes remote-tracking refs first;
`--branch` reads a branch other than the default.

**This is also your inbox.** Questions and proposals a builder raised arrive
here — it is the only channel they have, since they cannot reach the Hub. Its
one weakness is latency: nothing moves until you pull, so make `pull --all`
routine.

### `init` — onboard a repository that has none

```bash
python3 skills/project-hub/scripts/project_hub.py init /path/to/repo --dry-run
```

Reads the repository, writes `MARK.md` and a generated `SUMMARY.md`, installs
Project Context, then pushes — install and push sharing one branch and one
confirmation. Refused when Project Context is already installed; use `pull` or
`push` then.

It does not carry the installer. Point it at one with `--installer`, the
`PROJECT_CONTEXT_INIT` environment variable, or `tools.project_context_init` in
the marker. With none it **exits 3 having written nothing into your
repository** — the mark and registry row are still correct.

### `doctor`

```bash
python3 skills/project-hub/scripts/project_hub.py doctor
```

The shared Project Context doctor, with `owners_window/` excluded. A Hub is
itself a Project Context install, so install the protocol skill into it and the
doctor arrives with it.

---

## Budgets

Refused before anything is pushed, and the offending file is named:

`SUMMARY.md` ≤ 150 words · any one `global/` file ≤ 400 · the whole pushed
subset ≤ 2,000 · `blueprint/EPIC.md` ≤ 600 · `blueprint/ARCHITECTURE.md` ≤ 1,200

Word counts strip frontmatter, fenced code and HTML comments. All are
overridable in `.project-hub.json` — unlike the identity rule, which is not.

---

## The two plans

`blueprint/EPIC.md` is yours: what the project is for and what must be true when
it is done. `PLAN.md` in the repository is the builders': what this milestone
does about it. Two records, two authors, two audiences.

What connects them is a `Serves:` line on each plan item naming the epic item it
advances. Keep an epic under 600 words and it stays the thing people actually
read.

---

## The cost, stated plainly

A guardrail change means touching every repository. `push --all` makes it one
command, but it is N branches and N pull requests. A repository nobody has
pushed to lately is quietly stale, though the doctor reports stamp age so
"quietly" overstates it.

What you buy is that builders hold no permission on the Hub — not even read —
and that a project repository needs no network at all to work.

---

## Not built yet

- **The Hub's cross-project assembler** — asking the Hub a question spanning
  every project.
- **`review`** — the pending-items list.
- **The `Serves:` conformance check** — a convention today, not enforced.
- **A SQLite cache** — deliberately deferred until an automated query proves
  slow. Never in a project repository.

---

*Mirrored to the Owner's Guide page in Notion. When the two disagree, this file
is the one that ships with the code.*

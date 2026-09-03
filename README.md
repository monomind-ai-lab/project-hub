# Project Hub

A private folder where one person holds the context for every project they
oversee: what the organisation stands for, what each project is for, and what
the people building it have actually written down.

It is plain Markdown in a Git repository. No database, no service to log into,
no runtime dependency. An agent reads it; so can you.

## This repository is the scaffold, not a Hub

Read this bit before anything else, because it is the thing everyone gets
backwards.

- **This public repository is the scaffold.** It is a template. It contains no
  organisation's records.
- **A Hub is an instance you make from it.** You copy the scaffold into a new
  private repository of your own, and that repository is your Hub. It is
  private, and it stays private.
- **A Hub is closed to builders.** The people working in your project
  repositories hold no permission on your Hub — not write, not read. That is not
  a policy you have to enforce; it is what a private repository they were never
  invited to already does.

Nothing flows from a builder's repository into your Hub except by your own
`/hub-pull`. Nothing flows out of your Hub into a repository except by your own
`/hub-push`, on a branch, with the diff shown, after you confirm.

## What an owner gets

- **One place the global tier is authored.** Identity, guardrails, workflows,
  goals, resources. You write them once, in `global/`, and push them into the
  repositories that need them.
- **A folder per project.** Its mark (remote, branch, visibility, who builds
  it), your summary of it, and the blueprint you author for it: `EPIC.md`, the
  goal the project serves, and `ARCHITECTURE.md`, the shape it has to keep.
- **The builders' own records, brought to you.** `/hub-pull` copies each
  repository's plan, tasks, decisions, learnings and open questions into
  `projects/<id>/pulled/`. You read them here, together, without cloning
  anything.
- **A window of your own.** `owners_window/` is where you write about what is
  coming: half-formed projects, reflections, an argument with yourself. It is
  never pushed anywhere, never linted, and never pulled into.
- **No transcripts anywhere.** Sessions stay on the machine they happened on.
  What travels is a short capsule, if the builder chose to write one.

## Start

1. Make a **private** repository of your own from this scaffold, and clone it.
2. Open the folder in the tool you already work in — Claude Code or Codex.
3. Paste this as your first message:

   ```
   Read ADAPTER-PROMPT.md at the root of this folder and follow it.
   ```

The agent identifies your tool, asks you one round of questions, writes a thin
pointer file for that tool, helps you seed `global/`, registers your first
project, and offers to configure Obsidian. Then it reports what it wrote, what
it skipped, and what is still empty.

Running it again is safe. It checks before every write and skips anything you
have changed.

## What is in the folder

| Path | Holds |
| --- | --- |
| `AGENTS.md` | The contract. One file, read first, never duplicated |
| `ADAPTER-PROMPT.md` | The activation prompt you paste |
| `global/` | The global tier you author |
| `projects/<id>/` | Mark, summary, `blueprint/`, and `pulled/` |
| `owners_window/` | Yours. Never pushed, never linted |
| `registry.md` | Every repository the Hub knows about |
| `guides/` | Six short guides, one question each |
| `skills/` | The `/hub-init`, `/hub-pull` and `/hub-push` commands |
| `.obsidian/` | Configuration only. No plugin code |

## Where to go next

- `guides/what-the-hub-is.md` — and what it is not
- `guides/authored-and-pushed.md` — which files you own and which you do not
- `guides/add-a-project.md` — registering a repository
- `guides/owners-window.md` — the window, and promoting an idea out of it
- `guides/bring-in-a-builder.md` — adding a second person, without giving them
  the Hub
- `guides/obsidian.md` — what Obsidian adds, and why it is optional

`CHANGELOG-MIGRATION.md` is the upgrade log. It is written to be applied by an
agent rather than read by you.

## Obsidian is optional

The Hub is a Git repository. Obsidian is one way to look at it and one way to
write in it — backlinks, graph, search, and an in-vault agent if you install
Claudian. Nothing in the commands, the stamps, or the checks depends on it.

This scaffold ships Obsidian **configuration** and no plugin code. Plugins are
installed from Obsidian's community browser, updated by Obsidian, and licensed
to you — not vendored here, where they would go stale and drag their licences
into this distribution.

## Licence

MIT with the Commons Clause v1.0 condition. You may use, copy, modify and
distribute it, including inside your own organisation. You may not sell it, or
sell a service whose value is substantially this software. Full text in
`LICENSE`. The Commons Clause makes this not an OSI-approved open source
licence, which is worth knowing before you build on it.

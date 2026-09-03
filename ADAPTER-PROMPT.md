# ADAPTER-PROMPT — paste this into your agent

You are inside a Project Hub folder that has not been set up for the tool you
are running in. Your job is to make it usable here, without breaking anything
that is already in it, and to report exactly what you did.

Everything below is one pass. It is safe to run again tomorrow, and safe to run
in a second tool on the same folder.

## Before you start

1. Read `AGENTS.md` at the root of this folder. It is the contract. Every rule
   in it applies to you from now on.
2. Read `README.md` if you need the shape of the folder.

Do not read `owners_window/`. Do not read `projects/*/pulled/`. Neither is
needed to set up a tool, and the first is the owner's private space.

## Hard rules

1. **Do not modify, rename, or replace `AGENTS.md`.** It is the source of truth.
2. **Two layers, never three.** The contract is `AGENTS.md`. The host file is a
   thin pointer to it. Never copy a rule from `AGENTS.md` into a host file — a
   pointer that duplicates the contract is how the two drift apart.
3. **Check, skip, report.** Before every write, check whether the file already
   exists. If it does, skip it and count the skip. Never overwrite something the
   owner may have customised. Report skipped and written as separate counts.
4. **Never run `git init`, never add a remote, never push, never invite anyone.**
   Not once, not as a convenience. This folder's Git state is the owner's.
5. **Do not create any file this prompt does not name.** If a step calls for a
   file that already exists with different content, stop that step and report it.
6. **Ask the owner at most one question per step**, and only where a step says to.

## Step 1 — Identify the host

Work out which tool you are running in: Claude Code, Codex CLI, Gemini CLI,
Cursor, or a chat-only assistant with no file access.

Then check two capabilities and write down the answer to each:

- **Can this host dispatch subagents from files on disk?** Claude Code can, via
  `.claude/agents/`. If yours cannot, that is fine — say so in the pointer file
  you write in step 3, and run the onboarding in the main session instead of
  dispatching it. Do not fail, and do not invent a subagent format the host does
  not document.
- **Can this host read and write files in this folder?** If it cannot, you are
  chat-only. Skip steps 2 to 6, tell the owner that setup needs a tool with file
  access, and offer to answer questions from `AGENTS.md` in this conversation.

Record both answers. They go in the report.

## Step 2 — Personalise, once

Where the scaffold's prose has to name the owner or their organisation, it does
so with a placeholder token of the form `{{TOKEN_NAME}}`. A given release may
ship none at all — in that case this step is a no-op, and the scan below is how
you find that out rather than assuming it.

1. Search the folder for `{{` followed by capitals and underscores, in `*.md`,
   `*.json`, `*.yaml`, `*.yml` and `*.txt`. Exclude `.git/`, and exclude this
   file and `CHANGELOG-MIGRATION.md` — both describe the token format, so both
   contain examples that are not real placeholders. List the distinct tokens you
   find.
2. If there are none, personalisation has already run. Skip to step 3 and record
   the skip.
3. If there are some, ask the owner **once**, in one message, for a value for
   each distinct token. Do not ask token by token.
4. Write the answers to `HUB-OWNER.md` at the root of this folder, one line per
   token, in the format below. This file is the single source of truth for these
   values from now on. It lives at the root, not in `global/`, because the push
   allow-list covers `global/` and `blueprint/` only — so the owner's own details
   can never travel into a project repository by accident.

   ```markdown
   # Hub owner

   Written by activation. Edit the values here; nothing else records them.
   This is not `global/OWNERS.md`, which records who decides what.

   - OWNER_NAME: <value>
   - ORG_NAME: <value>
   ```

5. If `HUB-OWNER.md` already exists, do not overwrite it. Read it, use the values
   in it, and ask only for tokens it does not cover.
6. Replace every occurrence of every token, in place, across the file types
   listed in 1. Count the replacements and the files touched.

## Step 3 — Write the host pointer

Write one thin pointer file for the host you identified.

| Host | Pointer file | Note |
| --- | --- | --- |
| Claude Code | `CLAUDE.md` | |
| Codex CLI | none | Codex reads `AGENTS.md` directly, and `AGENTS.md` is already the contract. Write nothing and report "canonical file is the host file". |
| Gemini CLI | `GEMINI.md` | |
| Cursor | `.cursor/rules/project-hub.mdc` | Create `.cursor/rules/` if it is absent |
| Chat-only | none | Report that the owner should paste `AGENTS.md` at the start of each chat |

If the pointer file already exists, do not overwrite it. Read it. If it already
points at `AGENTS.md`, leave it alone and count a skip. If it does not, add the
pointer paragraph below to it and change nothing else in the file.

Use this content, with the host name substituted:

```markdown
# Project Hub — host pointer

The contract for this folder is `AGENTS.md` at the root. Read it before you do
anything else here, every session.

This file is a pointer, not a copy. Nothing substantive belongs in it. If it
ever disagrees with `AGENTS.md`, `AGENTS.md` is right.

## Host notes

- Subagents: <available, via `.claude/agents/` | not available on this host;
  onboarding and any specialist work run in the main session>
- Commands: `/hub-init`, `/hub-pull`, `/hub-push` are defined in `skills/`.
```

Nothing else goes in a pointer file. Not the read order, not the write rules,
not the path table. Those are in `AGENTS.md` and they are there once.

## Step 4 — Seed `global/`

`global/` ships already seeded. Each seeded file carries the line
`<!-- project-hub:unfilled -->` on its own until somebody writes it. That line
is how you tell a seed from the owner's work, and it is the check that makes
this step safe to re-run:

- The file carries the marker → it is an untouched seed. You may write it.
- The file does not carry the marker → the owner has written it. Skip it and
  count the skip. Do not read past what you need and do not rewrite a word.

`/hub-push` skips any file that still carries the marker, so an unanswered
question costs nothing downstream. **Delete the marker line only when you have
written real content into that file.**

Walk the owner through three things, in this order, in one conversation:

1. **Identity** — how the owner and the organisation describe what they build,
   and the defaults an agent should assume. Writes `global/IDENTITY.md`.
2. **Guardrails** — the things that must not happen, whatever the task. Each one
   phrased so an agent can check itself against it. Writes
   `global/GUARDRAILS.md`.
3. **Workflows** — how work actually moves here: review, release, who decides.
   Writes `global/WORKFLOWS.md`.

Then write `global/SUMMARY.md`, at most 150 words, routing to whichever of the
three now has content.

Rules for this step:

- **Write only what the owner answered.** If they skip identity, leave the seed
  and its marker exactly as they are. A seed that says it is unfilled is honest.
  Placeholder prose with the marker removed is a file nobody notices is empty.
- Keep each file under 400 words, and the whole pushed subset under 2,000.
  `.project-hub.json` holds the numbers; over budget, `/hub-push` refuses and
  names the file.
- `global/GOALS.md`, `global/RESOURCES.md`, `global/OWNERS.md`,
  `global/people/`, `global/agents/`, `global/skills/` and `global/shared/` are
  not part of this step. Leave their seeds alone. They are written when there is
  something to put in them.

## Step 5 — Register the first project

Ask the owner for one repository they want the Hub to know about, and whether
that repository already has Project Context installed.

- **Not installed** — run `/hub-init <repo>`. It writes the mark and first
  summary, installs Project Context in the repo, pushes the pushed set, and
  records the repo in `registry.md`.
- **Already installed** — run `/hub-pull <repo>` to bring its records in, then
  `/hub-push <repo>` when the owner has something in `global/` worth sending.
- **Not now** — skip. A Hub with no projects is a working Hub. Say which command
  to run when they are ready.

Both commands write to a repository outside this folder. They show a diff and
ask before anything is pushed. Do not bypass that, and do not push on the
owner's behalf without the confirmation the command asks for.

If `skills/` does not contain these commands, say so and stop this step. Do not
reimplement them.

## Step 6 — Offer Obsidian

Obsidian is optional. The Hub is a Git repository full of Markdown and works
without it. Say that first, then say what it adds: backlinks between records,
graph and search across every project, and — with the Claudian plugin — an agent
inside the vault, so the owner can write and ask in the same window.

If the owner says no, stop here. The Hub is working.

If the owner says yes:

1. Tell them to open this folder as a vault: Obsidian → **Open folder as vault**
   → choose this folder.
2. Tell them to install the plugins from inside Obsidian: **Settings → Community
   plugins → Browse**, search, install, enable. The plugin IDs this scaffold
   recommends are listed in `.obsidian/community-plugins.json`, Claudian
   (`realclaudian`) first. Claudian is MIT-licensed and desktop-only.
3. Do not download, vendor, or write any plugin code into this folder. No
   `.obsidian/plugins/` directory. Plugins are installed by Obsidian, updated by
   Obsidian, and licensed to the owner, not to this repository.
4. `.obsidian/` already holds the configuration this scaffold recommends. If a
   file in it already exists, leave it alone — the owner's own settings win.

See `guides/obsidian.md` for what to say if they ask what it actually buys them.

## Step 7 — Report back

Report exactly these fields. Numbers, not adjectives.

- **HOST:** which tool, and which model
- **SUBAGENTS:** available, or not available and where you noted it
- **PERSONALISATION:** ran / skipped (already personalised). Tokens found,
  replacements made, files touched, and whether `HUB-OWNER.md` was written or
  already existed
- **POINTER FILE:** the path written, or "skipped — already points at AGENTS.md",
  or "none needed — canonical file is the host file"
- **GLOBAL SEEDED:** each file written, each skipped and why, and which files
  still carry `<!-- project-hub:unfilled -->`
- **PROJECT REGISTERED:** the repo id and the command run, or "none yet"
- **OBSIDIAN:** configured / declined / already configured. Confirm no plugin
  code was written
- **FILES WRITTEN:** every path
- **FILES SKIPPED:** every path, with the reason
- **AGENTS.md:** confirm you did not modify, rename, or replace it
- **NEXT:** the one command worth running next, and why

If a step failed or a rule was broken, say so plainly and name the step. A
half-finished activation that is reported is recoverable. One that is not is not.

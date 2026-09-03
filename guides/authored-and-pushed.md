# The authored set and the pushed set

**One question: which files may I edit, and where?**

Every record in this system has exactly one authoring home. The rule is not a
convention — a check enforces it, and it will tell you when you have broken it.

## The two sets, in a project repository

| Set | Files | Written by | Arrives how |
| --- | --- | --- | --- |
| **Authored** | `SUMMARY.md`, `NOW.md`, `PLAN.md`, `tasks/`, `DECISIONS.md`, `decisions/`, `LEARNINGS.md`, `QUESTIONS.md`, `questions/`, `inbox/`, `indexes/` | Builders, in the repo | They write it there |
| **Pushed** | `global/`, `blueprint/` (`EPIC.md` and `ARCHITECTURE.md`) | The owner, in the Hub | `/hub-push`, as a commit on a branch |

The pushed set is read-only in the repository. Each pushed file's hash is
recorded in the marker when it lands. If someone edits one, the check fails and
names the Hub as the place to make that change.

## The mirror image, in the Hub

`global/` and `projects/<id>/blueprint/` are authored here — this is their home,
edit them freely. `projects/<id>/pulled/` is the copy that came up from a
repository; do not edit it, because the next pull overwrites it. Change the
record where it was written.

## Why split it this way

Because it makes the permission model trivial. Builders can write everything
they are allowed to write and nothing they are not, and the Git host's ordinary
repository permissions are the whole mechanism. No approval gate, no reviewer
config, no feature that private repositories on a free plan do not have.

## What a builder does when a pushed record is wrong

They cannot edit it, and they should not try. They file a question in
`QUESTIONS.md`, or capture a `proposal` capsule in `inbox/`. Both are part of
the authored set, so the next `/hub-pull` brings them here, alongside the
project context that explains why. The owner reads it and changes the record at
its source.

The weak point is latency: nothing moves until the owner pulls. So pull often,
and read the oldest unanswered question first.

## One more rule that follows from this

Every `PLAN.md` milestone item carries a `Serves:` line naming an item in
`blueprint/EPIC.md`. The epic says what the project is for; the plan says what
this milestone does about it. A plan item that serves nothing is work the epic
never asked for — that is an error, and the fix is either to anchor it or to
raise a question about the epic.

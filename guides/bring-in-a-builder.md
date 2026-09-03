# Bringing in a builder

**One question: someone else is joining a project — what do I do?**

Almost nothing, and that is the design working. A builder needs access to the
project repository they are working in. They need no access to the Hub, and you
should not give them any.

## The steps

1. **Add them to the project repository** on your Git host, the way you already
   would. Write access to that repository, and nothing else.
2. **Check the repository has Project Context installed.** If it does not, run
   `/hub-init <repo>` from the Hub first. If it does, run `/hub-push <repo>` so
   they start with a current global tier and blueprint.
3. **Record them in `projects/<id>/MARK.md`**, under the builders it lists. This
   is how the Hub knows who is on a project; it grants nothing.
4. **Tell them to read the repository's own `AGENTS.md`.** The managed block
   Project Context maintains there says everything they need: read `NOW.md` and
   `PLAN.md` before substantial work, read `blueprint/` before planning, and do
   not edit the pushed set.

That is all. There is no invitation to send, no Hub permission to grant, and no
approval file to edit.

## What they can and cannot do

They can write everything in the authored set: the plan, tasks, decisions,
learnings, questions, the inbox. They cannot edit `global/` or `blueprint/` —
the check will refuse and name the Hub. They cannot see the Hub at all: not
your other projects, not `owners_window/`, not the global records you have not
pushed to their repository.

## How they push back

A builder who thinks a guardrail, an epic item, or an architecture record is
wrong files a question in `QUESTIONS.md`, or captures a `proposal` capsule in
`inbox/`. Both are in the authored set, so your next `/hub-pull` brings them up
with the project context that explains them. You change the record at its
source, then push.

It costs them no permission, no fork, and no pull request against a repository
they cannot see. The cost is yours: nothing moves until you pull. Make
`/hub-pull --all` a routine, and read the oldest unanswered question first.

## What never happens

You never invite a builder to the Hub — not read-only, not "just for the
guardrails". The moment someone can read the Hub, the Hub is no longer the
place you can write freely about the projects they work on. That is what
`owners_window/` is for, and it only works while nobody else is in the room.

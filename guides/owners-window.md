# The owner's window

**One question: where do I put an idea that is not a project yet?**

`owners_window/` is your space. Future projects, reflections, a half-formed
argument with yourself, the thing you will regret not writing down. It sits
next to the content that goes down to repositories and the content that comes
up from them, and it is the only part of the Hub defined by what does *not*
happen to it.

## Three negatives

- **Never pushed.** `/hub-push` copies `global/` and `blueprint/`, and nothing
  else. It works from an allow-list, not a deny-list, so this is a property of
  the mechanism rather than a rule someone has to remember. Any folder added to
  the Hub later is non-pushed until the allow-list says otherwise.
- **Never linted.** No required frontmatter, no record schema, no word budget,
  no link validation. A place to think stops being one the moment it starts
  reporting errors.
- **Never pulled into.** `/hub-pull` writes only to `projects/<id>/pulled/`.

Write however you like in here. There is no template and no naming convention.

## What agents may do with it

An agent working in the Hub reads `owners_window/` only when you name it — for
instance when you ask what is coming next. It is not in the read order in
`AGENTS.md`, and no project's context packet can reach it, because nothing here
is pushed.

## Promotion: the way out

An idea that matures leaves the window by being **promoted**. Promotion is a
deliberate act and an ordinary edit — nothing automates it, and nothing should.

An idea becomes one of three things:

| It has become | Write it as |
| --- | --- |
| A project that should exist | `projects/<id>/MARK.md`, then `blueprint/EPIC.md` |
| A rule that applies everywhere | A record in `global/` — usually `GUARDRAILS.md` or `WORKFLOWS.md` |
| A change of direction for a project that exists | An edit to that project's `blueprint/EPIC.md` |

Freeform in, structured out. When you promote, the note in `owners_window/` has
done its job — delete it or leave it as the record of how you got there, as you
prefer. Nothing checks.

## The one thing to watch

Budgets apply to what you promote, not to what you write here. An epic is 600
words; a guardrail file is 400. `/hub-push` refuses an over-budget file and
names it, before it reaches a single repository. So promotion is where the
thinking gets compressed, and that compression is the point.

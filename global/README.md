# `global/` — the tier the owner authors once and every project inherits

This folder is the authority for everything true across all projects. It is
edited **here and only here**. `project-hub push <repo>` copies the shareable
subset of this folder into a project repository's `project-context/global/`,
where it is read-only: the doctor in that repository errors if a copy is edited
locally and names this Hub as the place to change it.

Push works from an **allow-list**, not a deny-list. The list lives in
`.project-hub.json` under `push.global_include`. A file in this folder that is
not on that list is not pushed — including this README and `OWNERS.md` — and
any file or folder added here later is not pushed until it is listed.

## What each file holds

| File | Holds | Pushed |
| --- | --- | --- |
| `SUMMARY.md` | The L0 route: what this organisation is, in ≤150 words. Loaded into every session in every project. | yes |
| `IDENTITY.md` | Who we are, what we build, who it is for, the voice. | **never** |
| `GUARDRAILS.md` | The rules that hold everywhere. Each one is a constraint an agent can check itself against, not an aspiration. | yes |
| `WORKFLOWS.md` | How work moves: the shapes of a change, a review, a release. | yes |
| `GOALS.md` | What the organisation is trying to be true by when. | opt-in |
| `RESOURCES.md` | Where the shared things are: hosts, trackers, environments, accounts by name — never a credential. | opt-in |
| `OWNERS.md` | Who owns what. A record for people and for `review`, **not** an enforcement mechanism. Governance is the Git host's repository permissions. | no |
| `people/` | One record per person the projects should know about. | opt-in |
| `agents/` | One record per agent: what it may do, what it may never do. | opt-in |
| `skills/` | One record per shared skill, versioned, with `learned_from` links. | yes |
| `shared/` | Records that are global but fit none of the above. | yes |

**never** and **opt-in** are not the same thing.

`IDENTITY.md` is never pushed, at any setting — decision D9. Identity is the
owner's or the organisation's voice and defaults, and a project repository may
have outside collaborators in it. A Hub whose `push.global_include` names
`IDENTITY.md` does not get to push it: the entry is dropped and `/hub-push`
reports the refusal rather than obeying quietly. It reaches the owner's own
packet, here in the Hub, and nowhere else.

**opt-in** means not pushed by default and pushable per project. Objectives
across every project, internal hosts and environments, and a roster of people
are each more sensitive than the guardrails a builder actually needs in order
to do the work — so an owner who wants one of them in a particular repository
names it in that project's `push.global_include`.

## Budgets

`SUMMARY.md` ≤ 150 words. Every other file in the pushed subset ≤ 400 words,
and the whole pushed subset ≤ 2,000 words. `push` refuses an over-budget
subset and names the file to trim, before it reaches a single repository. The
numbers live in `.project-hub.json` under `push.budget_words`.

## Unfilled seeds

A seeded file carries the line `<!-- project-hub:unfilled -->` until someone
writes it. `push` skips a file that still carries it — an empty guardrail is
worse than no guardrail — and `project_hub.py status` lists what is still
waiting. Delete the line when you write the file.

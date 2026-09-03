# Adding a project

**One question: how do I get a repository into the Hub?**

There are two starting points. Which one you are in depends on whether the
repository already has Project Context installed — look for a
`project-context/` folder at its root.

## The repository has no Project Context yet

Run `/hub-init <repo>`. In order, it:

1. Reads the repository and writes `projects/<id>/MARK.md` — remote, default
   branch, host, visibility, languages, entry points.
2. Writes `projects/<id>/SUMMARY.md`, a first draft of what the project is and
   where it stands. Edit it; it is yours.
3. Installs Project Context into the repository, including the managed block in
   both its `CLAUDE.md` and its `AGENTS.md`.
4. Runs `/hub-push` for it, so the repository starts with your global tier and
   its blueprint.
5. Records it in `registry.md`.

It stops at the first failure, and it refuses outright if Project Context is
already installed. Steps 3 and 4 write to a repository outside the Hub: they
work on a branch, never the default branch, show you the diff, and ask before
pushing. Merging that branch is your job, not the tool's.

## The repository already has Project Context

Run `/hub-pull <repo>` first. It copies the repository's own records into
`projects/<id>/pulled/`, stamped with repository, branch, commit and time, and
updates the summary's state line and the registry. It is read-only against the
repository — it clones or fetches and writes nothing there.

Then write `projects/<id>/blueprint/EPIC.md` and `ARCHITECTURE.md`, and run
`/hub-push <repo>` when you have something worth sending.

## After that

- `/hub-pull --all` is the routine that catches you up on every registered
  repository. Run it before you read.
- `/hub-push --all` is what you run after editing a guardrail. Be aware of the
  cost: it is one branch and one merge per repository, and a repository nobody
  merges goes quietly stale. The check reports how old each stamp is, so
  "quietly" is the wrong word in practice.

## What you need before either command

Write access to the repository for `/hub-init` and `/hub-push`. Read access is
enough for `/hub-pull`. You already have both, because you administer the
repository — that is the whole permission story, and there is nothing else to
configure.

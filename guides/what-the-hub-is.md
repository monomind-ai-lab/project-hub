# What the Hub is, and what it is not

**One question: what am I looking at?**

A Project Hub is one private Git repository, owned by one person. It holds
three things: the global tier that person authors, a folder for each project
they oversee, and their own working space.

That is the whole idea. Everything else in this scaffold is machinery for
getting content into those three places and out again safely.

## What it is

- **The authoring home of the global tier.** Identity, guardrails, workflows,
  goals, resources. Written here, once, and copied down into project
  repositories by `/hub-push`.
- **The owner's view of every project.** For each one: a mark (its remote,
  branch, visibility, who builds it), a summary, a blueprint the owner writes,
  and a copy of what the builders wrote, brought up by `/hub-pull`.
- **A folder of Markdown in Git.** You can read it in any editor, grep it,
  and open it on a machine with no agent installed.

## What it is not

- **Not a project repository.** No code, no builds, no issues. Project Context
  is the thing that lives in a project repository; the Hub is the other side.
- **Not shared with builders.** They hold no permission on it, not even read.
  If you need them to see something, push it into their repository.
- **Not a place transcripts go.** Sessions stay local. What may travel is a
  short capsule, at most 200 words, and only if someone wrote one.
- **Not a database or a service.** There is nothing to run, nothing to log
  into, and no dependency to install.
- **Not required by a project repository.** A repo with Project Context and no
  Hub is a complete, working, offline product. The Hub is created deliberately
  by someone who wants the aggregate view. It never appears on its own.

## The one thing worth remembering

Content moves in exactly two directions, and the owner starts both of them.
Down, with `/hub-push`: the global tier and a project's blueprint go into a
repository. Up, with `/hub-pull`: a repository's own records come here as a
stamped copy. There is no third path, and no builder-initiated one.

Next: `authored-and-pushed.md`.

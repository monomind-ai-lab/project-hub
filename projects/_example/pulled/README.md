# `pulled/` — the mirror

`project_hub.py pull notes-api` writes the repository's **authored set** here,
verbatim: `SUMMARY.md`, `NOW.md`, `PLAN.md`, `tasks/`, `DECISIONS.md`,
`decisions/`, `LEARNINGS.md`, `QUESTIONS.md`, `questions/`, `inbox/`, and
`indexes/`.

That list is an allow-list, which is why `sessions/` never arrives here, and
why neither does the pushed set the Hub sent down in the first place — copying
`global/` back up would make a round trip out of a one-way flow.

Alongside the copy, `STAMP.json` records the repository, the branch, the commit
and the time it was read, plus a `sha256` per file. That is the provenance: a
pulled record is only as current as the commit it came from.

Do not edit anything here. The next pull overwrites it, and the place those
records are authored is the repository. A pulled `questions/` or `inbox/` is
the builders' feedback channel arriving — read it, answer it in `global/` or in
`blueprint/`, and push the answer down.

This folder is empty until the first pull.

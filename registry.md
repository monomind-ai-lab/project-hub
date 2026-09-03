# Registry

Every repository this Hub knows about. `init` adds a row, `pull` and `push`
refresh one. The table is read and written by
`skills/project-hub/scripts/project_hub.py`, so keep the header and the column
order; everything below the table is yours.

| Project | Path | Remote | Branch | Last pull | Last push |
| --- | --- | --- | --- | --- | --- |

## How a row is filled

- **Project** — the project id, which is the folder name under `projects/`.
- **Path** — a local working copy the owner can read. Relative to this Hub
  where that makes sense, absolute only on the owner's own machine and never
  committed as a home path. `—` when only a remote is known.
- **Remote** — the fetch URL.
- **Branch** — the default branch, the one `pull` reads.
- **Last pull** / **Last push** — UTC timestamps, `—` when it has not happened.

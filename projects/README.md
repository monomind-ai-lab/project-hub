# `projects/`

One folder per repository the owner knows about, named by its project id.

| File | Authored by | Direction |
| --- | --- | --- |
| `MARK.md` | `project_hub.py init`, then the owner | stays here |
| `SUMMARY.md` | generated first draft, then the owner | stays here |
| `blueprint/EPIC.md` | the owner | pushed down |
| `blueprint/ARCHITECTURE.md` | the owner | pushed down |
| `pulled/` | `project_hub.py pull` | pulled up, never edited here |

`pulled/` is a mirror of the repository's authored set. Edit it and the next
pull overwrites you; the place to change those records is the repository.

A folder whose name starts with `_` is a worked example, not a project. The
commands skip it, and `registry.md` does not list it. `projects/_example/` is
here to be read and then deleted.

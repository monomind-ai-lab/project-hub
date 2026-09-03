# `project_hub.py` — command reference

```text
python3 skills/project-hub/scripts/project_hub.py [--hub PATH] [--format json|text] <command> [...]
```

Zero runtime dependencies, Python 3.11+, standard library only. `--hub` may be
any path inside the Hub; the tool walks upward for `.project-hub.json` and
refuses to run if it does not find one. `--hub` and `--format` may be given
before or after the subcommand.

Every command plans before it writes. `--dry-run` prints the plan and touches
nothing; `--apply` performs it and prints the plan again, refreshed. Re-runs
are idempotent. Exit codes:

| Code | Means |
| --- | --- |
| 0 | done, or nothing to do |
| 1 | declined at the confirmation prompt, or the doctor found errors |
| 2 | refused: a conflict, a blocked precondition, or a bad argument |
| 3 | `init` got as far as it could and stopped at the install step |

## `init <repo>`

Onboards a repository that has **no** Project Context yet. Five steps, in
order, stopping at the first failure.

1. Reads the repository and derives a project id — the remote's repository
   name slugified, or the directory name. `--id` overrides it.
2. Writes `projects/<id>/MARK.md` from `templates/project/MARK.md`: remote,
   host, default branch, visibility, languages, entry points.
3. Writes `projects/<id>/SUMMARY.md`, a generated first draft the owner edits,
   and registers the project in `registry.md`.
4. Installs Project Context into the repository.
5. Pushes the global tier and this project's blueprint.

Steps 1 to 3 touch only the Hub. Steps 4 and 5 both write to someone else's
repository, so they share **one gate, one branch, and one confirmation** —
`project-hub/init-<id>-<YYYYMMDD>` unless `--branch` names another. Installing
on one branch and pushing on another would leave the install uncommitted and
the push refusing the tree it had just dirtied. The install is committed as
`chore(project-context): install Project Context`, the push as a second commit
on the same branch, and then it stops: `"pushed": false`, and the command to
send the branch is printed.

```bash
project_hub.py init ../notes-api --dry-run
project_hub.py init ../notes-api --apply
project_hub.py init ../notes-api --apply --no-push        # stop after the install
project_hub.py init ../notes-api --apply --id notes-api   # name it yourself
```

| Option | Does |
| --- | --- |
| `--id ID` | override the derived project id |
| `--installer PATH` | where the Project Context initializer is |
| `--branch NAME` | the branch to create in the target repository |
| `--no-push` | stop after step 4, on the branch, install committed |
| `--yes` | skip the confirmation prompt |
| `--skip-doctor` | do not run the shared doctor before pushing |

**Refused** when the repository already has `project-context/.project-context.json`
— `push` is the right command then — when the target is not a git repository,
when the derived id is not a slug or starts with `_`, when the target's working
tree is dirty, when the branch would be the default branch or already exists,
and when a non-interactive session did not pass `--yes`.

If the initializer itself fails, the command exits **3** and says so: the
repository is left on the branch holding whatever the initializer wrote, which
is recoverable with one `git switch` and one branch delete.

`MARK.md` and `SUMMARY.md` are create-only. An existing one is reported as
`preserve_existing` and left exactly as it was.

### Finding the initializer

A Hub carries the Project Context **protocol** skill, not its installer: a
consuming repository never needs its own copy of the thing that installed it.
So `init` has to be told where the initializer lives, and asks in this order:

1. `--installer PATH`
2. the `PROJECT_CONTEXT_INIT` environment variable
3. `tools.project_context_init` in `.project-hub.json`
4. `project-context` on `PATH`

If none answers, `init` exits **3** after step 3. The mark, the summary, and
the registry row are written and correct; nothing was written to the
repository. Point it at the initializer and re-run — the create-only plan makes
the second run safe.

## `pull [repo] [--all]`

Copies a repository's **authored set** into `projects/<id>/pulled/`.

```bash
project_hub.py pull notes-api --dry-run
project_hub.py pull notes-api --apply
project_hub.py pull ../notes-api --apply          # by path instead of id
project_hub.py pull --all --apply
project_hub.py pull notes-api --apply --fetch     # refresh remote-tracking refs first
project_hub.py pull notes-api --apply --prune     # delete mirror files the repo no longer has
```

**Read-only against the repository.** It reads the default branch through
`git ls-tree` and `git show`, which touch the object database and never the
working tree, the index, or a branch. `--fetch` is the only thing that reaches
the network, and it writes only remote-tracking refs in the owner's own clone.

The authored set is an allow-list — `SUMMARY.md`, `NOW.md`, `PLAN.md`,
`tasks/`, `DECISIONS.md`, `decisions/`, `LEARNINGS.md`, `QUESTIONS.md`,
`questions/`, `inbox/`, `indexes/`. Everything else is excluded because it is
not on the list, which is why `sessions/`, the marker, the protocol text, and
the whole pushed set never arrive here. Symlinks and submodules in the tree are
skipped and reported, never followed.

Alongside the mirror, `pulled/STAMP.json` records the repository, the branch,
the commit, the time, and a `sha256` per file. A pull that finds nothing new
rewrites nothing, including the stamp.

`pull` also writes `projects/<id>/MARK.md` if it is absent — a pulled project
with no mark is unaddressable — refreshes the managed state line in
`projects/<id>/SUMMARY.md` if that file has one, and updates the registry's
last-pull column.

| Option | Does |
| --- | --- |
| `--all` | every registered repository with a readable working copy |
| `--branch NAME` | read this branch instead of the default one |
| `--fetch` | `git fetch origin` in the owner's clone first |
| `--prune` | delete mirror files the repository no longer has (default: report them as `stale`) |

## `push [repo] [--all]`

Copies the Hub's shareable `global/` subset and `projects/<id>/blueprint/` into
the repository's `project-context/`, and writes the stamps into that
repository's marker.

```bash
project_hub.py push notes-api --dry-run           # plan and full diff
project_hub.py push notes-api --apply             # gated; prompts before writing
project_hub.py push --all --dry-run
```

**This is the only write into a repository the Hub does not live in.**

### What is sent

An allow-list, three filters deep:

1. `.project-hub.json` → `push.global_include` names what may leave `global/`.
   Anything not named is not sent. `owners_window/`, `templates/`, `docs/`,
   `skills/`, and any folder added to the Hub later are non-pushed by default
   and need no rule to stay that way. `OWNERS.md` is deliberately not on the
   list: it is a governance record for the owner and for `review`.
2. Any `README.md` is skipped — a README explains the Hub, not the
   organisation.
3. A record still carrying `<!-- project-hub:unfilled -->` is skipped and
   reported. An empty guardrail in front of every agent is worse than none.

`projects/<id>/blueprint/**/*.md` is sent whole, minus the same two filters.

### Budgets

Checked before anything moves. Over budget is a refusal naming the file and how
many words to trim.

| Path | Words |
| --- | --- |
| `global/SUMMARY.md` | 150 |
| any other global record | 400 |
| the whole global subset | 2,000 |
| `blueprint/EPIC.md` | 600 |
| `blueprint/ARCHITECTURE.md` | 1,200 |

Frontmatter, fenced code, and HTML comments are not counted. The numbers live
in `.project-hub.json` under `push.budget_words`.

### Refusals

| Condition | Why |
| --- | --- |
| No `project-context/.project-context.json` in the repository | Project Context is not installed; run `init` |
| A copy's hash does not match its stamp | it was edited where it landed; the place to change it is the Hub |
| A file is already at the destination with no stamp | this push did not put it there |
| The Hub has uncommitted changes in what would be sent | the stamp would name a commit that does not contain those bytes (`--allow-dirty` to override) |
| The shared doctor reports errors in the Hub | fix them, or `--skip-doctor` |
| Over budget | trim the named file |
| The target's working tree is dirty | commit or stash first |
| The branch would be the default branch | push works on a branch, always |
| The branch already exists | pass `--branch <name>` |
| A destination is a symlink | never followed |

### The gate

On `--apply`, in this order:

1. Nothing to send → says so and stops. No branch is created.
2. The target's tree must be clean; the branch must not be the default branch;
   the branch must not already exist.
3. The unified diff is printed and a person is asked. `--yes` skips the prompt;
   without it, a non-interactive session is declined rather than assumed.
4. `git switch --create project-hub/push-<id>-<YYYYMMDD>`, the files are
   written, only those paths are staged, one commit is made carrying
   `Source-Commit:` and `Project-Id:` trailers.
5. **It stops.** The report says `"pushed": false` and
   `"would push branch <name> to <remote>"`, and lists the exact commands to
   send it and to get back to the branch you started on.

Sending the branch to the remote and merging it are human acts. This tool
never runs `git push`, never force-pushes, never creates a remote, and never
runs `git init`.

`push` does not write the managed blocks in `CLAUDE.md` and `AGENTS.md`. That
text belongs to Project Context and there is one copy of it; a second copy here
would drift. The report says whether each file is present so the owner can run
the initializer or `/projectcontext-update` if one is missing.

| Option | Does |
| --- | --- |
| `--all` | every registered repository with a readable working copy |
| `--branch NAME` | the branch to create in the target |
| `--yes` | skip the confirmation prompt |
| `--allow-dirty` | push from a Hub with uncommitted changes in the sent set |
| `--skip-doctor` | do not run the shared doctor first |
| `--prune` | remove copies the Hub no longer publishes |

## `doctor`

The shared Project Context doctor, run on the Hub, with `owners_window/`
excluded.

```bash
project_hub.py doctor
project_hub.py doctor --doctor ../project-context/skills/project-context/scripts/context_doctor.py
```

It is a delegation, not a second doctor: there is one record model and one set
of issue codes, and a Hub is an ordinary Project Context install, so the check
it runs on itself is the same code every repository runs. The module is found
at `.agents/skills/project-context/scripts/context_doctor.py`, or wherever
`PROJECT_CONTEXT_DOCTOR` or `--doctor` says.

Issues whose path falls under any prefix in `.project-hub.json` →
`lint.exclude` are dropped before the summary, and the count of dropped issues
is reported. `owners_window/` is the only entry, and it is why the owner's own
space is never linted: a place to think stops being one the moment it starts
reporting errors.

When the doctor cannot be found, the report says so and why. Nothing is
guessed, and no substitute check runs in its place.

## The registry

`registry.md` holds one row per known repository. `init` adds a row; `pull` and
`push` refresh one. The tool rewrites only the table — anything a person wrote
around it survives.

The `Path` column holds a Hub-relative path when there is one. When the working
copy is somewhere else on the owner's machine, the column shows `—` and the
real location goes into `.project-hub.local.json`, which is ignored by Git.
That is deliberate: an absolute home path in a tracked file is exactly the kind
of thing this product must never carry.

## `.project-hub.json`

```json
{
  "schema": "project-context/1",
  "version": "0.1.0",
  "registry": "registry.md",
  "lint":  { "exclude": ["owners_window/"] },
  "push":  { "global_include": ["SUMMARY.md", "…", "shared/"],
             "budget_words":   { "global_total": 2000, "…": 0 } },
  "tools": { "project_context_init": "../project-context/skills/project-context-init/scripts/project_context_init.py" }
}
```

One schema string, `project-context/1`, shared with Project Context. One
version number, read from `VERSION`. `tools` is optional and is the third place
`init` looks for the initializer.

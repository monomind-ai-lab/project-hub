# `templates/`

The shapes this Hub writes and the owner copies.

| Template | Used by | Written to |
| --- | --- | --- |
| `project/MARK.md` | `project_hub.py init` | `projects/<id>/MARK.md` |
| `project/SUMMARY.md` | `project_hub.py init` | `projects/<id>/SUMMARY.md` |
| `project/blueprint/EPIC.md` | the owner, by hand | `projects/<id>/blueprint/EPIC.md` |
| `project/blueprint/ARCHITECTURE.md` | the owner, by hand | `projects/<id>/blueprint/ARCHITECTURE.md` |
| `global/PERSON.md` | the owner, by hand | `global/people/<name>.md` |
| `global/AGENT.md` | the owner, by hand | `global/agents/<name>.md` |
| `global/SKILL.md` | the owner, by hand | `global/skills/<name>.md` |
| `global/SHARED.md` | the owner, by hand | `global/shared/<name>.md` |

## Placeholders

`init` substitutes these and nothing else. A placeholder it cannot answer is
left as the literal `TBD` so the gap is visible rather than invented.

`{{project_id}}` `{{remote}}` `{{host}}` `{{default_branch}}` `{{visibility}}`
`{{languages}}` `{{entry_points}}` `{{tracker}}` `{{ci}}` `{{deployment}}`
`{{installed}}` `{{today}}` `{{file_count}}` `{{shape}}`

Editing a template changes what the next `init` writes. It never rewrites a
project folder that already exists: every write in this product is create-only,
so an existing `MARK.md` is reported as preserved, not replaced.

## Records versus metadata

`global/*.md` templates are records in the `project-context/1` model and carry
frontmatter with the six required keys — `id`, `kind`, `status`, `title`,
`created`, `asserted_by`. The `project/*` templates do not: a mark, a summary,
an epic and an architecture record are Hub-side documents that the model has no
`kind` for, and inventing one would put a value in `kind` that no doctor
recognises. They stay plain Markdown, the way registries do.

# Epic — notes-api

The high-level plan: what this project is for, and what must be true when it is
done. Authored here in the Hub, pushed down into the repository read-only. The
repository's own `PLAN.md` is the milestone in front of the builders, and every
one of its items names an item here with a `Serves:` line.

Budget: 600 words.

## Why this project exists

Notes written during incidents, reviews, and handoffs were being lost inside
three separate tools. The cost was paid twice: once when the note could not be
found, and again when the same investigation was repeated. `notes-api` is the
one place a note goes and the one place it is searched from.

## What must be true when it is done

- **E-001 — One store.** Every team note written after adoption lives in
  `notes-api`. No team keeps a second canonical store.
- **E-002 — Search that finds a note from a half-remembered phrase.**
  Full-text search over title and body, ranked, returning in under 300ms at the
  ninety-fifth percentile on the current corpus.
- **E-003 — A note outlives its author's account.** Deleting a person does not
  delete or hide their notes; attribution survives as a name, not a foreign key
  to a live account.
- **E-004 — Two clients, one contract.** The CLI and the internal tools use the
  same documented HTTP API. There is no privileged path.
- **E-005 — Restorable within an hour.** A backup exists, and a restore has
  been performed from it at least once, by someone following the written
  procedure rather than remembering it.

## What this project is not

Not a wiki, not a document editor, not a chat log. A note is short, owned, and
searchable; anything that wants sections and images belongs elsewhere.

## Known tensions

`E-002` and `E-003` pull against each other: the cheapest search index keys on
the author account that `E-003` says must be able to disappear. Whoever plans
that milestone should read both items together and raise a question rather than
quietly picking one.

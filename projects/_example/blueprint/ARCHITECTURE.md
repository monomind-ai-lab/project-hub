# Architecture — notes-api

The shape the code cannot express: the decisions that stay true across
milestones, and the reasons they were made. Authored here in the Hub, pushed
down into the repository read-only. Budget: 1,200 words.

This file is not a description of the code. A reader can get that from the
code. It is the set of constraints that would be expensive to rediscover.

## Shape

One process, one database, no queue.

```text
client (CLI, internal tools)
      │  HTTPS, JSON
      ▼
notes-api  ── src/notes_api/
      │  SQL
      ▼
Postgres   ── migrations/
```

The absence of a queue is deliberate and load-bearing. Every write is a single
transaction that either lands or fails in front of the caller. Adding a queue
would buy throughput this service has never needed and cost the property that
makes it easy to reason about: there is no state in flight.

## Constraints that hold

- **The database is the only durable state.** No local disk cache, no
  filesystem uploads, no in-memory store that matters after a restart. A
  deployment is a stateless process; if it were not, `E-005` would be a much
  larger promise than it is.
- **Search runs in Postgres.** Full-text search uses a generated `tsvector`
  column and a GIN index, not a second search service. The corpus is small
  enough that the second service would be pure operational cost. This is the
  decision most likely to be revisited, and the honest trigger for revisiting
  it is a p95 that stays over 300ms after the index is correct — not a feeling
  that Postgres is the wrong tool.
- **Authorship is a string, not a foreign key.** A note records the author's
  display name and a stable actor string at write time. Accounts are a
  different lifecycle from notes, and `E-003` says notes win. The cost is that
  a renamed person is renamed only in notes written after the rename.
- **The HTTP contract is the boundary.** The CLI has no access the internal
  tools lack. When a client needs something the API cannot do, the API grows;
  no client reaches into the database.
- **Migrations are forward-only.** There is no down migration. A mistake is
  fixed by a new migration, which is the only kind of fix that is true of
  production as well as of a developer's laptop.

## What is deliberately absent

- **No soft delete.** A deleted note is gone. Retention arguments were had and
  settled: a note people believe is deleted but is not is worse than a note
  that is actually gone.
- **No multi-tenancy.** One organisation, one database. Every design that
  assumed tenants added a column nobody filled.
- **No API versioning.** There is one version. Breaking changes are coordinated
  with two clients, both of which are in the same organisation. A version
  header would be ceremony around a conversation that already happens.

## Where the shape is likely to break

The search rewrite is the pressure point. If ranking needs anything Postgres
cannot express, the choice is between a second store — which breaks "the
database is the only durable state" — and accepting worse ranking. That is a
decision for the owner, not for whoever is holding the milestone, and it should
arrive here as a question rather than as a merged pull request.

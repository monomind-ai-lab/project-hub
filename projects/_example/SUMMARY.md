# notes-api — owner's summary

A small internal HTTP service that stores and searches team notes. One Python
package, one Postgres schema, one deployment. It exists because three teams
were each keeping notes in a different place and none of them was searchable.

Shape: `src/notes_api/` holds the service, `migrations/` the schema, `tests/`
the suite that gates the deploy. There is no frontend; clients are the CLI and
two internal tools.

State: in maintenance. The search rewrite is the only open work.

<!-- project-hub:state:start -->
Last pull: never · Last push: never
<!-- project-hub:state:end -->

The block above is maintained by `project_hub.py`. Nothing outside those two
markers is ever read or written by the tool, so the rest of this file is yours.

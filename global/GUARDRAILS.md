<!-- project-hub:unfilled -->
# Guardrails

Rules that hold in every project. Each one is written so an agent can check
its own work against it and know whether it passed.

Format: one line per rule, imperative, falsifiable.

- G-001 …
- G-002 …

A rule nobody can fail is not a guardrail. If a rule needs a paragraph of
explanation, the explanation belongs in `shared/` and the rule stays one line.

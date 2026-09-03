---
id: C-YYYY-MM-DD-xxxx
kind: capsule
status: accepted
title: Skill — <name>
created: YYYY-MM-DD
asserted_by: person:<owner>
---

# Skill — `<name>`

- Version: `1`
- Applies to:
- Learned from: `capsule:<id>`, `doc:<binding>:<path>@<commit>`

## When to use it

The trigger, in the words someone would actually use.

## The method

Numbered, short, checkable.

## What it is not for

The near-miss cases that would otherwise pull it in wrongly.

## Changing it

Bump the version, add a `learned_from` reference to the record that taught the
change, and keep the old text only if a project still depends on it — in which
case supersede rather than rewrite.

# What Obsidian adds

**One question: should I open the Hub in Obsidian?**

Only if you want to. The Hub is a Git repository full of Markdown. Every
command, every stamp, and every check works with Obsidian never installed. This
guide exists so the choice is informed, not so you make it.

## What it adds

- **Backlinks.** A guardrail shows you every project record that mentions it.
- **Graph and search across everything at once.** Useful when the Hub holds a
  dozen projects and you are looking for where a decision was actually made.
- **A writing surface.** Properties panel for frontmatter, outline, word count
  — and word count matters here, because the budgets are counted in words.
- **An agent in the same window.** With the Claudian plugin you can ask and
  write without switching applications.

## What it does not add

Nothing depends on it. Records use ordinary relative Markdown links so they
render on GitHub and in any editor; hand-written wikilinks are accepted too,
and the checks resolve both. Obsidian will not sync your Hub — Git does that.
It will not run the `/hub-*` commands — your terminal agent does.

## Setting it up

1. Obsidian → **Open folder as vault** → choose this folder.
2. **Settings → Community plugins → Browse.** Search for each ID listed in
   `.obsidian/community-plugins.json`, install it, and enable it.

The recommended list, in order:

| Plugin | ID | Why |
| --- | --- | --- |
| Claudian | `realclaudian` | An agent inside the vault. MIT, desktop only |
| Git | `obsidian-git` | Commit and pull the Hub without leaving Obsidian |

Trim that list if you disagree. It is a recommendation, not a requirement.

## Why no plugin code ships here

This scaffold ships `.obsidian/` **configuration** and nothing else. There is
no `.obsidian/plugins/` directory and there never will be.

Vendoring a plugin means three problems at once: the file is large (Claudian's
build alone is over 3 MB), it is stale the moment upstream releases again, and
its licence becomes part of this distribution. Obsidian already solves all
three — it installs plugins, updates them, and licenses them to you.

`community-plugins.json` is Obsidian's list of *enabled* plugin IDs. Listing an
ID you have not installed is harmless: Obsidian simply does not load it, and it
starts working the moment you install it from the browser. That is what lets
this scaffold recommend plugins without shipping any.

If a file in `.obsidian/` already exists when you activate, activation leaves it
alone. Your settings win over ours.

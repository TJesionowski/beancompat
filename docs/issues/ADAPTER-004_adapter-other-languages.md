---
id: ADAPTER-004
title: "Adapters: Dart / Zig / Clojure efforts"
status: done
priority: low
created: 2026-04-26
category: ADAPTER
tags: [tracking]
---

# Adapters: Dart / Zig / Clojure efforts

**Status:** done (all three projects accounted for)
**Tier:** TBD per project

## Problem

The mailing list thread and surrounding community discussion mention beancount work in Dart, Zig, and Clojure, but none are concrete enough to have a row in `docs/references/README.md` or a directory under `implementations/`. This issue exists so the interest is captured in one place rather than dropped. As any of these mature into something invokable, split it out into its own `adapter-<name>.md` and remove its bullet from this file.

This is *not* a commitment to wrap every implementation that ever gets mentioned — only the ones that reach "actually parses beancount source" status are worth an adapter. The bar is the same as for other adapters: a CLI or library surface beancompat can drive black-box, plus a maintainer who's responding to issues.

## Context

- **Adapter pattern:** Subprocess-based, JSON-out — same as `implementations/beancountparserlima/` (Rust binary), `implementations/beancountparser/` (Python lark-based via `-c`), or `implementations/beancountv2/` (separate venv). Pick whichever pattern matches the implementation language.
- **Adapter skill:** `/update-implementations`.

## Resolution

All three languages are now accounted for (confirmed 2026-04-27 via mailing list thread):

- **Zig:** TurboBean by Moritz Drexl (https://github.com/themoritz/turbobean). Already split out to ADAPTER-002.
- **Clojure:** limabean by Simon Guest (https://github.com/tesujimath/limabean). The project is 55% Rust / 42% Clojure; the Rust side handles parsing and booking, exposed as Clojure data structures. beancompat drives the Rust binary — already tracked in ADAPTER-001.
- **Dart:** Vishesh Handa's private parser ("80% finished beancount parser in Dart, just for fun"). No public URL; not maintained; does not meet the bar (CLI surface + responsive maintainer). No adapter warranted.

No new issues to split off. Closing.

## References

- Mailing list: https://groups.google.com/g/beancount/c/EOoD755XNP0
- beancompat: `docs/references/README.md`, `implementations/`
- Skill: `/update-implementations`

# Issues

Open work items, one file per item. Each file has YAML frontmatter for programmatic tracking (status, priority, category) and prose sections for context, acceptance criteria, and references.

## Format

Each issue file has this shape:

```markdown
---
id: CATEGORY-NNN
title: "Short title"
status: open | in-progress | blocked | done | wontfix
priority: low | medium | high | critical
created: YYYY-MM-DD
category: ADAPTER | FAVA | BUG | TASK
tags: [optional, list]
---

# Title

## Problem
## Context
## Acceptance criteria
## References
```

**YAML frontmatter is required.** The `/issues-drive` skill mutates `status` programmatically and will fail on plain-markdown issues.

Filename convention: `{ID}_{slug}.md` — e.g. `FAVA-001_options-dcontext-neutral.md`.

## Categories

- **ADAPTER** — wiring up external implementation adapters
- **FAVA** — Fava-compat coverage items (capabilities, fixtures, schema)
- **BUG** — defects in beancompat itself
- **TASK** — general infrastructure or process work

## Usage

```bash
python scripts/issues.py list
python scripts/issues.py list --status=open --sort=priority
python scripts/issues.py list --status=in-progress --sort=priority
python scripts/issues.py list --category=FAVA
python scripts/issues.py validate
```

## Companion skills

- `/issues-drive` — attended-loop worker: picks one open/in-progress issue per invocation, executes it, and commits.
- `/issues-update` — audit issues against current repo state; mark resolved, add new, refresh facts.
- `/issues-init` — initialize a fresh tracker (stops if `docs/issues/` already exists).

## Open — Fava-compat coverage

| ID | Issue | Capability | Priority |
|---|---|---|---|
| FAVA-001 | [`options.dcontext` neutral representation](FAVA-001_options-dcontext-neutral.md) | CAP_FAVA | medium |
| FAVA-002 | [`MISSING` sentinel tag](FAVA-002_missing-sentinel.md) | CAP_PRINT, CAP_FAVA | medium |
| FAVA-003 | [`CAP_HASH` + `hash_entries`](FAVA-003_cap-hash.md) | CAP_HASH (new) | medium |
| FAVA-004 | [Typed columns in `QueryResult`](FAVA-004_typed-query-columns.md) | CAP_BQL, CAP_FAVA | medium |
| FAVA-005 | [30-key `options` coverage fixture](FAVA-005_options-coverage-fixture.md) | CAP_FAVA | high |
| FAVA-006 | [`CAP_PLUGINS` registration method](FAVA-006_cap-plugins-registration.md) | CAP_PLUGINS | medium |
| FAVA-007 | [`CAP_SUMMARIZE` for date-range windowing](FAVA-007_cap-summarize.md) | CAP_SUMMARIZE (new) | medium |
| FAVA-008 | [`CAP_INGEST` (deferred)](FAVA-008_cap-ingest.md) | CAP_INGEST (new) | low |

## Open — Implementation adapters

| ID | Issue | Language | Priority |
|---|---|---|---|
| ADAPTER-001 | [Adapter: limabean](ADAPTER-001_adapter-limabean.md) | Rust | high |
| ADAPTER-002 | [Adapter: TurboBean](ADAPTER-002_adapter-turbobean.md) | TBD | medium |
| ADAPTER-003 | [Adapter: rustledger](ADAPTER-003_adapter-rustledger.md) | Rust | medium |
| ADAPTER-004 | [Adapters: Dart / Zig / Clojure](ADAPTER-004_adapter-other-languages.md) | various | low |

## Wontfix

| ID | Issue | Reason |
|---|---|---|
| FAVA-009 | [`loader._load(...)` private-API parity](FAVA-009_loader-private-api.md) | Fava-side wart; fix belongs upstream |

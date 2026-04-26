# Issues

Open work items, one file per item. Broken out from the README's Fava-compat coverage roadmap so each item has room for context, acceptance criteria, and references without bloating the README.

## Format

Each issue file is plain markdown — no frontmatter — with this shape:

```markdown
# <Title>

**Status:** open | resolved | wontfix
**Tier:** parse | check | round-trip | Fava-compat (CAP_FAVA) | other
**Capability:** CAP_HASH | CAP_SUMMARIZE | …  (omit if N/A)

## Problem
<one or two paragraphs: the gap and why it matters>

## Context
<Fava-side anchors, beancompat-side files that would change>

## Acceptance criteria
- [ ] <concrete check>
- [ ] <concrete check>

## References
- Fava: `<path>`
- beancompat: `<path>`
- Memory: `.claude/memory/<file>`
```

Status conventions:

- **open** — not started, partially done, or in progress.
- **resolved** — done; keep the file with a one-line note pointing to the resolving commit or PR.
- **wontfix** — captured for visibility but not actionable in this repo (e.g. the gap belongs upstream).

## Open

| Issue | Capability | Notes |
|---|---|---|
| [`options.dcontext` neutral representation](options-dcontext-neutral.md) | CAP_FAVA | Replace live `DisplayContext` with a stable neutral key |
| [`MISSING` sentinel tag](missing-sentinel.md) | CAP_PRINT, CAP_FAVA | Round-trip preserves `MISSING` identity |
| [`CAP_HASH` + `hash_entries`](cap-hash.md) | CAP_HASH (new) | Stable hashes for Fava's edit-flow API |
| [Typed columns in `QueryResult`](typed-query-columns.md) | CAP_BQL, CAP_FAVA | `column.datatype` tags in query output |
| [30-key `options` coverage fixture](options-coverage-fixture.md) | CAP_FAVA | Enumerate the BeancountOptions keys Fava reads |
| [`CAP_PLUGINS` registration method](cap-plugins-registration.md) | CAP_PLUGINS | Adapter-level plugin registration |
| [`CAP_SUMMARIZE` for date-range windowing](cap-summarize.md) | CAP_SUMMARIZE (new) | Opening/closing entry semantics |
| [`CAP_INGEST` (deferred)](cap-ingest.md) | CAP_INGEST (new) | beangulp `Importer` ABC compat |

## Wontfix

| Issue | Reason |
|---|---|
| [`loader._load(...)` private-API parity](loader-private-api.md) | Fava-side wart; fix belongs upstream |

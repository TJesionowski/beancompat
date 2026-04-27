---
id: FAVA-005
title: "30-key options coverage fixture"
status: done
priority: high
created: 2026-04-26
category: FAVA
tags: [options, fixture]
---

# 30-key `options` coverage fixture

**Status:** open
**Tier:** Fava-compat (CAP_FAVA)

## Problem

Fava reads roughly 30 keys off the beancount options map (the `BeancountOptions` TypedDict in `fava/beans/types.py`). beancompat has no fixture that asserts these keys are present in any adapter's output. As a result, an alternative implementation could ship a Fava-compat tier that passes every other test while silently omitting an option key Fava needs at runtime.

The fix is to seed a fixture that explicitly enumerates the BeancountOptions keys and asserts the reference implementation populates them — making the omission visible and giving alternative implementations a single check to run against.

## Context

- **Fava-side:** `src/fava/beans/types.py` defines `BeancountOptions` as the canonical enumeration. Pull the key list directly from there.
- **beancompat-side:** New fixture under `fixtures/parse/` (or a new `fixtures/options/` subdirectory). Adapters emit the options map via `_parse_helper.py`. Related to `FAVA-001_options-dcontext-neutral.md` (which converts one of those keys to a neutral shape).

## Acceptance criteria

- [ ] Fixture file enumerates the BeancountOptions keys with expected types.
- [ ] Fixture passes against the reference (beancount v3) adapter.
- [ ] Fixture has a `known_divergences` entry for any adapter that intentionally omits a key (e.g. parser-only adapters that don't run the loader).
- [ ] Key list is sourced directly from a recent Fava checkout — not hand-typed — and the fixture comments name the Fava version it was derived from.

## Resolution

`fixtures/parse/options_coverage.json` added with 31 assertable BeancountOptions keys. `_parse_helper.py` serializer extended to handle `set/frozenset`, `Decimal`, `Enum`, and `dict[str, Decimal]`. `test_round_trip.py` updated to strip `options` from round-trip assertion (printer does not emit option directives). beancount v3 passes; beancount-v2, beancount-parser, beancount-parser-lima are xfailed with documented reasons.

## References

- Fava: `src/fava/beans/types.py` (BeancountOptions TypedDict)
- beancompat: `fixtures/parse/`, `fixtures/README.md`, `implementations/beancount/_parse_helper.py`
- Memory: `.claude/memory/fava_contract_surface.md`
- Related: `FAVA-001_options-dcontext-neutral.md`

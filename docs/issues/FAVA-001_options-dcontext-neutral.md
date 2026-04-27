---
id: FAVA-001
title: "options.dcontext neutral representation"
status: done
priority: medium
created: 2026-04-26
category: FAVA
tags: [options, display-context]
---

# `options.dcontext` neutral representation

**Status:** open
**Tier:** Fava-compat (CAP_FAVA)

## Problem

The reference adapter currently passes the live `DisplayContext` Python object through the options map. Fava reads `.build()` and per-currency precision off this object. A non-Python implementation has nothing to put there, and the JSON-oriented portable schema cannot serialize a live object — so any cross-implementation comparison or fixture that touches options precision today is reference-only.

The fix is to define a stable, neutral key (e.g. `display_precision_by_currency`) that any implementation can populate from its own internal precision tracking, and have the reference adapter compute that key from `DisplayContext.build()` on the way out.

## Context

- **Fava-side:** `src/fava/beans/types.py` enumerates the `BeancountOptions` keys Fava actually reads. The dcontext-derived precision is one of them.
- **beancompat-side:** `implementations/beancount/_parse_helper.py` (and the v2 helper) emit the options map; both currently either skip or dump the dcontext object. The portable schema in `fixtures/README.md` does not document any options-shape conventions.
- The new key needs a fixture under `fixtures/parse/` (or a new `fixtures/options/` group — see also `FAVA-005_options-coverage-fixture.md`).

## Acceptance criteria

- [ ] Portable schema documents a neutral `display_precision_by_currency` (or equivalent) key shape in `fixtures/README.md`.
- [ ] Reference adapter (`implementations/beancount/_parse_helper.py`) emits the key derived from `DisplayContext.build()`.
- [ ] v2 adapter (`implementations/beancountv2/_parse_helper.py`) emits the same shape from v2's equivalent.
- [ ] At least one fixture under `fixtures/` exercises the key with a multi-currency input.
- [ ] No live `DisplayContext` object survives the JSON round-trip in any adapter.

## Resolution

`serialize_display_context()` added to both v3 and v2 `_parse_helper.py`, deriving `display_precision_by_currency` (dict[str, int]) from `dcontext.build().fmtstrings`. `fixtures/parse/display_precision_by_currency.json` exercises USD (2dp) and JPY (0dp). `fixtures/README.md` documents the key shape. beancount v3 and v2 pass; beancount-parser and beancount-parser-lima are xfailed (no loader).

## References

- Fava: `src/fava/beans/types.py` (BeancountOptions TypedDict)
- beancompat: `implementations/beancount/_parse_helper.py`, `implementations/beancountv2/_parse_helper.py`, `fixtures/README.md`
- Memory: `.claude/memory/fava_contract_surface.md`

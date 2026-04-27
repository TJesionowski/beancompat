---
id: FAVA-002
title: "MISSING sentinel tag in the portable schema"
status: done
priority: medium
created: 2026-04-26
category: FAVA
tags: [schema, round-trip]
---

# `MISSING` sentinel tag in the portable schema

**Status:** open
**Tier:** Fava-compat (CAP_FAVA), affects round-trip (CAP_PRINT)

## Problem

beancount v3 uses a singleton `MISSING` sentinel to mark fields that were elided in source (e.g. an interpolated posting amount). The current portable JSON schema has no way to express "this field was specifically MISSING, not absent and not None" — so a round-trip through the fixture format loses the distinction. Fava-compat consumers downstream cannot reconstruct the original parse.

The fix is to introduce a marker object — `{"__missing__": true}` — that adapters emit wherever the source had `MISSING`, and that downstream consumers can treat as a typed sentinel.

## Context

- **beancount-side:** `MISSING` is defined in `beancount.core.amount` (and re-exported); it shows up on `Posting.units.number`, `.units.currency`, `.cost`, `.price` and on `CostSpec` fields after parse but before booking.
- **beancompat-side:** `implementations/beancount/_parse_helper.py` serializes posting fields; needs to detect `MISSING` and emit the marker. `fixtures/README.md` schema section needs to document the marker. Affects `test_round_trip.py` since the print round-trip currently sidesteps this.
- The `kind` discriminator already added for `CostSpec` vs `Cost` is the precedent for how the schema handles typed-but-shapeless data.

## Acceptance criteria

- [ ] `fixtures/README.md` documents the `{"__missing__": true}` marker and where it can appear (any field that accepts a parsed-but-not-yet-booked value).
- [ ] Reference adapter emits the marker for elided posting fields.
- [ ] At least one fixture under `fixtures/parse/` exercises the marker on an elided posting.
- [ ] `test_round_trip.py` verifies that a fixture with `MISSING` round-trips losslessly through the print capability.

## Resolution

`{"__missing__": True}` sentinel added. `beancountparser/_parse_helper.py` emits it for `simple_posting` (elided amount). `beancount/_parse_helper.py` and `beancountv2/_parse_helper.py` detect MISSING in `serialize_amount` and `serialize_cost` (defensive — loader resolves MISSING before serialization). `fixtures/README.md` documents the sentinel with parse-vs-check-tier semantics. `fixtures/parse/missing_sentinel.json` exercises an elided posting with a sparse expected so both parse-tier (MISSING) and check-tier (resolved) adapters satisfy containment.

## References

- Fava: `src/fava/beans/protocols.py` (Amount/Cost/Position protocols admit alternative implementations but assume MISSING is preserved)
- beancompat: `implementations/beancount/_parse_helper.py`, `fixtures/README.md`, `tests/test_round_trip.py`
- Memory: `.claude/memory/fava_contract_surface.md`

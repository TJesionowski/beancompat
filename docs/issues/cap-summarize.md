# `CAP_SUMMARIZE` for date-range windowing

**Status:** open
**Tier:** Fava-compat (CAP_FAVA)
**Capability:** CAP_SUMMARIZE (new)

## Problem

Fava uses `beancount.ops.summarize.clamp_opt` (and related summarize ops) to render date-windowed views — opening balance entries at the window start, closing entries at the window end, transactions in between. A Fava-compatible implementation must produce the same opening/closing entry semantics for the same window. beancompat does not test this today.

The fix is to add `CAP_SUMMARIZE`, an adapter method that clamps a loaded ledger to a date range, and fixtures that pin down opening-balance entry shape, closing-balance shape, and which entries get included vs excluded at the boundaries.

## Context

- **Fava-side:** Date-filtered ledger views in Fava call `ops.summarize.clamp_opt`. Opening entries summarize all activity strictly before the window start; closing entries optionally summarize activity after window end. Boundary semantics (does an entry on `start_date` get included? closed?) matter for chart correctness.
- **beancompat-side:** New `CAP_SUMMARIZE = "summarize"` constant. New protocol method like `clamp(source, start_date, end_date) -> ParseResult`. New fixture group under `fixtures/check/` since this requires booking. Reference adapter implementation in `implementations/beancount/__init__.py` (subprocess to a helper that calls `summarize.clamp_opt`).

## Acceptance criteria

- [ ] `CAP_SUMMARIZE` constant added.
- [ ] Adapter method that takes a source + window and returns the clamped directives.
- [ ] Reference implementation in the v3 adapter.
- [ ] Fixtures covering: window with an entry exactly on the start boundary, window with an entry exactly on the end boundary, window with no entries, window with multiple currencies.
- [ ] Fixtures pin the shape of generated opening and closing entries (account, narration, amount).

## References

- beancount: `beancount.ops.summarize.clamp_opt`
- beancompat: `implementations/adapter.py`, `implementations/beancount/__init__.py`, `fixtures/check/`
- Memory: `.claude/memory/fava_contract_surface.md`

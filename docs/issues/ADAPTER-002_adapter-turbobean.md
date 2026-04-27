---
id: ADAPTER-002
title: "Adapter: TurboBean"
status: in-progress
priority: medium
created: 2026-04-26
category: ADAPTER
tags: [vNext, divergence]
---

# Adapter: TurboBean

**Status:** in-progress
**Tier:** parse, possibly check (depends on what upstream exposes)
**Implementation:** [themoritz/turbobean](https://github.com/themoritz/turbobean) (Zig)

## Problem

`implementations/turbobean/` is a stub directory (only `.gitkeep`). TurboBean is interesting precisely *because* it diverges — Moritz is implementing parts of Martin's vNext document, including a different inventory model. That makes TurboBean the highest-value single target for divergence-discovery: the entire reason beancompat exists is to make divergences like this visible without forcing a "right answer" verdict.

Until the adapter is wired up, the fixtures and generative tests cannot exercise TurboBean's vNext semantics, and no `known_divergences` entries can be authored against it.

## Context

- **Upstream:** https://github.com/themoritz/turbobean — written in Zig (requires Zig 0.15.2 to build). Builds with `zig build --release=safe -Dembed-static --prefix ~/.local`.
- **CLI surface (as of 2026-04-27):** `turbobean serve <file>`, `turbobean fmt`, `turbobean lsp`. **No structured-output command exists.** Protobuf output is planned (listed as `[ ] Protobuf Output` in the README) but not yet implemented. The adapter cannot be wired up until TurboBean ships a machine-readable dump command.
- **Divergence axis:** Inventory model per vNext. Once the adapter exists, the inventory-touching fixtures (cost basis, FIFO sells, partial sells with gains — see `tests/test_booking_discrepancies.py`, `tests/test_cost_inventory.py`) become the obvious first place to record `known_divergences`.
- **vNext doc:** https://beancount.github.io/docs/beancount_v3.html — the source of truth for what TurboBean is implementing. Worth reading before authoring divergence entries so the divergences are described in vNext's own terms, not as "TurboBean is wrong."
- **Adapter skill:** `/update-implementations`.
- **Blocker:** Upstream must implement a structured-output command (protobuf or JSON) before an adapter can be written. Watch https://github.com/themoritz/turbobean for progress on the Protobuf Output feature.

## Acceptance criteria

- [x] Upstream URL and language confirmed; `docs/references/README.md` row updated.
- [ ] `implementations/turbobean/__init__.py` implementing the `Implementation` protocol.
- [ ] Adapter advertises whatever capabilities upstream actually supports (likely CAP_PARSE; CAP_BOOKING if a booking pipeline is shipped).
- [ ] `is_available()` correctly reports false when TurboBean is not installed.
- [ ] At least one fixture exercises a vNext-divergent code path with a `known_divergences` entry explaining the difference in vNext terms.
- [ ] Build/install instructions added so contributors can run the adapter.

**Progress (2026-04-27):** Criterion 1 done — URL and language (Zig) confirmed from mailing list + GitHub. Remaining criteria blocked on upstream shipping a structured-output command; watching the repo for protobuf output progress.

## References

- Implementation: https://github.com/themoritz/turbobean
- vNext spec: https://beancount.github.io/docs/beancount_v3.html
- Mailing list: https://groups.google.com/g/beancount/c/EOoD755XNP0
- beancompat: `implementations/turbobean/` (stub), `tests/test_cost_inventory.py`, `tests/test_booking_discrepancies.py`
- Skill: `/update-implementations`

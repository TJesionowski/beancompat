---
id: ADAPTER-002
title: "Adapter: TurboBean"
status: open
priority: medium
created: 2026-04-26
category: ADAPTER
tags: [vNext, divergence]
---

# Adapter: TurboBean

**Status:** open
**Tier:** parse, possibly check (depends on what upstream exposes)
**Implementation:** TurboBean (Moritz Drexl)

## Problem

`implementations/turbobean/` is a stub directory (only `.gitkeep`). TurboBean is interesting precisely *because* it diverges — Moritz is implementing parts of Martin's vNext document, including a different inventory model. That makes TurboBean the highest-value single target for divergence-discovery: the entire reason beancompat exists is to make divergences like this visible without forcing a "right answer" verdict.

Until the adapter is wired up, the fixtures and generative tests cannot exercise TurboBean's vNext semantics, and no `known_divergences` entries can be authored against it.

## Context

- **Upstream:** TurboBean's repository, language, and CLI surface are not recorded in `docs/references/README.md` (the row reads `Language: ?`). Step 1 of this issue is to track the project down — Moritz has posted on the beancount mailing list — and decide which surface to wrap.
- **Divergence axis:** Inventory model per vNext. Once the adapter exists, the inventory-touching fixtures (cost basis, FIFO sells, partial sells with gains — see `tests/test_booking_discrepancies.py`, `tests/test_cost_inventory.py`) become the obvious first place to record `known_divergences`.
- **vNext doc:** https://beancount.github.io/docs/beancount_v3.html — the source of truth for what TurboBean is implementing. Worth reading before authoring divergence entries so the divergences are described in vNext's own terms, not as "TurboBean is wrong."
- **Adapter skill:** `/update-implementations`.

## Acceptance criteria

- [ ] Upstream URL and language confirmed; `docs/references/README.md` row updated.
- [ ] `implementations/turbobean/__init__.py` implementing the `Implementation` protocol.
- [ ] Adapter advertises whatever capabilities upstream actually supports (likely CAP_PARSE; CAP_BOOKING if a booking pipeline is shipped).
- [ ] `is_available()` correctly reports false when TurboBean is not installed.
- [ ] At least one fixture exercises a vNext-divergent code path with a `known_divergences` entry explaining the difference in vNext terms.
- [ ] Build/install instructions added so contributors can run the adapter.

## References

- Implementation: TurboBean (URL TBD — see mailing list thread for current location)
- vNext spec: https://beancount.github.io/docs/beancount_v3.html
- Mailing list: https://groups.google.com/g/beancount/c/EOoD755XNP0
- beancompat: `implementations/turbobean/` (stub), `tests/test_cost_inventory.py`, `tests/test_booking_discrepancies.py`
- Skill: `/update-implementations`

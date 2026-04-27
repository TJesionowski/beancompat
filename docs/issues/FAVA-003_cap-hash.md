---
id: FAVA-003
title: "CAP_HASH capability and hash_entries adapter method"
status: open
priority: medium
created: 2026-04-26
category: FAVA
tags: [capability, fava-edit-flow]
---

# `CAP_HASH` capability and `hash_entries` adapter method

**Status:** open
**Tier:** Fava-compat (CAP_FAVA)
**Capability:** CAP_HASH (new)

## Problem

Fava's edit-flow JSON API uses `beancount.core.compare.hash_entry` to identify entries by stable hash so the frontend can refer to a specific directive across reload cycles. A Fava-compatible implementation must expose hash values that are stable within itself and ideally agree across implementations for the same input. beancompat does not test this today.

The fix is to add a new capability `CAP_HASH` and a corresponding adapter method (`hash_entries(entries) -> list[str]` or similar), then add a fixture that asserts cross-implementation hash agreement on a small canonical input.

## Context

- **Fava-side:** `compare.hash_entry` (in `beancount.core.compare`) is called via Fava's edit-flow code. Fava treats the hash as opaque but expects it to be a function of the directive's normative content (date, type, narration, postings, etc.) and stable across reloads of the same source.
- **beancompat-side:** `implementations/adapter.py` defines the capability constants and the `Implementation` protocol. Add `CAP_HASH = "hash"`, add `hash_entries` to the protocol, implement it in `implementations/beancount/__init__.py` (subprocess-based, calling `compare.hash_entry`).
- Cross-impl agreement is aspirational — the immediate test is that hashes are stable within an implementation and that the reference impl produces consistent hashes for fixture inputs. Cross-impl agreement becomes meaningful once a second implementation supports CAP_HASH.

## Acceptance criteria

- [ ] `CAP_HASH` constant added to `implementations/adapter.py`.
- [ ] `hash_entries` method added to the `Implementation` protocol.
- [ ] Reference (beancount v3) adapter implements `hash_entries` via the public `compare.hash_entry` API.
- [ ] At least one fixture asserts the hash for a small canonical input (regression test for the reference impl).
- [ ] Test skips cleanly on adapters that do not declare `CAP_HASH`.

## References

- Fava: edit-flow JSON API; `compare.hash_entry` consumer
- beancount: `beancount.core.compare.hash_entry`
- beancompat: `implementations/adapter.py`, `implementations/beancount/__init__.py`, `implementations/beancount/_parse_helper.py`
- Memory: `.claude/memory/fava_contract_surface.md`

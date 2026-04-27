---
id: FAVA-008
title: "CAP_INGEST — beangulp Importer ABC compatibility"
status: open
priority: low
created: 2026-04-26
category: FAVA
tags: [capability, beangulp, deferred]
---

# `CAP_INGEST` — beangulp `Importer` ABC compatibility

**Status:** open (deferred)
**Tier:** orthogonal to core beancount; required for full Fava-compat
**Capability:** CAP_INGEST (new)

## Problem

beangulp ships an `Importer` ABC that downstream importers subclass to bring CSV/OFX/PDF data into beancount. Fava's import UI invokes importers through this ABC. A non-Python implementation that wants to be a drop-in replacement for the full Fava experience needs a Python-level shim that exposes the `Importer` interface and produces directives in beancount-namedtuple shape.

This is orthogonal to the core beancount API — beangulp is a separate package — and would be a meaningfully larger test surface than the rest of beancompat. Worth capturing as a known gap, deferring until the core tiers are denser.

## Context

- **beangulp-side:** `beangulp.Importer` ABC defines `identify`, `extract`, `file_account`, `file_date`, `file_name`. Importers return lists of beancount directives.
- **Fava-side:** Fava's import view is one of the six `core/` files outside `fava/beans/` (per the contract-surface memory) — `core/ingest.py`. The Fava-side surface is small but assumes the beangulp ABC.
- **beancompat-side:** New `CAP_INGEST = "ingest"`. Likely a separate test suite (its own `tests/test_ingest.py`) and its own fixture group (sample input files + expected directive output). Almost certainly never tested against parser-only adapters.

## Acceptance criteria

- [ ] `CAP_INGEST` constant defined.
- [ ] Adapter method that runs an importer against a sample input and returns directives.
- [ ] At least one minimal fixture: a CSV input + expected directive output through a trivial importer.
- [ ] Reference adapter implementation that calls beangulp.
- [ ] Documentation in `tests/README.md` (or a new `tests/ingest/README.md`) explaining the suite is opt-in via `CAP_INGEST`.

## References

- beangulp: `beangulp.Importer` ABC
- Fava: `fava/core/ingest.py`
- beancompat: `implementations/adapter.py`, new `tests/test_ingest.py`, new `fixtures/ingest/`
- Memory: `.claude/memory/fava_contract_surface.md`

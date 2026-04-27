---
id: ADAPTER-003
title: "Adapter: rustledger"
status: done
priority: medium
created: 2026-04-26
category: ADAPTER
tags: [rust]
---

# Adapter: rustledger

**Status:** open
**Tier:** parse at minimum; check if upstream exposes booking
**Implementation:** [rustledger/rustledger](https://github.com/rustledger/rustledger) (Rust, AI-assisted)

## Problem

No directory exists for rustledger under `implementations/`. rustledger is interesting in two ways: it's a second Rust implementation (good for cross-Rust agreement signal alongside limabean), and it ships its own AI-assisted spec documents under `spec/` — meaning its authors have already written down what they think correct behavior looks like. That makes rustledger the best test of whether two independent specs (rustledger's, and the de-facto spec encoded in beancount's behavior) agree.

## Context

- **Upstream:** https://github.com/rustledger/rustledger plus the cross-PTA format spec at https://github.com/rustledger/pta-standards/tree/main/formats/beancount.
- **Adapter shape:** Likely the same Rust-binary-helper-via-subprocess pattern used by `implementations/beancountparserlima/`. Reuse the `_binary_path()` / Cargo build flow.
- **Divergence opportunity:** rustledger has its own format spec, so the first round of fixture failures against rustledger doubles as a free audit of where rustledger's spec disagrees with beancount-as-written. That's exactly the kind of divergence mapping beancompat exists to surface.
- **Adapter skill:** `/update-implementations`.

## Acceptance criteria

- [x] `implementations/rustledger/` created with adapter `__init__.py` implementing the `Implementation` protocol.
- [x] Helper binary (Cargo crate or wrapping a rustledger CLI) emits the portable JSON shape.
- [x] Adapter advertises whatever capabilities upstream supports (start with CAP_PARSE).
- [x] `is_available()` correctly reports false when the binary isn't built.
- [x] At least one cross-impl fixture either passes or has a `known_divergences` entry referencing the relevant section of rustledger's spec.
- [x] `docs/references/README.md` updated if rustledger's surface or status changes.

## Resolution

CAP_PARSE adapter landed. `rustledger-loader` v0.14.0 exposes `Loader::new().load(path)` without features; the helper binary maps all 12 directive types to the portable JSON schema. All parse-tier fixtures pass or have documented known_divergences: `display_precision_by_currency` (DisplayContext.precisions is private) and `options_coverage` (beancount v3-only keys absent, `tolerance_multiplier` aliased to `inferred_tolerance_multiplier`). Build requires `--ignore-rust-version` since system Rust is 1.93.0 and rustledger declares `rust-version = "1.94"`. Suite: 306 passed, 119 skipped, 11 xfailed (+24 vs baseline).

## References

- Upstream: https://github.com/rustledger/rustledger
- Spec docs: https://github.com/rustledger/rustledger/tree/main/spec
- Format spec: https://github.com/rustledger/pta-standards/tree/main/formats/beancount
- Existing analogue: `implementations/beancountparserlima/`
- beancompat: `implementations/adapter.py` (protocol)
- Skill: `/update-implementations`

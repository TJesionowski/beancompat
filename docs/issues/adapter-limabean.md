# Adapter: limabean

**Status:** open
**Tier:** parse + check (CAP_PARSE, CAP_BOOKING) — booking is the point
**Implementation:** [tesujimath/limabean](https://github.com/tesujimath/limabean) (Rust, Simon Guest)

## Problem

`implementations/limabean/` is a stub directory (only `.gitkeep`). limabean is the most concrete non-Python booking implementation in flight today — a Rust booking layer built on `beancount-parser-lima` — and beancompat currently has no booking-capable Rust adapter. Until limabean is wired up, every booking-tier test in the suite is reference-only and the cross-implementation comparison the project exists to do can't actually run for booking semantics.

The existing `implementations/beancountparserlima/` adapter is the closest analogue: Cargo-built Rust binary helper, JSON-out, subprocess invocation. limabean's adapter should follow the same shape but advertise CAP_BOOKING in addition to CAP_PARSE.

## Context

- **Upstream:** Simon Guest already adapted Martin's booking tests to Rust under `rust/limabean-booking/src/tests/booking.rs` (linked from `docs/references/README.md`). That suite is the closest thing to a "limabean is correct" check; passing the same fixtures via beancompat's `check/` tier is the goal.
- **Existing pattern:** `implementations/beancountparserlima/__init__.py` shows the full subprocess-to-Rust-binary flow: `_binary_path()` helper preferring `target/release` over `target/debug`, `is_available()` that runs the binary against `/dev/null`, JSON-out parse helper. Reuse this shape.
- **Adapter skill:** `/update-implementations` is the project's skill for guided adapter creation. Use it.
- **Capabilities to advertise:** at minimum CAP_PARSE + CAP_BOOKING. CAP_PRINT and CAP_BQL only if upstream actually exposes them — don't claim capabilities that aren't there.
- **Known unknowns:** whether limabean exposes a CLI suitable for batch invocation, or whether the adapter needs a small `limabean-helper` Cargo crate that wraps the library and emits the portable JSON shape (likely the latter — same as the lima-parse-helper crate).

## Acceptance criteria

- [ ] `implementations/limabean/__init__.py` implementing the `Implementation` protocol.
- [ ] Cargo crate (under `implementations/limabean/`) that wraps the library and emits the portable JSON shape used by other adapters.
- [ ] Adapter advertises CAP_PARSE and CAP_BOOKING.
- [ ] `is_available()` correctly reports false when the helper binary isn't built.
- [ ] At least one `check/` fixture passes against limabean.
- [ ] Any divergence from the reference impl is recorded as a `known_divergences` entry on the relevant fixture (precedent: `fixtures/parse/open_multi_currency.json`).
- [ ] Build instructions added to `implementations/limabean/` (or a top-level `BUILDING.md`) so contributors know to run `cargo build --release`.

## References

- Upstream: https://github.com/tesujimath/limabean
- Booking tests: https://github.com/tesujimath/limabean/blob/main/rust/limabean-booking/src/tests/booking.rs
- Parser sibling: https://github.com/tesujimath/beancount-parser-lima
- Existing analogue: `implementations/beancountparserlima/`
- beancompat: `implementations/limabean/` (stub), `implementations/adapter.py` (protocol)
- Skill: `/update-implementations`

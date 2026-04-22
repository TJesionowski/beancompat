# beancompat

A repertoire of black-box property tests for beancount implementations.

## What this is

A **descriptive** (not normative) compatibility test suite for beancount implementations. It exercises the full external interface that downstream tooling (Fava, plugins, extensions) relies on, and documents where implementations diverge.

Implementors are adults who can disagree with Martin Blais. Users are (mostly) adults who can decide which implementation to use. This project aims to limit the inevitable fragmentation by making the invisible explicit.

## Why this exists

The beancount community tried and failed to establish a normative spec process. See the [mailing list thread](https://groups.google.com/g/beancount/c/EOoD755XNP0).

Multiple new implementations are appearing — limabean (Rust), TurboBean (diverging on inventory per vNext), rustledger (AI-assisted Rust rewrite), plus work in Dart, Zig, Clojure. Martin Blais's advice: "if you really want something done, drive it yourself without trying too hard to get consensus." His key observation: "The main challenge to new implementors is going to be completeness. With the AIs zero-to-0.8 is almost instant; your enemy will be 0.8 to 1.0. Lots of little details to care for."

beancompat is the bottom-up answer. No RFC, no BDFL, no consensus required. Just tests that show you the facts.

## Goals

- **Validation suite for implementors:** A portable set of black-box tests any beancount implementation can run against itself.
- **Feature coverage assurance:** Detect when an implementation silently drops or diverges on features that real ledgers depend on.
- **The 0.8→1.0 tool:** Target the "lots of little details" that are the real challenge for new implementations.
- **Divergence discovery:** Use generative property-based testing to *find* behavioral differences, not just confirm known ones.

## Non-goals

- **Normativity.** We document behavior; we don't prescribe it. No test is "the right answer."
- **Benchmarking.** Correctness only; performance comparison is a separate concern.
- **Replacing the RFC process.** We don't build consensus on what beancount *should* do. We make visible what implementations *actually* do.

## Scope

Beancount-like systems specifically. If an implementation reads .beancount files and claims beancount compatibility, it's in scope. The broader PTA ecosystem (hledger, ledger) is not.

## How it works

Tests are organized in two layers:

1. **Hand-written property tests** — specific .beancount snippets with specific expected outputs. These document known, important behaviors.
2. **Generative property tests** (Hypothesis `@given`) — for any valid generated input, implementations should agree or diverge in a documented way. Hypothesis shrinking minimizes failing cases to the simplest possible example.

Implementations are invoked as external processes (true black-box). Adapter configurations live in `implementations/`.

## Running tests

```bash
# Run against the reference beancount implementation
pytest tests/

# Run against a specific implementation
pytest tests/ --implementation=limabean
```

## Portable fixtures

For implementations in languages other than Python, `fixtures/` holds a set of
JSON files — each pairs a `.beancount` snippet with the expected parse output
in a neutral shape. Any implementation can consume these directly without a
Python test harness. See [`fixtures/README.md`](fixtures/README.md) for the
schema, tiering (`parse/` vs `check/`), and a non-Python consumption recipe.

## Compatibility tiers

beancompat has three compatibility tiers, with increasing strictness:

| Tier | Capability | Test file | What it checks |
|------|-----------|-----------|----------------|
| **Parse** | `CAP_PARSE` | `test_fixtures.py` (parse/ fixtures) | Source parses to directives with the right shape |
| **Check** | `CAP_BOOKING` | `test_fixtures.py` (check/ fixtures) | Full loader semantics — booking, interpolation, balance assertions |
| **Round-trip** | `CAP_PRINT` | `test_round_trip.py` | Implementation can re-serialize its own output back to parseable source |
| **Fava** | `CAP_FAVA` | `test_fava_compat.py` | In-process Python objects satisfy `fava.beans.abc` protocols — a Fava-compatible implementation can drive Fava's edit, chart, and query UIs |

A non-Python implementation that wants to be Fava-compatible needs a Python
frontend layer that wraps its native output into beancount-namedtuple-shaped
objects. See the CAP_FAVA docstring in `implementations/adapter.py`.

### Fava-compat coverage roadmap

Derived from a survey of Fava's beancount API surface (see the
[`fava_contract_surface` memory](.claude/memory/fava_contract_surface.md) and
the Fava-isolation layer at `src/fava/beans/`). Items below are the known
gaps between what beancompat verifies today and what a full Fava-compatible
implementation must expose. Ordered roughly by Fava-blast-radius.

- [ ] **`options.dcontext` neutral representation.** Options map currently passes a live `DisplayContext` object; Fava reads `.build()` and per-currency precision. Emit stable neutral keys (e.g. `display_precision_by_currency`) and add an options-coverage fixture.
- [ ] **`MISSING` sentinel tag.** Round-trip loses the v3 `MISSING` identity; add a `{"__missing__": true}` marker in the schema.
- [ ] **`CAP_HASH` + `hash_entries`.** Fava uses `compare.hash_entry` to drive its edit-flow JSON API. Add adapter method + fixture asserting stable, cross-impl-agreed hashes.
- [ ] **Typed columns in `QueryResult`.** Fava reads `column.datatype` (Amount/Inventory/Position/Decimal/date). Enrich `QueryResult.columns` with type tags; add a typed-column fixture.
- [ ] **30-key `options` coverage fixture.** Seed a fixture listing the option keys Fava reads off `BeancountOptions` (see `fava/beans/types.py`).
- [ ] **`CAP_PLUGINS` registration method.** The capability exists but no adapter method drives plugin registration into the loader pipeline.
- [ ] **`CAP_SUMMARIZE`** for date-range windowing (`ops.summarize.clamp_opt`). Opening/closing entry semantics.
- [ ] **`CAP_INGEST`** — beangulp `Importer` ABC compat. Separate suite; orthogonal to core beancount but required for full Fava coverage.
- [ ] **`loader._load(...)` private-API parity.** Fava calls a private loader fn to bypass caching. Document as a Fava-side wart; not beancompat's problem to fix.

### Shipped
- Parse/check-tier JSON fixtures (`test_fixtures.py`)
- `CAP_PRINT` round-trip (`test_round_trip.py`)
- `CAP_FAVA` Python-level ABC conformance (`test_fava_compat.py`)
- `CostSpec` vs `Cost` `kind` discriminator in the portable schema

## Project structure

```
beancompat/
├── docs/references/      # Primary sources and reference index
├── fixtures/             # Portable JSON fixtures (language-independent)
├── implementations/      # Per-implementation adapter configuration
├── ledgers/              # Sample .beancount files used by tests
├── scripts/              # Fixture generator and CLI runner
├── strategies/           # Hypothesis strategies for beancount primitives
├── tests/                # Property tests
└── results/              # Generated: test results and diff reports
```

## License

MIT

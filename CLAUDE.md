# beancompat — Claude Code Instructions

## Project overview

Black-box property test suite for beancount implementations. Tests exercise the external interface that downstream tooling relies on and document where implementations diverge.

## Tech stack

- Python 3.12 (Nix flake devshell)
- pytest + Hypothesis for property-based testing
- beancount v3 as reference implementation

## Conventions

- Tests go in `tests/`. Name test files `test_<feature>.py`.
- Hypothesis strategies go in `strategies/`. One module per domain (accounts, amounts, transactions, etc.).
- Implementation adapters live in `implementations/`. Each implementation gets a subdirectory with adapter config.
- Sample ledger files go in `ledgers/`.
- Generated results go in `results/` (gitignored).

## Black-box execution model

Implementations are invoked as external processes — no importing of internals. The adapter interface (`implementations/adapter.py`) defines how to invoke an implementation and parse its output.

## Test layers

1. **Hand-written property tests**: specific inputs, specific expected outputs. Document known behaviors.
2. **Generative tests** (`@given`): generated inputs, assert agreement between implementations. Discover unknown divergences.

## Claude skills

1. **Update implementations** — install/configure a new implementation's adapter, re-run tests, document findings.
2. **Check a ledger** — run tests against a user-provided ledger, filter discrepancies, explain semantic differences.

## Running tests

```bash
pytest tests/
pytest tests/ -v          # verbose
pytest tests/ -x          # stop on first failure
```

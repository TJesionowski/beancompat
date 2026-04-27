# Tests

## Organization

- `test_<feature>.py` — Tests for a specific beancount feature area.
- Hand-written tests use plain pytest assertions on known inputs.
- Generative tests use `@given` with strategies from `strategies/`.

## Naming conventions

- `test_<feature>_<behavior>` — Hand-written test for a specific behavior.
- `test_<feature>_roundtrip` or `test_<feature>_no_errors` — Generative tests.

## Capability-gated suites

Some test files require a specific capability and skip automatically for adapters that don't advertise it:

- `test_ingest.py` — requires `CAP_INGEST`. Tests `run_importer(importer, filepath)` against a trivial beangulp `Importer` subclass and a CSV fixture in `fixtures/ingest/`. Non-Python adapters are always skipped; only adapters that call beangulp can implement this.

## Running

```bash
pytest tests/                    # all tests
pytest tests/test_parse.py       # single file
pytest tests/ -k "open"          # keyword filter
pytest tests/ --hypothesis-seed=0  # reproduce a specific run
```

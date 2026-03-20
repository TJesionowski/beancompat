# Tests

## Organization

- `test_<feature>.py` — Tests for a specific beancount feature area.
- Hand-written tests use plain pytest assertions on known inputs.
- Generative tests use `@given` with strategies from `strategies/`.

## Naming conventions

- `test_<feature>_<behavior>` — Hand-written test for a specific behavior.
- `test_<feature>_roundtrip` or `test_<feature>_no_errors` — Generative tests.

## Running

```bash
pytest tests/                    # all tests
pytest tests/test_parse.py       # single file
pytest tests/ -k "open"          # keyword filter
pytest tests/ --hypothesis-seed=0  # reproduce a specific run
```

---
description: Add a new beancount implementation adapter to the test suite
---

# Update Implementations

Add a new beancount implementation adapter to beancompat.

## Steps

1. **Research the implementation**
   - Determine: language, install method, CLI vs library, parse API
   - Determine capabilities: which of `parse`, `booking`, `plugins`, `bql`, `includes` it supports
   - Install it in the dev environment (`pip install` or nix)

2. **Create adapter directory**
   - `implementations/<name>/__init__.py` — adapter class
   - `implementations/<name>/_parse_helper.py` — subprocess helper that emits JSON

3. **Implement the adapter class**
   Follow the protocol in `implementations/adapter.py`:
   - `name` property → short identifier string
   - `capabilities` property → set of `CAP_*` constants from `implementations.adapter`
   - `is_available()` → subprocess check for the dependency
   - `parse_string(source)` → write to temp file, delegate to `check_file`
   - `check_file(path)` → invoke `_parse_helper.py` via subprocess, parse JSON into `ParseResult`
   - `execute_query(source, query)` → return error `QueryResult` if BQL unsupported

4. **Implement the parse helper**
   The helper script must emit JSON matching this schema:
   ```json
   {
     "directives": [{"type": "...", "date": "...", "meta": {}, "data": {}}],
     "errors": ["..."],
     "options": {}
   }
   ```
   Reference `implementations/beancount/_parse_helper.py` for the exact field shapes per directive type (postings, amounts, costs, etc).

5. **Register in test infrastructure**
   In `tests/conftest.py`:
   - Import the new adapter class
   - Add it to the `ADAPTERS` dict
   - Add a standalone session-scoped fixture if needed

6. **Run tests and document**
   ```bash
   # Existing tests unchanged
   pytest tests/ -v -k "not cross_impl"

   # Cross-implementation tests show agreement/divergence
   pytest tests/test_cross_impl.py -v

   # Full suite
   pytest tests/ -v
   ```
   Note any divergences — these are the interesting findings, not failures.

## Key patterns

- All implementation access is black-box (subprocess). Never import internals.
- The `_parse_helper.py` runs inside the implementation's Python environment.
- Capability-based test skipping (`@pytest.mark.requires_capability`) handles parser-only vs full implementations automatically.
- Existing single-implementation tests use the `beancount` fixture and are unaffected.
- Cross-implementation tests use the parametrized `implementation` fixture.


# Typed columns in `QueryResult`

**Status:** open
**Tier:** Fava-compat (CAP_FAVA), affects BQL (CAP_BQL)

## Problem

`QueryResult.columns` in `implementations/adapter.py` is currently `list[str]` — column names only. Fava reads `column.datatype` (one of `Amount`, `Inventory`, `Position`, `Decimal`, `date`) when rendering query results, because how a value is displayed depends on its type. Without type tags in the portable shape, beancompat cannot exercise Fava's query-rendering paths or detect when an alternative implementation returns a typed column with the wrong tag.

The fix is to enrich `QueryResult.columns` with type tags (e.g. `list[tuple[str, str]]` or `list[dict[name, datatype]]`) and add a fixture that asserts the tags for representative BQL queries.

## Context

- **Fava-side:** Fava's chart and query renderers branch on `column.datatype`. Source: query rendering in `fava/core/` (one of the six exception files outside `fava/beans/` per the contract-surface memory).
- **beancompat-side:** `implementations/adapter.py` defines `QueryResult`. Reference adapter emits columns from `beancount.query` / `beanquery` results, both of which expose a `dtype`. The v2 adapter also has access to typed columns. `tests/test_bql.py` is where the typed-column assertions land.

## Acceptance criteria

- [ ] `QueryResult.columns` shape changed to carry both name and datatype.
- [ ] Reference adapter populates the datatype tag from the underlying query result's dtype.
- [ ] v2 adapter populates the datatype tag from v2's equivalent.
- [ ] `tests/test_bql.py` has at least one test asserting datatype tags for queries that return Amount, Inventory, Decimal, and date columns.
- [ ] Existing BQL tests updated to the new shape.

## References

- Fava: `fava/core/query.py`, `fava/core/charts.py`
- beancompat: `implementations/adapter.py` (`QueryResult`), `tests/test_bql.py`
- Memory: `.claude/memory/fava_contract_surface.md`

"""Shared serialization and containment matching for portable fixtures.

The fixture format is documented in fixtures/README.md. This module provides:

- `parse_result_to_dict`: convert a ParseResult (as produced by any adapter)
  into the neutral JSON shape.
- `contains`: containment match — returns (ok, reason). The `expected` object
  is a lower bound; `actual` must contain everything in `expected`, but may
  have extra keys.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from implementations.adapter import ParseResult


# Source-location keys that are not portable across implementations or runs.
# `filename` is a temp path; `lineno` is impl-dependent bookkeeping. Neither
# belongs in an assertion by default. Fixture authors who want to assert on
# line numbers can add them back manually.
NON_PORTABLE_META_KEYS = {"filename", "lineno"}


def _strip_source_location(meta: dict) -> dict:
    return {k: v for k, v in meta.items() if k not in NON_PORTABLE_META_KEYS}


def _strip_posting_source_location(posting: dict) -> dict:
    posting = dict(posting)
    if "meta" in posting and isinstance(posting["meta"], dict):
        posting["meta"] = _strip_source_location(posting["meta"])
    return posting


def parse_result_to_dict(result: ParseResult, *, portable: bool = True) -> dict[str, Any]:
    """Convert a ParseResult into the neutral dict form used by fixtures.

    When `portable=True` (default), strips source-location metadata keys
    (`filename`, `lineno`) that are not stable across runs or implementations.
    """
    out_directives = []
    for d in result.directives:
        meta = dict(d.meta)
        data = _normalize(d.data)
        if portable:
            meta = _strip_source_location(meta)
            if isinstance(data, dict) and "postings" in data and isinstance(data["postings"], list):
                data["postings"] = [_strip_posting_source_location(p) for p in data["postings"]]
        out_directives.append(
            {
                "type": d.type,
                "date": d.date,
                "meta": meta,
                "data": data,
            }
        )
    return {
        "errors": list(result.errors),
        "directives": out_directives,
        "options": dict(result.options),
    }


def _normalize(value: Any) -> Any:
    """Recursively normalize a data payload so it round-trips through JSON.

    Adapter Directive.data may contain nested dicts/lists of primitives already;
    this is a defensive pass-through that leaves primitives as-is.
    """
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


def contains(actual: Any, expected: Any, path: str = "") -> tuple[bool, str]:
    """Containment match: every key/index in `expected` must appear in `actual`.

    Rules:
      - dict: every key in expected must be in actual, and values must match recursively.
        Extra keys in actual are ignored.
      - list: lengths must match; elements are matched positionally. (Exception: for
        the top-level `errors` list, see `contains_parse_result`.)
      - scalar: must be equal.
    """
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False, f"{path}: expected object, got {type(actual).__name__}"
        for k, v in expected.items():
            if k not in actual:
                return False, f"{path}.{k}: missing from actual"
            ok, reason = contains(actual[k], v, f"{path}.{k}")
            if not ok:
                return False, reason
        return True, ""

    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False, f"{path}: expected array, got {type(actual).__name__}"
        if len(actual) != len(expected):
            return (
                False,
                f"{path}: length mismatch (expected {len(expected)}, got {len(actual)})",
            )
        for i, (a, e) in enumerate(zip(actual, expected)):
            ok, reason = contains(a, e, f"{path}[{i}]")
            if not ok:
                return False, reason
        return True, ""

    if actual != expected:
        return False, f"{path}: expected {expected!r}, got {actual!r}"
    return True, ""


def contains_parse_result(actual: dict, expected: dict) -> tuple[bool, str]:
    """Apply containment matching to a ParseResult-shaped dict.

    `errors` is matched as a set (order-insensitive substring-equal), because
    error ordering is not a stable part of the contract. All other fields use
    positional containment.
    """
    expected_errors = expected.get("errors")
    if expected_errors is not None:
        actual_errors = actual.get("errors", [])
        missing = [e for e in expected_errors if e not in actual_errors]
        if missing:
            return False, f"errors: missing expected {missing!r} (actual: {actual_errors!r})"
        if not expected_errors and actual_errors:
            return False, f"errors: expected none, got {actual_errors!r}"

    expected_without_errors = {k: v for k, v in expected.items() if k != "errors"}
    return contains(actual, expected_without_errors)

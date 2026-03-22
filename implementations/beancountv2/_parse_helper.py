#!/usr/bin/env python3
"""Helper script: loads a beancount file and emits JSON to stdout.

Invoked as a subprocess to maintain black-box separation.
Usage: python3 _parse_helper.py <path.beancount>
"""

import json
import sys
from datetime import date
from decimal import Decimal
from enum import Enum


def default_serializer(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, frozenset):
        return sorted(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def serialize_meta(meta):
    """Serialize metadata dict, preserving user-defined keys."""
    if not meta:
        return {}
    result = {}
    for k, v in meta.items():
        if k.startswith("__"):
            continue  # skip internal keys like __tolerances__, __automatic__
        if isinstance(v, (str, int, float, bool, type(None))):
            result[k] = v
        elif isinstance(v, Decimal):
            result[k] = str(v)
        elif isinstance(v, date):
            result[k] = v.isoformat()
        # skip non-serializable values
    return result


def serialize_amount(amount):
    """Serialize a beancount Amount to dict."""
    if amount is None:
        return None
    return {"number": str(amount.number), "currency": amount.currency}


def serialize_cost(cost):
    """Serialize a beancount Cost/CostSpec to dict."""
    if cost is None:
        return None
    result = {}
    if hasattr(cost, "number") and cost.number is not None:
        result["number"] = str(cost.number)
    if hasattr(cost, "currency") and cost.currency is not None:
        result["currency"] = cost.currency
    if hasattr(cost, "date") and cost.date is not None:
        result["date"] = cost.date.isoformat()
    if hasattr(cost, "label") and cost.label is not None:
        result["label"] = cost.label
    return result or None


def directive_to_dict(entry):
    """Convert a beancount directive to a JSON-serializable dict."""
    type_name = type(entry).__name__.lower()

    d = {
        "type": type_name,
        "date": entry.date.isoformat(),
        "meta": serialize_meta(entry.meta),
        "data": {},
    }

    if type_name == "open":
        d["data"]["account"] = entry.account
        d["data"]["currencies"] = list(entry.currencies) if entry.currencies else []
        d["data"]["booking"] = entry.booking
    elif type_name == "close":
        d["data"]["account"] = entry.account
    elif type_name == "transaction":
        d["data"]["flag"] = entry.flag
        d["data"]["payee"] = entry.payee
        d["data"]["narration"] = entry.narration
        d["data"]["tags"] = sorted(entry.tags) if entry.tags else []
        d["data"]["links"] = sorted(entry.links) if entry.links else []
        d["data"]["postings"] = []
        for p in entry.postings or []:
            posting = {
                "account": p.account,
                "units": serialize_amount(p.units),
                "cost": serialize_cost(p.cost),
                "price": serialize_amount(p.price),
                "flag": p.flag,
                "meta": serialize_meta(p.meta),
            }
            d["data"]["postings"].append(posting)
    elif type_name == "balance":
        d["data"]["account"] = entry.account
        d["data"]["amount"] = serialize_amount(entry.amount)
        d["data"]["tolerance"] = str(entry.tolerance) if entry.tolerance else None
        d["data"]["diff_amount"] = serialize_amount(entry.diff_amount) if entry.diff_amount else None
    elif type_name == "pad":
        d["data"]["account"] = entry.account
        d["data"]["source_account"] = entry.source_account
    elif type_name == "commodity":
        d["data"]["currency"] = entry.currency
    elif type_name == "note":
        d["data"]["account"] = entry.account
        d["data"]["comment"] = entry.comment
    elif type_name == "document":
        d["data"]["account"] = entry.account
        d["data"]["filename"] = entry.filename
    elif type_name == "event":
        d["data"]["type"] = entry.type
        d["data"]["description"] = entry.description
    elif type_name == "query":
        d["data"]["name"] = entry.name
        d["data"]["query_string"] = entry.query_string
    elif type_name == "price":
        d["data"]["currency"] = entry.currency
        d["data"]["amount"] = serialize_amount(entry.amount)
    elif type_name == "custom":
        d["data"]["type"] = entry.type
        d["data"]["values"] = []
        if hasattr(entry, "values") and entry.values:
            for v in entry.values:
                if hasattr(v, "value"):
                    d["data"]["values"].append(str(v.value))
                else:
                    d["data"]["values"].append(str(v))

    return d


def run_query(path, query_string):
    """Load a file and execute a BQL query, emitting JSON."""
    try:
        import beanquery

        conn = beanquery.connect("beancount://" + path)
        result = conn.execute(query_string)

        columns = [col.name for col in result.description]
        rows = []
        for row in result:
            rows.append([str(v) if v is not None else None for v in row])

        output = {
            "columns": columns,
            "rows": rows,
            "errors": [],
        }
    except Exception as e:
        output = {
            "columns": [],
            "rows": [],
            "errors": [str(e)],
        }

    json.dump(output, sys.stdout, default=default_serializer)


def main():
    path = sys.argv[1]

    if len(sys.argv) >= 4 and sys.argv[2] == "--query":
        query_string = sys.argv[3]
        run_query(path, query_string)
        return

    from beancount import loader

    entries, errors, options = loader.load_file(path)

    # Serialize options, including lists of strings
    serialized_options = {}
    for k, v in options.items():
        if isinstance(v, (str, int, float, bool, type(None))):
            serialized_options[k] = v
        elif isinstance(v, list) and all(isinstance(i, str) for i in v):
            serialized_options[k] = v

    output = {
        "directives": [directive_to_dict(e) for e in entries],
        "errors": [str(e) for e in errors],
        "options": serialized_options,
    }

    json.dump(output, sys.stdout, default=default_serializer)


if __name__ == "__main__":
    main()

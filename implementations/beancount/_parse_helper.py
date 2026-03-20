#!/usr/bin/env python3
"""Helper script: loads a beancount file and emits JSON to stdout.

Invoked as a subprocess to maintain black-box separation.
Usage: python3 _parse_helper.py <path.beancount>
"""

import json
import sys
from decimal import Decimal


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, frozenset):
        return sorted(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def directive_to_dict(entry):
    """Convert a beancount directive to a JSON-serializable dict."""
    type_name = type(entry).__name__.lower()
    meta = dict(entry.meta) if entry.meta else {}
    # Remove non-serializable internal meta keys
    meta = {
        k: v
        for k, v in meta.items()
        if isinstance(v, (str, int, float, bool, type(None)))
    }

    d = {
        "type": type_name,
        "date": entry.date.isoformat(),
        "meta": meta,
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
                "units": None,
                "cost": None,
                "price": None,
                "flag": p.flag,
            }
            if p.units is not None:
                posting["units"] = {
                    "number": str(p.units.number),
                    "currency": p.units.currency,
                }
            d["data"]["postings"].append(posting)
    elif type_name == "balance":
        d["data"]["account"] = entry.account
        if entry.amount is not None:
            d["data"]["amount"] = {
                "number": str(entry.amount.number),
                "currency": entry.amount.currency,
            }
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
    elif type_name == "custom":
        d["data"]["type"] = entry.type

    return d


def main():
    path = sys.argv[1]

    from beancount import loader

    entries, errors, options = loader.load_file(path)

    output = {
        "directives": [directive_to_dict(e) for e in entries],
        "errors": [str(e) for e in errors],
        "options": {
            k: v
            for k, v in options.items()
            if isinstance(v, (str, int, float, bool, type(None)))
        },
    }

    json.dump(output, sys.stdout, default=decimal_default)


if __name__ == "__main__":
    main()

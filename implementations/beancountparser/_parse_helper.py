#!/usr/bin/env python3
"""Helper script: parses a beancount file with beancount-parser and emits JSON.

Invoked as a subprocess to maintain black-box separation.
Usage: python3 _parse_helper.py <path.beancount>

Emits the same JSON schema as the beancount adapter's helper:
{
    "directives": [...],
    "errors": [...],
    "options": {...}
}
"""

import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from lark import Token, Tree


def eval_number_expr(node):
    """Evaluate a number_expr tree to a Decimal."""
    if isinstance(node, Token):
        if node.type == "NUMBER":
            return Decimal(str(node))
        return None

    if isinstance(node, Tree):
        rule = str(node.data)

        if rule == "number_expr":
            return eval_number_expr(node.children[0])

        if rule == "number_atom":
            # unary: [UNARY_OP, number]
            if len(node.children) == 2:
                op = str(node.children[0])
                val = eval_number_expr(node.children[1])
                if val is not None and op == "-":
                    return -val
                return val
            return eval_number_expr(node.children[0])

        if rule == "number_add_expr":
            left = eval_number_expr(node.children[0])
            op = str(node.children[1])
            right = eval_number_expr(node.children[2])
            if left is not None and right is not None:
                return left + right if op == "+" else left - right
            return None

        if rule == "number_mul_expr":
            left = eval_number_expr(node.children[0])
            op = str(node.children[1])
            right = eval_number_expr(node.children[2])
            if left is not None and right is not None:
                return left * right if op == "*" else left / right
            return None

        # Single child passthrough
        if len(node.children) == 1:
            return eval_number_expr(node.children[0])

    return None


def extract_amount(amount_tree):
    """Extract {number, currency} from an amount tree."""
    if amount_tree is None or not isinstance(amount_tree, Tree):
        return None
    number = eval_number_expr(amount_tree.children[0])
    currency = str(amount_tree.children[1])
    return {"number": str(number) if number is not None else None, "currency": currency}


def extract_cost(cost_tree):
    """Extract cost dict from a cost_spec tree."""
    if cost_tree is None or not isinstance(cost_tree, Tree):
        return None
    result = {}
    for item in cost_tree.children:
        if not isinstance(item, Tree) or str(item.data) != "cost_item":
            continue
        child = item.children[0]
        if isinstance(child, Tree) and str(child.data) == "amount":
            amt = extract_amount(child)
            if amt:
                result["number"] = amt["number"]
                result["currency"] = amt["currency"]
        elif isinstance(child, Token):
            if child.type == "DATE":
                result["date"] = str(child)
            elif child.type == "ESCAPED_STRING":
                result["label"] = str(child).strip('"')
    return result or None


def extract_price(price_tree):
    """Extract price amount from per_unit_price or total_price tree."""
    if price_tree is None or not isinstance(price_tree, Tree):
        return None
    # Both per_unit_price and total_price have a single amount child
    return extract_amount(price_tree.children[0])


def unquote(token):
    """Remove quotes from an ESCAPED_STRING token."""
    s = str(token)
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s


def parse_metadata_value(value_node):
    """Parse a metadata value token/tree to a Python value."""
    if isinstance(value_node, Token):
        if value_node.type == "ESCAPED_STRING":
            return unquote(value_node)
        if value_node.type == "NUMBER":
            return str(Decimal(str(value_node)))
        if value_node.type == "DATE":
            return str(value_node)
        if value_node.type == "BOOLEAN":
            return str(value_node).upper() == "TRUE"
        if value_node.type == "ACCOUNT":
            return str(value_node)
        if value_node.type == "CURRENCY":
            return str(value_node)
        return str(value_node)
    if isinstance(value_node, Tree):
        if str(value_node.data) == "amount":
            return extract_amount(value_node)
        if str(value_node.data) == "number_expr":
            val = eval_number_expr(value_node)
            return str(val) if val is not None else None
    return str(value_node)


def walk_tree(tree):
    """Walk the Lark parse tree and extract directives, errors, and options."""
    directives = []
    errors = []
    options = {}

    # The tree is flat: statements are siblings, not nested.
    # A date_directive is followed by metadata_item and posting statements
    # that belong to it. We track the "current directive" to attach them.
    current_directive = None
    current_postings = None
    current_meta = None

    def flush_directive():
        nonlocal current_directive, current_postings, current_meta
        if current_directive is not None:
            if current_meta:
                current_directive["meta"] = current_meta
            if current_postings is not None:
                current_directive["data"]["postings"] = current_postings
            directives.append(current_directive)
        current_directive = None
        current_postings = None
        current_meta = None

    # Track current posting for posting-level metadata
    current_posting = None
    current_posting_meta = None

    def flush_posting():
        nonlocal current_posting, current_posting_meta
        if current_posting is not None:
            if current_posting_meta:
                current_posting["meta"] = current_posting_meta
            if current_postings is not None:
                current_postings.append(current_posting)
        current_posting = None
        current_posting_meta = None

    for stmt in tree.children:
        if not isinstance(stmt, Tree) or str(stmt.data) != "statement":
            continue

        child = stmt.children[0]
        if child is None:
            continue

        if not isinstance(child, Tree):
            continue

        rule = str(child.data)

        if rule == "date_directive":
            flush_posting()
            flush_directive()
            directive_node = child.children[0]
            if isinstance(directive_node, Tree):
                d = extract_directive(directive_node)
                if d:
                    current_directive = d
                    current_meta = {}
                    if d["type"] == "transaction":
                        current_postings = []

        elif rule == "metadata_item":
            key = str(child.children[0])
            value = parse_metadata_value(child.children[1]) if len(child.children) > 1 else None
            if current_posting is not None:
                if current_posting_meta is None:
                    current_posting_meta = {}
                current_posting_meta[key] = value
            elif current_meta is not None:
                current_meta[key] = value

        elif rule == "posting":
            flush_posting()
            posting = extract_posting(child)
            if posting is not None:
                current_posting = posting
                current_posting_meta = {}

        elif rule == "simple_directive":
            flush_posting()
            flush_directive()
            # option, plugin, include, pushtag, poptag
            inner = child.children[0]
            if isinstance(inner, Tree):
                inner_rule = str(inner.data)
                if inner_rule == "option":
                    key = unquote(inner.children[0])
                    value = unquote(inner.children[1]) if len(inner.children) > 1 else ""
                    options[key] = value

    flush_posting()
    flush_directive()

    return directives, errors, options


def extract_directive(node):
    """Extract a directive dict from a date_directive child tree."""
    rule = str(node.data)
    children = node.children

    date_str = str(children[0])

    if rule == "txn":
        return extract_txn(children, date_str)
    elif rule == "open":
        return extract_open(children, date_str)
    elif rule == "close":
        return extract_close(children, date_str)
    elif rule == "balance":
        return extract_balance(children, date_str)
    elif rule == "pad":
        return extract_pad(children, date_str)
    elif rule == "note":
        return extract_note(children, date_str)
    elif rule == "event":
        return extract_event(children, date_str)
    elif rule == "commodity":
        return extract_commodity(children, date_str)
    elif rule == "price":
        return extract_price_directive(children, date_str)
    elif rule == "custom":
        return extract_custom(children, date_str)
    elif rule == "document":
        return extract_document(children, date_str)
    elif rule == "query":
        return extract_query_directive(children, date_str)

    return None


def extract_txn(children, date_str):
    """Extract transaction directive."""
    # children: DATE, FLAG, [payee], narration, [annotations]
    flag = str(children[1]) if children[1] is not None else "*"

    payee = None
    narration = None
    tags = []
    links = []

    # Find the string tokens (payee and/or narration)
    strings = []
    for c in children[2:]:
        if isinstance(c, Token) and c.type == "ESCAPED_STRING":
            strings.append(unquote(c))
        elif isinstance(c, Tree) and str(c.data) == "annotations":
            for ann in c.children:
                if isinstance(ann, Token):
                    s = str(ann)
                    if ann.type == "TAG":
                        tags.append(s[1:])  # strip #
                    elif ann.type == "LINK":
                        links.append(s[1:])  # strip ^

    if len(strings) == 2:
        payee = strings[0]
        narration = strings[1]
    elif len(strings) == 1:
        narration = strings[0]

    return {
        "type": "transaction",
        "date": date_str,
        "meta": {},
        "data": {
            "flag": flag,
            "payee": payee,
            "narration": narration,
            "tags": sorted(tags),
            "links": sorted(links),
            "postings": [],
        },
    }


def extract_open(children, date_str):
    """Extract open directive."""
    account = str(children[1])
    currencies = []
    booking = None

    for c in children[2:]:
        if isinstance(c, Tree) and str(c.data) == "currencies":
            currencies = [str(t) for t in c.children if isinstance(t, Token)]
        elif isinstance(c, Token) and c.type == "ESCAPED_STRING":
            booking = unquote(c)

    return {
        "type": "open",
        "date": date_str,
        "meta": {},
        "data": {
            "account": account,
            "currencies": currencies,
            "booking": booking,
        },
    }


def extract_close(children, date_str):
    return {
        "type": "close",
        "date": date_str,
        "meta": {},
        "data": {"account": str(children[1])},
    }


def extract_balance(children, date_str):
    # children: DATE, ACCOUNT, amount
    account = str(children[1])
    amount = extract_amount(children[2]) if len(children) > 2 else None
    return {
        "type": "balance",
        "date": date_str,
        "meta": {},
        "data": {
            "account": account,
            "amount": amount,
            "tolerance": None,
            "diff_amount": None,
        },
    }


def extract_pad(children, date_str):
    return {
        "type": "pad",
        "date": date_str,
        "meta": {},
        "data": {
            "account": str(children[1]),
            "source_account": str(children[2]),
        },
    }


def extract_note(children, date_str):
    return {
        "type": "note",
        "date": date_str,
        "meta": {},
        "data": {
            "account": str(children[1]),
            "comment": unquote(children[2]),
        },
    }


def extract_event(children, date_str):
    return {
        "type": "event",
        "date": date_str,
        "meta": {},
        "data": {
            "type": unquote(children[1]),
            "description": unquote(children[2]),
        },
    }


def extract_commodity(children, date_str):
    return {
        "type": "commodity",
        "date": date_str,
        "meta": {},
        "data": {"currency": str(children[1])},
    }


def extract_price_directive(children, date_str):
    # children: DATE, CURRENCY, amount
    currency = str(children[1])
    amount = extract_amount(children[2]) if len(children) > 2 else None
    return {
        "type": "price",
        "date": date_str,
        "meta": {},
        "data": {
            "currency": currency,
            "amount": amount,
        },
    }


def extract_custom(children, date_str):
    # children: DATE, ESCAPED_STRING (type), ...values
    custom_type = unquote(children[1])
    values = []
    for c in children[2:]:
        if c is None:
            continue
        if isinstance(c, Token):
            if c.type == "ESCAPED_STRING":
                values.append(unquote(c))
            elif c.type == "ACCOUNT":
                values.append(str(c))
            elif c.type == "NUMBER":
                values.append(str(c))
            elif c.type == "BOOLEAN":
                values.append(str(c))
            elif c.type == "DATE":
                values.append(str(c))
            elif c.type == "CURRENCY":
                values.append(str(c))
            else:
                values.append(str(c))
        elif isinstance(c, Tree):
            if str(c.data) == "amount":
                amt = extract_amount(c)
                if amt:
                    values.append("%s %s" % (amt["number"], amt["currency"]))
            elif str(c.data) == "number_expr":
                val = eval_number_expr(c)
                if val is not None:
                    values.append(str(val))

    return {
        "type": "custom",
        "date": date_str,
        "meta": {},
        "data": {
            "type": custom_type,
            "values": values,
        },
    }


def extract_document(children, date_str):
    return {
        "type": "document",
        "date": date_str,
        "meta": {},
        "data": {
            "account": str(children[1]),
            "filename": unquote(children[2]),
        },
    }


def extract_query_directive(children, date_str):
    return {
        "type": "query",
        "date": date_str,
        "meta": {},
        "data": {
            "name": unquote(children[1]),
            "query_string": unquote(children[2]),
        },
    }


def extract_posting(posting_tree):
    """Extract a posting dict from a posting tree."""
    inner = posting_tree.children[0]
    if not isinstance(inner, Tree):
        return None

    rule = str(inner.data)

    if rule == "simple_posting":
        flag = None
        if inner.children[0] is not None:
            flag = str(inner.children[0])
        account = str(inner.children[1])
        return {
            "account": account,
            "units": None,
            "cost": None,
            "price": None,
            "flag": flag,
            "meta": {},
        }

    if rule == "detailed_posting":
        # children: [flag], ACCOUNT, amount, [cost_spec], [price]
        flag = None
        if inner.children[0] is not None:
            flag = str(inner.children[0])
        account = str(inner.children[1])
        units = extract_amount(inner.children[2]) if inner.children[2] is not None else None
        cost = extract_cost(inner.children[3]) if len(inner.children) > 3 and inner.children[3] is not None else None
        price = extract_price(inner.children[4]) if len(inner.children) > 4 and inner.children[4] is not None else None

        return {
            "account": account,
            "units": units,
            "cost": cost,
            "price": price,
            "flag": flag,
            "meta": {},
        }

    return None


def main():
    path = sys.argv[1]
    content = Path(path).read_text()

    from beancount_parser.parser import make_parser

    p = make_parser()

    try:
        tree = p.parse(content)
    except Exception as e:
        output = {
            "directives": [],
            "errors": [str(e)],
            "options": {},
        }
        json.dump(output, sys.stdout)
        return

    directives, errors, options = walk_tree(tree)

    output = {
        "directives": directives,
        "errors": errors,
        "options": options,
    }

    json.dump(output, sys.stdout)


if __name__ == "__main__":
    main()

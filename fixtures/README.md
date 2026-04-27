# Portable fixtures

Language-independent test fixtures. Each fixture is a single JSON file containing a `.beancount` source snippet and the expected parse output in a neutral shape. Any implementation — in any language — can load these files, parse the embedded source, serialize its own output to the same shape, and compare.

This is the "executable spec" artifact: the reference implementation (beancount v3) is the source of truth, and the fixtures capture what it produces for a curated set of inputs. Other implementations are free to match, diverge, or extend — the fixtures make the facts visible.

## File layout

```
fixtures/
  README.md            — this file
  parse/               — parse-tier: pure syntax, no semantic checking required
    <name>.json
  check/               — check-tier: requires booking, interpolation, date sort
    <name>.json
```

The tier is the capability requirement. An implementation that exposes only a
parser (like `beancount-parser`, `beancount-parser-lima`) is expected to pass
`parse/` fixtures. Implementations that also do balance checking, auto-posting
interpolation, and date-sorted output (like beancount v2/v3) are expected to
pass `check/` fixtures as well.

## Fixture schema

```json
{
  "name": "open_single",
  "description": "Single open directive with one currency constraint.",
  "source": "2024-01-01 open Assets:Bank USD\n",
  "known_divergences": {
    "beancount-parser-lima": "Emits currencies in alphabetical order rather than source order."
  },
  "expected": {
    "errors": [],
    "directives": [
      {
        "type": "open",
        "date": "2024-01-01",
        "data": {
          "account": "Assets:Bank",
          "currencies": ["USD"]
        }
      }
    ]
  }
}
```

### Fields

- `name` *(string)* — short identifier, typically matches the filename stem.
- `description` *(string)* — one-line human-readable description.
- `source` *(string)* — complete `.beancount` input. Include a trailing newline.
- `known_divergences` *(object, optional)* — map of `adapter_name → reason`.
  Fixture authors record known semantic differences for implementations that
  will not pass, so the divergence is visible in the suite without being
  confused with setup bugs. The Python test runner treats these as xfail.
- `expected` *(object)* — lower-bound assertion on the parse output.
  - `errors` *(array of string)* — parse/check errors. Usually `[]` for happy-path fixtures.
  - `directives` *(array of object)* — expected directives in document order.
  - `options` *(object, optional)* — options that must be present. Usually omitted; most options are implementation-specific. Special keys:
    - `display_precision_by_currency` *(object)* — per-currency display precision inferred from transaction amounts. Shape: `{"USD": 2, "JPY": 0}` (currency → integer decimal-place count). Derived from `dcontext.build().fmtstrings`; currencies with no explicit precision format are omitted. Parser-only adapters (no loader) emit `{}`.

### Directive shape

```json
{
  "type": "open" | "close" | "transaction" | "balance" | "pad" | "commodity" | "note" | "document" | "event" | "query" | "price" | "custom",
  "date": "YYYY-MM-DD",
  "meta": { ... user-defined metadata keys ... },
  "data": { ... type-specific fields ... }
}
```

Type-specific `data` fields (see `scripts/generate_fixtures.py` and `implementations/beancount/_parse_helper.py` for the canonical serialization):

| Type          | Required `data` keys |
|---------------|----------------------|
| `open`        | `account`, `currencies` (array, possibly empty), `booking` (nullable string) |
| `close`       | `account` |
| `transaction` | `flag`, `payee` (nullable), `narration`, `tags` (sorted array), `links` (sorted array), `postings` (array) |
| `balance`     | `account`, `amount` (`{number, currency}`) |
| `pad`         | `account`, `source_account` |
| `commodity`   | `currency` |
| `price`       | `currency`, `amount` |
| `note`        | `account`, `comment` |
| `event`       | `type`, `description` |

Posting shape: `{account, units: {number, currency} | null, cost: Cost | CostSpec | null, price: {number, currency} | null, flag: string | null, meta: object}`.

Cost vs CostSpec — a posting's `cost` field carries a `kind` discriminator:

- `{"kind": "cost", "number": "...", "currency": "...", "date"?: "...", "label"?: "..."}` — a booked Cost, produced after the loader's booking pass. Emitted by implementations at the check tier (CAP_BOOKING).
- `{"kind": "cost_spec", "number_per"?: "...", "number_total"?: "...", "merge"?: bool, "currency"?: "...", "date"?: "...", "label"?: "..."}` — an unbooked CostSpec, produced by parser-only implementations or at the parse tier.

Fava renders these differently; implementations must emit the right shape for their tier. The same source can produce `cost_spec` at parse tier and `cost` at check tier.

Numbers are serialized as decimal strings (e.g. `"50.00"`), never floats, to preserve precision.

## Matching semantics: containment, not equality

An implementation **passes** a fixture when its parse output *contains* `expected`. Specifically:

- Every key in `expected.errors` must appear in actual `errors` (order-insensitive).
- `expected.directives` must match actual `directives` positionally (same length, same order).
- For each directive, every key in `expected` must appear in actual with the same value. Keys in actual that are absent from expected are ignored.
- Nested `data` and `meta` objects follow the same rule recursively.

This is deliberate:

- **Forgiving of extensions.** An implementation that emits extra metadata or extra options keys does not fail.
- **Strict on stated behavior.** Anything the fixture declares must match exactly.
- **Portable across implementations with different option dictionaries.** v3 emits ~30 options keys; v2 emits fewer; a new Rust impl may emit none. Fixtures declare only what's load-bearing.

## Consuming fixtures from a non-Python implementation

1. Decide which tier(s) to run: `fixtures/parse/` if your project is a parser, plus `fixtures/check/` if it also does booking/interpolation.
2. For each fixture JSON file:
   a. Parse the JSON.
   b. If `known_divergences[your-name]` is present, record the case as *expected-fail* (xfail) and continue.
   c. Write the `source` string to a temp `.beancount` file (or pass as stdin if your parser supports it).
   d. Run your parser. Serialize your parse result to the schema above.
   e. Apply containment matching against `expected`. Record pass/fail.
3. Report aggregate pass / xfail / fail counts.

A minimal Rust harness is ~100 lines with `serde_json` + your parser. A Zig harness is similar with `std.json`. No Python runtime required at test time.

## Regenerating fixtures

```bash
# Regenerate the `expected` field of every fixture using the reference adapter (beancount v3):
python scripts/generate_fixtures.py

# Regenerate a single fixture:
python scripts/generate_fixtures.py fixtures/parse/open_single.json
```

The generator preserves `name`, `description`, and `source`; it overwrites only `expected`. Review the diff and commit.

## Running fixtures against a registered adapter

```bash
# Run all fixtures against a specific adapter:
python scripts/run_fixtures.py --adapter beancount-parser-lima

# Run via pytest (exercises all available adapters, respecting tiering and known_divergences):
pytest tests/test_fixtures.py -v
```

## Seeding a new fixture

1. Create `fixtures/parse/<name>.json` (or `check/<name>.json`) with:
   ```json
   { "name": "...", "description": "...", "source": "...", "expected": {} }
   ```
2. Run `python scripts/generate_fixtures.py fixtures/parse/<name>.json`. The generator parses `source` with the reference adapter and fills in `expected`.
3. Run `pytest tests/test_fixtures.py` against all adapters. Any non-reference failure is a candidate for `known_divergences` (if intentional) or a bug report (if not).

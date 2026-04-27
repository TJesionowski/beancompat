//! Parse+book helper for limabean.
//!
//! Reads a beancount file, parses it with beancount-parser-lima, and emits JSON
//! to stdout in the portable schema used by all beancompat adapters.
//!
//! Usage:
//!   limabean-helper <path.beancount>               # parse only (no booking)
//!   limabean-helper <path.beancount> --booked      # parse + booking (TODO)
//!
//! # Booking integration (TODO — next iteration)
//!
//! Booking requires implementing PostingSpec for beancount-parser-lima's
//! Posting<'a> type.  The limabean-booking crate's "lima-parser-types" feature
//! provides LimaParserBookingTypes<'a> (BookingTypes impl) and LimaTolerance<'a>
//! (Tolerance impl derived from parser Options).  You still need:
//!
//! 1. Implement limabean_booking::PostingSpec for a wrapper around
//!    beancount_parser_lima::Posting<'a> that maps:
//!      - account()  -> &'a str
//!      - units()    -> Option<rust_decimal::Decimal>
//!      - currency() -> Option<&'a str>
//!      - cost()     -> Option<&Self::CostSpec>
//!      - price()    -> Option<&Self::PriceSpec>
//!
//! 2. Implement CostSpec and PriceSpec for the parser's cost/price types.
//!
//! 3. In main: iterate sorted directives, maintain an Inventory map keyed by
//!    account &str, and call limabean_booking::book() per transaction:
//!
//!      let tolerance = LimaTolerance::from(&options);
//!      let mut positions: HashMap<&str, Positions<LimaParserBookingTypes>> = HashMap::new();
//!      for txn in transactions {
//!          let booked = limabean_booking::book(
//!              txn.date().item(),
//!              &posting_wrappers,
//!              &tolerance,
//!              |acct| positions.get(acct),
//!              |acct| open_booking_method(acct),
//!          )?;
//!          // update positions, serialize booked postings into output JSON
//!      }

use beancount_parser_lima::{
    BeancountParser, BeancountSources, DirectiveVariant, Flag, MetaValue, PriceSpec,
    ScopedExprValue, SimpleValue,
};
use serde_json::{json, Value};
use std::env;
use std::path::PathBuf;
use std::process;

fn flag_to_str(flag: &Flag) -> &'static str {
    match flag {
        Flag::Asterisk => "*",
        Flag::Exclamation => "!",
        Flag::Ampersand => "&",
        Flag::Hash => "#",
        Flag::Question => "?",
        Flag::Percent => "%",
        Flag::Letter(_) => "?",
    }
}

fn meta_value_to_json(mv: &MetaValue) -> Value {
    match mv {
        MetaValue::Simple(sv) => match sv {
            SimpleValue::String(s) => json!(s),
            SimpleValue::Currency(c) => json!(c.as_ref()),
            SimpleValue::Account(a) => json!(a.as_ref()),
            SimpleValue::Tag(t) => json!(t.as_ref()),
            SimpleValue::Link(l) => json!(l.as_ref()),
            SimpleValue::Date(d) => json!(d.to_string()),
            SimpleValue::Bool(b) => json!(b),
            SimpleValue::Null => Value::Null,
            SimpleValue::Expr(ev) => json!(ev.value().to_string()),
        },
        MetaValue::Amount(a) => {
            json!({
                "number": a.number().item().value().to_string(),
                "currency": a.currency().item().as_ref(),
            })
        }
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: limabean-helper <path.beancount>");
        process::exit(1);
    }

    let path = PathBuf::from(&args[1]);
    let sources = match BeancountSources::try_from(path) {
        Ok(s) => s,
        Err(e) => {
            let output = json!({
                "directives": [],
                "errors": [format!("Failed to read file: {}", e)],
                "options": {},
            });
            println!("{}", output);
            return;
        }
    };

    let parser = BeancountParser::new(&sources);

    match parser.parse() {
        Ok(success) => {
            let mut directives = Vec::new();

            for directive in success.directives {
                let date = directive.date().item().to_string();
                let metadata = directive.metadata();

                let mut meta = serde_json::Map::new();
                for (key, value) in metadata.key_values() {
                    let k = key.item().as_ref().to_string();
                    let v = meta_value_to_json(value.item());
                    meta.insert(k, v);
                }

                let tags: Vec<String> = metadata
                    .tags()
                    .map(|t| t.item().as_ref().to_string())
                    .collect();
                let links: Vec<String> = metadata
                    .links()
                    .map(|l| l.item().as_ref().to_string())
                    .collect();

                let (type_name, data) = match directive.variant() {
                    DirectiveVariant::Transaction(txn) => {
                        let mut postings = Vec::new();
                        for sp in txn.postings() {
                            let p = sp.item();
                            let flag = p.flag().map(|f| flag_to_str(f.item()));

                            let units = match (p.amount(), p.currency()) {
                                (Some(num), Some(cur)) => Some(json!({
                                    "number": num.item().value().to_string(),
                                    "currency": cur.item().as_ref(),
                                })),
                                _ => None,
                            };

                            // limabean is parse-only in this iteration; costs are always CostSpec.
                            let cost = p.cost_spec().map(|cs| {
                                let cs = cs.item();
                                let mut cost_obj = serde_json::Map::new();
                                cost_obj.insert("kind".into(), json!("cost_spec"));
                                if let Some(per_unit) = cs.per_unit() {
                                    cost_obj.insert(
                                        "number_per".into(),
                                        json!(per_unit.item().value().to_string()),
                                    );
                                }
                                if let Some(total) = cs.total() {
                                    cost_obj.insert(
                                        "number_total".into(),
                                        json!(total.item().value().to_string()),
                                    );
                                }
                                if let Some(cur) = cs.currency() {
                                    cost_obj
                                        .insert("currency".into(), json!(cur.item().as_ref()));
                                }
                                if let Some(d) = cs.date() {
                                    cost_obj.insert("date".into(), json!(d.item().to_string()));
                                }
                                if let Some(label) = cs.label() {
                                    cost_obj.insert("label".into(), json!(label.item()));
                                }
                                Value::Object(cost_obj)
                            });

                            let price = p.price_annotation().map(|pa| {
                                let pa = pa.item();
                                match pa {
                                    PriceSpec::CurrencyAmount(scoped, cur) => {
                                        let num = match scoped {
                                            ScopedExprValue::PerUnit(ev) => ev.value().to_string(),
                                            ScopedExprValue::Total(ev) => ev.value().to_string(),
                                        };
                                        json!({
                                            "number": num,
                                            "currency": cur.as_ref(),
                                        })
                                    }
                                    PriceSpec::BareAmount(scoped) => {
                                        let num = match scoped {
                                            ScopedExprValue::PerUnit(ev) => ev.value().to_string(),
                                            ScopedExprValue::Total(ev) => ev.value().to_string(),
                                        };
                                        json!({ "number": num })
                                    }
                                    PriceSpec::BareCurrency(cur) => {
                                        json!({ "currency": cur.as_ref() })
                                    }
                                    PriceSpec::Unspecified => Value::Null,
                                }
                            });

                            let p_meta = p.metadata();
                            let mut posting_meta = serde_json::Map::new();
                            for (key, value) in p_meta.key_values() {
                                let k = key.item().as_ref().to_string();
                                let v = meta_value_to_json(value.item());
                                posting_meta.insert(k, v);
                            }

                            postings.push(json!({
                                "account": p.account().item().as_ref(),
                                "units": units,
                                "cost": cost,
                                "price": price,
                                "flag": flag,
                                "meta": Value::Object(posting_meta),
                            }));
                        }

                        let mut sorted_tags = tags.clone();
                        sorted_tags.sort();
                        let mut sorted_links = links.clone();
                        sorted_links.sort();

                        (
                            "transaction",
                            json!({
                                "flag": flag_to_str(txn.flag().item()),
                                "payee": txn.payee().map(|p| p.item().to_string()),
                                "narration": txn.narration().map(|n| n.item().to_string()),
                                "tags": sorted_tags,
                                "links": sorted_links,
                                "postings": postings,
                            }),
                        )
                    }
                    DirectiveVariant::Open(open) => {
                        let currencies: Vec<String> = open
                            .currencies()
                            .map(|c| c.item().as_ref().to_string())
                            .collect();
                        let booking = open.booking().map(|b| format!("{}", b.item()));

                        (
                            "open",
                            json!({
                                "account": open.account().item().as_ref(),
                                "currencies": currencies,
                                "booking": booking,
                            }),
                        )
                    }
                    DirectiveVariant::Close(close) => (
                        "close",
                        json!({
                            "account": close.account().item().as_ref(),
                        }),
                    ),
                    DirectiveVariant::Balance(bal) => {
                        let atol = bal.atol().item();
                        let amount = atol.amount().item();
                        let tolerance = atol.tolerance().map(|t| t.item().to_string());

                        (
                            "balance",
                            json!({
                                "account": bal.account().item().as_ref(),
                                "amount": {
                                    "number": amount.number().item().value().to_string(),
                                    "currency": amount.currency().item().as_ref(),
                                },
                                "tolerance": tolerance,
                                "diff_amount": null,
                            }),
                        )
                    }
                    DirectiveVariant::Pad(pad) => (
                        "pad",
                        json!({
                            "account": pad.account().item().as_ref(),
                            "source_account": pad.source().item().as_ref(),
                        }),
                    ),
                    DirectiveVariant::Note(note) => (
                        "note",
                        json!({
                            "account": note.account().item().as_ref(),
                            "comment": note.comment().item().to_string(),
                        }),
                    ),
                    DirectiveVariant::Event(event) => (
                        "event",
                        json!({
                            "type": event.event_type().item().to_string(),
                            "description": event.description().item().to_string(),
                        }),
                    ),
                    DirectiveVariant::Commodity(commodity) => (
                        "commodity",
                        json!({
                            "currency": commodity.currency().item().as_ref(),
                        }),
                    ),
                    DirectiveVariant::Price(price) => {
                        let amount = price.amount().item();
                        (
                            "price",
                            json!({
                                "currency": price.currency().item().as_ref(),
                                "amount": {
                                    "number": amount.number().item().value().to_string(),
                                    "currency": amount.currency().item().as_ref(),
                                },
                            }),
                        )
                    }
                    DirectiveVariant::Query(query) => (
                        "query",
                        json!({
                            "name": query.name().item().to_string(),
                            "query_string": query.content().item().to_string(),
                        }),
                    ),
                    DirectiveVariant::Custom(custom) => {
                        let values: Vec<Value> = custom
                            .values()
                            .map(|v| meta_value_to_json(v.item()))
                            .collect();

                        (
                            "custom",
                            json!({
                                "type": custom.type_().item().to_string(),
                                "values": values,
                            }),
                        )
                    }
                    DirectiveVariant::Document(doc) => (
                        "document",
                        json!({
                            "account": doc.account().item().as_ref(),
                            "filename": doc.path().item().to_string(),
                        }),
                    ),
                };

                directives.push(json!({
                    "type": type_name,
                    "date": date,
                    "meta": Value::Object(meta),
                    "data": data,
                }));
            }

            let mut options = serde_json::Map::new();
            if let Some(title) = success.options.title() {
                options.insert("title".into(), json!(title.item().to_string()));
            }
            let op_currencies: Vec<String> = success
                .options
                .operating_currency()
                .map(|c| c.as_ref().to_string())
                .collect();
            if !op_currencies.is_empty() {
                options.insert("operating_currency".into(), json!(op_currencies));
            }

            let output = json!({
                "directives": directives,
                "errors": [],
                "options": Value::Object(options),
            });
            println!("{}", output);
        }
        Err(parse_error) => {
            let errors: Vec<String> = parse_error
                .errors
                .iter()
                .map(|e| format!("{:?}", e))
                .collect();

            let output = json!({
                "directives": [],
                "errors": errors,
                "options": {},
            });
            println!("{}", output);
        }
    }
}

//! Parse+book helper for limabean.
//!
//! Reads a beancount file, parses it with beancount-parser-lima, runs the
//! limabean booking algorithm, and emits JSON to stdout in the portable schema
//! used by all beancompat adapters.
//!
//! Usage:
//!   limabean-helper <path.beancount>
//!
//! Always runs the full pipeline: parse + booking.

use beancount_parser_lima::{
    BeancountParser, BeancountSources, DirectiveVariant, Flag, MetaValue, PriceSpec,
    ScopedExprValue, SimpleValue,
};
use limabean_booking::{book, Booking, LimaParserBookingTypes, LimaTolerance, Positions};
use serde_json::{json, Value};
use std::collections::HashMap;
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
            // Pass 1: build account -> booking method map from Open directives.
            // Safe to do in one pass before transactions because beancount requires
            // accounts to be opened before use, so opens precede transactions in practice.
            let mut account_booking: HashMap<&str, Booking> = HashMap::new();
            for directive in &success.directives {
                if let DirectiveVariant::Open(open) = directive.variant() {
                    let method = open
                        .booking()
                        .map(|b| Booking::from(*b.item()))
                        .unwrap_or_default();
                    account_booking.insert(open.account().item().as_ref(), method);
                }
            }

            let tolerance = LimaTolerance::from(&success.options);
            let mut inventory: HashMap<&str, Positions<LimaParserBookingTypes>> =
                HashMap::new();

            // Pass 2: serialize all directives, booking each transaction.
            let mut directives_json = Vec::new();
            let mut booking_errors: Vec<String> = Vec::new();

            for directive in &success.directives {
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
                        let posting_list: Vec<_> = txn.postings().collect();
                        let txn_date = *directive.date().item();

                        let mut sorted_tags = tags.clone();
                        sorted_tags.sort();
                        let mut sorted_links = links.clone();
                        sorted_links.sort();

                        match book(
                            txn_date,
                            &posting_list,
                            &tolerance,
                            |acct| inventory.get(acct),
                            |acct| account_booking.get(acct).copied().unwrap_or_default(),
                        ) {
                            Ok(bookings) => {
                                // Update inventory before serializing.
                                let (interp_postings, updated_inv) = (
                                    bookings.interpolated_postings,
                                    bookings.updated_inventory,
                                );
                                for (acct, positions) in updated_inv {
                                    inventory.insert(acct, positions);
                                }

                                // Zip booked postings with originals (1:1, aligned by idx).
                                let mut postings_json = Vec::new();
                                for (orig_sp, interp) in
                                    posting_list.iter().zip(interp_postings.iter())
                                {
                                    let raw_p = orig_sp.item();
                                    let flag =
                                        raw_p.flag().map(|f| flag_to_str(f.item()));

                                    let mut posting_meta = serde_json::Map::new();
                                    for (key, value) in raw_p.metadata().key_values() {
                                        posting_meta.insert(
                                            key.item().as_ref().to_string(),
                                            meta_value_to_json(value.item()),
                                        );
                                    }

                                    let units = json!({
                                        "number": interp.units.to_string(),
                                        "currency": interp.currency,
                                    });

                                    // Resolved cost (from CostSpec after booking).
                                    let cost =
                                        interp.cost.as_ref().and_then(|pc| {
                                            pc.iter().next().map(|(cur, post_cost)| {
                                                let mut obj = serde_json::Map::new();
                                                obj.insert("kind".into(), json!("cost"));
                                                obj.insert(
                                                    "number".into(),
                                                    json!(post_cost.per_unit.to_string()),
                                                );
                                                obj.insert("currency".into(), json!(cur));
                                                obj.insert(
                                                    "date".into(),
                                                    json!(post_cost.date.to_string()),
                                                );
                                                if let Some(label) = &post_cost.label {
                                                    obj.insert(
                                                        "label".into(),
                                                        json!(label.to_string()),
                                                    );
                                                }
                                                Value::Object(obj)
                                            })
                                        });

                                    // Resolved price.
                                    let price =
                                        interp.price.as_ref().map(|pr| {
                                            json!({
                                                "number": pr.per_unit.to_string(),
                                                "currency": pr.currency,
                                            })
                                        });

                                    postings_json.push(json!({
                                        "account": raw_p.account().item().as_ref(),
                                        "units": units,
                                        "cost": cost,
                                        "price": price,
                                        "flag": flag,
                                        "meta": Value::Object(posting_meta),
                                    }));
                                }

                                (
                                    "transaction",
                                    json!({
                                        "flag": flag_to_str(txn.flag().item()),
                                        "payee": txn.payee().map(|p| p.item().to_string()),
                                        "narration": txn.narration().map(|n| n.item().to_string()),
                                        "tags": sorted_tags,
                                        "links": sorted_links,
                                        "postings": postings_json,
                                    }),
                                )
                            }

                            Err(e) => {
                                // On booking failure, include raw parse output and report error.
                                booking_errors.push(format!(
                                    "Booking error on {}: {:?}",
                                    date, e
                                ));

                                let mut raw_postings = Vec::new();
                                for sp in txn.postings() {
                                    let p = sp.item();
                                    let flag = p.flag().map(|f| flag_to_str(f.item()));
                                    let units =
                                        match (p.amount(), p.currency()) {
                                            (Some(num), Some(cur)) => Some(json!({
                                                "number": num.item().value().to_string(),
                                                "currency": cur.item().as_ref(),
                                            })),
                                            _ => None,
                                        };
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
                                            cost_obj.insert(
                                                "currency".into(),
                                                json!(cur.item().as_ref()),
                                            );
                                        }
                                        if let Some(d) = cs.date() {
                                            cost_obj.insert(
                                                "date".into(),
                                                json!(d.item().to_string()),
                                            );
                                        }
                                        if let Some(label) = cs.label() {
                                            cost_obj.insert(
                                                "label".into(),
                                                json!(label.item()),
                                            );
                                        }
                                        Value::Object(cost_obj)
                                    });
                                    let price = p.price_annotation().map(|pa| {
                                        let pa = pa.item();
                                        match pa {
                                            PriceSpec::CurrencyAmount(scoped, cur) => {
                                                let num = match scoped {
                                                    ScopedExprValue::PerUnit(ev) => {
                                                        ev.value().to_string()
                                                    }
                                                    ScopedExprValue::Total(ev) => {
                                                        ev.value().to_string()
                                                    }
                                                };
                                                json!({"number": num, "currency": cur.as_ref()})
                                            }
                                            PriceSpec::BareAmount(scoped) => {
                                                let num = match scoped {
                                                    ScopedExprValue::PerUnit(ev) => {
                                                        ev.value().to_string()
                                                    }
                                                    ScopedExprValue::Total(ev) => {
                                                        ev.value().to_string()
                                                    }
                                                };
                                                json!({"number": num})
                                            }
                                            PriceSpec::BareCurrency(cur) => {
                                                json!({"currency": cur.as_ref()})
                                            }
                                            PriceSpec::Unspecified => Value::Null,
                                        }
                                    });
                                    let mut p_meta_obj = serde_json::Map::new();
                                    for (key, value) in p.metadata().key_values() {
                                        p_meta_obj.insert(
                                            key.item().as_ref().to_string(),
                                            meta_value_to_json(value.item()),
                                        );
                                    }
                                    raw_postings.push(json!({
                                        "account": p.account().item().as_ref(),
                                        "units": units,
                                        "cost": cost,
                                        "price": price,
                                        "flag": flag,
                                        "meta": Value::Object(p_meta_obj),
                                    }));
                                }

                                (
                                    "transaction",
                                    json!({
                                        "flag": flag_to_str(txn.flag().item()),
                                        "payee": txn.payee().map(|p| p.item().to_string()),
                                        "narration": txn.narration().map(|n| n.item().to_string()),
                                        "tags": sorted_tags,
                                        "links": sorted_links,
                                        "postings": raw_postings,
                                    }),
                                )
                            }
                        }
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

                directives_json.push(json!({
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
                "directives": directives_json,
                "errors": booking_errors,
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

//! Parse helper for rustledger.
//!
//! Reads a beancount file with rustledger-loader and emits JSON to stdout
//! in the portable schema used by all beancompat adapters.
//!
//! Usage:
//!   rustledger-helper <path.beancount>
//!
//! Build: cd implementations/rustledger && cargo build --release

use rustledger_core::{Directive, DisplayContext, IncompleteAmount, MetaValue, PriceAnnotation};
use rustledger_loader::{Loader, LoadError, Options};
use serde_json::{json, Map, Value};
use std::env;
use std::path::PathBuf;
use std::process;

fn meta_value_to_json(mv: &MetaValue) -> Value {
    match mv {
        MetaValue::String(s) => json!(s),
        MetaValue::Account(s) => json!(s),
        MetaValue::Currency(s) => json!(s),
        MetaValue::Tag(s) => json!(s),
        MetaValue::Link(s) => json!(s),
        MetaValue::Date(d) => json!(d.to_string()),
        MetaValue::Number(n) => json!(n.to_string()),
        MetaValue::Bool(b) => json!(b),
        MetaValue::Amount(a) => json!({
            "number": a.number.to_string(),
            "currency": a.currency.as_str(),
        }),
        MetaValue::None => Value::Null,
    }
}

fn meta_to_json(meta: &rustledger_core::Metadata) -> Value {
    let mut m = Map::new();
    for (k, v) in meta {
        m.insert(k.clone(), meta_value_to_json(v));
    }
    Value::Object(m)
}

fn incomplete_amount_to_json(units: &IncompleteAmount) -> Value {
    match units {
        IncompleteAmount::Complete(a) => json!({
            "number": a.number.to_string(),
            "currency": a.currency.as_str(),
        }),
        IncompleteAmount::NumberOnly(n) => json!({
            "number": n.to_string(),
            "currency": Value::Null,
        }),
        IncompleteAmount::CurrencyOnly(c) => json!({
            "number": Value::Null,
            "currency": c.as_str(),
        }),
    }
}

fn price_to_json(price: &PriceAnnotation) -> Value {
    match price {
        PriceAnnotation::Unit(a) | PriceAnnotation::Total(a) => json!({
            "number": a.number.to_string(),
            "currency": a.currency.as_str(),
        }),
        PriceAnnotation::UnitIncomplete(u) | PriceAnnotation::TotalIncomplete(u) => {
            incomplete_amount_to_json(u)
        }
        PriceAnnotation::UnitEmpty | PriceAnnotation::TotalEmpty => Value::Null,
    }
}

fn serialize_postings(postings: &[rustledger_core::Posting]) -> Value {
    postings
        .iter()
        .map(|p| {
            let units = p.units.as_ref().map(incomplete_amount_to_json);
            let cost = p.cost.as_ref().map(|cs| {
                let mut obj = Map::new();
                obj.insert("kind".into(), json!("cost_spec"));
                if let Some(n) = cs.number_per {
                    obj.insert("number_per".into(), json!(n.to_string()));
                }
                if let Some(n) = cs.number_total {
                    obj.insert("number_total".into(), json!(n.to_string()));
                }
                if let Some(ref c) = cs.currency {
                    obj.insert("currency".into(), json!(c.as_str()));
                }
                if let Some(d) = cs.date {
                    obj.insert("date".into(), json!(d.to_string()));
                }
                if let Some(ref l) = cs.label {
                    obj.insert("label".into(), json!(l));
                }
                if cs.merge {
                    obj.insert("merge".into(), json!(true));
                }
                Value::Object(obj)
            });
            let price = p.price.as_ref().map(price_to_json);
            let flag = p.flag.map(|f| f.to_string());
            json!({
                "account": p.account.as_str(),
                "units": units,
                "cost": cost,
                "price": price,
                "flag": flag,
                "meta": meta_to_json(&p.meta),
            })
        })
        .collect()
}

fn serialize_directive(d: &Directive) -> Option<Value> {
    Some(match d {
        Directive::Transaction(txn) => {
            let mut tags: Vec<String> = txn.tags.iter().map(|t| t.to_string()).collect();
            let mut links: Vec<String> = txn.links.iter().map(|l| l.to_string()).collect();
            tags.sort();
            links.sort();
            json!({
                "type": "transaction",
                "date": txn.date.to_string(),
                "meta": meta_to_json(&txn.meta),
                "data": {
                    "flag": txn.flag.to_string(),
                    "payee": txn.payee.as_ref().map(|p| p.to_string()),
                    "narration": txn.narration.to_string(),
                    "tags": tags,
                    "links": links,
                    "postings": serialize_postings(&txn.postings),
                },
            })
        }
        Directive::Open(open) => {
            let currencies: Vec<String> =
                open.currencies.iter().map(|c| c.to_string()).collect();
            json!({
                "type": "open",
                "date": open.date.to_string(),
                "meta": meta_to_json(&open.meta),
                "data": {
                    "account": open.account.as_str(),
                    "currencies": currencies,
                    "booking": open.booking,
                },
            })
        }
        Directive::Close(close) => {
            json!({
                "type": "close",
                "date": close.date.to_string(),
                "meta": meta_to_json(&close.meta),
                "data": {
                    "account": close.account.as_str(),
                },
            })
        }
        Directive::Balance(bal) => {
            json!({
                "type": "balance",
                "date": bal.date.to_string(),
                "meta": meta_to_json(&bal.meta),
                "data": {
                    "account": bal.account.as_str(),
                    "amount": {
                        "number": bal.amount.number.to_string(),
                        "currency": bal.amount.currency.as_str(),
                    },
                    "tolerance": bal.tolerance.map(|t| t.to_string()),
                },
            })
        }
        Directive::Pad(pad) => {
            json!({
                "type": "pad",
                "date": pad.date.to_string(),
                "meta": meta_to_json(&pad.meta),
                "data": {
                    "account": pad.account.as_str(),
                    "source_account": pad.source_account.as_str(),
                },
            })
        }
        Directive::Price(p) => {
            json!({
                "type": "price",
                "date": p.date.to_string(),
                "meta": meta_to_json(&p.meta),
                "data": {
                    "currency": p.currency.as_str(),
                    "amount": {
                        "number": p.amount.number.to_string(),
                        "currency": p.amount.currency.as_str(),
                    },
                },
            })
        }
        Directive::Note(note) => {
            json!({
                "type": "note",
                "date": note.date.to_string(),
                "meta": meta_to_json(&note.meta),
                "data": {
                    "account": note.account.as_str(),
                    "comment": note.comment,
                },
            })
        }
        Directive::Event(ev) => {
            json!({
                "type": "event",
                "date": ev.date.to_string(),
                "meta": meta_to_json(&ev.meta),
                "data": {
                    "type": ev.event_type,
                    "description": ev.value,
                },
            })
        }
        Directive::Commodity(com) => {
            json!({
                "type": "commodity",
                "date": com.date.to_string(),
                "meta": meta_to_json(&com.meta),
                "data": {
                    "currency": com.currency.as_str(),
                },
            })
        }
        Directive::Document(doc) => {
            json!({
                "type": "document",
                "date": doc.date.to_string(),
                "meta": meta_to_json(&doc.meta),
                "data": {
                    "account": doc.account.as_str(),
                    "filename": doc.path,
                },
            })
        }
        Directive::Query(q) => {
            json!({
                "type": "query",
                "date": q.date.to_string(),
                "meta": meta_to_json(&q.meta),
                "data": {
                    "name": q.name,
                    "query_string": q.query,
                },
            })
        }
        Directive::Custom(c) => {
            let values: Vec<Value> = c.values.iter().map(meta_value_to_json).collect();
            json!({
                "type": "custom",
                "date": c.date.to_string(),
                "meta": meta_to_json(&c.meta),
                "data": {
                    "type_name": c.custom_type,
                    "values": values,
                },
            })
        }
    })
}

fn serialize_options(opts: &Options, _ctx: &DisplayContext) -> Map<String, Value> {
    let mut m = Map::new();

    if let Some(ref t) = opts.title {
        m.insert("title".into(), json!(t));
    }
    m.insert("name_assets".into(), json!(opts.name_assets));
    m.insert("name_liabilities".into(), json!(opts.name_liabilities));
    m.insert("name_equity".into(), json!(opts.name_equity));
    m.insert("name_income".into(), json!(opts.name_income));
    m.insert("name_expenses".into(), json!(opts.name_expenses));
    if let Some(ref r) = opts.account_rounding {
        m.insert("account_rounding".into(), json!(r));
    }
    m.insert(
        "account_previous_balances".into(),
        json!(opts.account_previous_balances),
    );
    m.insert(
        "account_previous_earnings".into(),
        json!(opts.account_previous_earnings),
    );
    m.insert(
        "account_previous_conversions".into(),
        json!(opts.account_previous_conversions),
    );
    m.insert(
        "account_current_earnings".into(),
        json!(opts.account_current_earnings),
    );
    if let Some(ref v) = opts.account_current_conversions {
        m.insert("account_current_conversions".into(), json!(v));
    }
    if let Some(ref v) = opts.account_unrealized_gains {
        m.insert("account_unrealized_gains".into(), json!(v));
    }
    if let Some(ref v) = opts.conversion_currency {
        m.insert("conversion_currency".into(), json!(v));
    }

    // inferred_tolerance_default: {currency: "0.005"}
    let itd: Map<String, Value> = opts
        .inferred_tolerance_default
        .iter()
        .map(|(k, v)| (k.clone(), json!(v.to_string())))
        .collect();
    m.insert("inferred_tolerance_default".into(), Value::Object(itd));

    m.insert(
        "inferred_tolerance_multiplier".into(),
        json!(opts.inferred_tolerance_multiplier.to_string()),
    );
    m.insert(
        "infer_tolerance_from_cost".into(),
        json!(opts.infer_tolerance_from_cost),
    );
    m.insert("booking_method".into(), json!(opts.booking_method));
    m.insert("render_commas".into(), json!(opts.render_commas));
    m.insert(
        "allow_pipe_separator".into(),
        json!(opts.allow_pipe_separator),
    );
    m.insert(
        "long_string_maxlines".into(),
        json!(opts.long_string_maxlines),
    );
    m.insert("documents".into(), json!(opts.documents));
    m.insert(
        "plugin_processing_mode".into(),
        json!(opts.plugin_processing_mode),
    );
    m.insert("operating_currency".into(), json!(opts.operating_currency));

    // display_precision: user-set precision per currency
    let dp: Map<String, Value> = opts
        .display_precision
        .iter()
        .map(|(k, v)| (k.clone(), json!(v)))
        .collect();
    m.insert("display_precision".into(), Value::Object(dp));

    m
}

fn load_errors_to_strings(errors: &[LoadError]) -> Vec<String> {
    errors
        .iter()
        .map(|e| match e {
            LoadError::ParseErrors { path, errors } => {
                let details: Vec<String> = errors.iter().map(|pe| pe.to_string()).collect();
                if details.is_empty() {
                    format!("parse errors in {}", path.display())
                } else {
                    format!(
                        "parse errors in {}: {}",
                        path.display(),
                        details.join("; ")
                    )
                }
            }
            other => other.to_string(),
        })
        .collect()
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: rustledger-helper <path.beancount>");
        process::exit(1);
    }

    let path = PathBuf::from(&args[1]);

    match Loader::new().load(&path) {
        Ok(result) => {
            let errors = load_errors_to_strings(&result.errors);

            let directives: Vec<Value> = result
                .directives
                .iter()
                .filter_map(|spanned| serialize_directive(&spanned.value))
                .collect();

            let options = serialize_options(&result.options, &result.display_context);

            let output = json!({
                "directives": directives,
                "errors": errors,
                "options": options,
            });
            println!("{}", output);
        }
        Err(e) => {
            let output = json!({
                "directives": [],
                "errors": [e.to_string()],
                "options": {},
            });
            println!("{}", output);
        }
    }
}

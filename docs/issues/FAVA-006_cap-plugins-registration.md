---
id: FAVA-006
title: "CAP_PLUGINS registration adapter method"
status: open
priority: medium
created: 2026-04-26
category: FAVA
tags: [capability, plugins]
---

# `CAP_PLUGINS` registration adapter method

**Status:** open
**Tier:** parse/check, affects Fava-compat (CAP_FAVA)
**Capability:** CAP_PLUGINS (constant exists; method does not)

## Problem

`CAP_PLUGINS` is declared in `implementations/adapter.py` and the reference adapter advertises it, but the `Implementation` protocol has no method that drives plugin registration into the loader pipeline. `tests/test_plugins.py` exercises the option-line `option "plugin" "..."` path implicitly via the loader, but there's no first-class adapter-level surface for "load this source with this plugin enabled."

This matters because alternative implementations may take plugins via a different path (constructor argument, registration call, configuration file) than v3's option-line. Without an adapter method, those implementations have no way to declare CAP_PLUGINS support to the suite.

## Context

- **beancount-side:** v3 plugins are registered via `option "plugin" "module.name"` lines in source, processed by `beancount.loader`. The plugin module is imported and its `__plugins__` callables are invoked during load.
- **beancompat-side:** Add a method like `parse_string_with_plugins(source, plugins: list[str]) -> ParseResult` (or extend `parse_string` with an optional `plugins` argument) to the `Implementation` protocol. Reference adapter implements by injecting option lines or by calling the loader with explicit plugin args. Add a fixture using a trivial in-tree plugin (e.g. one that adds a metadata key) so behavior is observable without external dependencies.

## Acceptance criteria

- [ ] `Implementation` protocol grows a plugin-registration method.
- [ ] Reference adapter implements the method.
- [ ] `tests/test_plugins.py` has a test that uses the new method (separate from the option-line path).
- [ ] At least one fixture exercises a trivial plugin and asserts its observable effect.
- [ ] Adapters without `CAP_PLUGINS` skip cleanly.

## References

- beancount: `beancount.loader` plugin invocation path
- beancompat: `implementations/adapter.py`, `implementations/beancount/__init__.py`, `tests/test_plugins.py`
- Memory: `.claude/memory/fava_contract_surface.md`

# `loader._load(...)` private-API parity

**Status:** wontfix
**Tier:** Fava-compat (CAP_FAVA), informational

## Problem

Fava calls `beancount.loader._load(...)` — a private function — to bypass the loader's caching layer and force a fresh parse on each request. This is a Fava-side wart: the public `load_string` / `load_file` API is documented; `_load` is not, and pinning beancompat to a leading-underscore name would commit alternative implementations to reproducing an explicitly-private surface.

This is captured here so the gap is documented and future contributors don't reopen it as actionable work. The right place for the fix is Fava: either expose the cache-bypass as a public API in beancount or stop relying on the private one.

## Context

- **Fava-side:** `src/fava/beans/load.py` calls `_load` directly (one of the small set of beancount internals Fava intentionally reaches into).
- **beancompat-side:** No code change planned. If Fava ever switches to a public surface, that becomes a normal CAP_FAVA item under whichever new method name beancount provides.

## Resolution

This issue exists for visibility only. It will not produce code, fixtures, or tests in beancompat. Close as wontfix if a process audit ever asks whether it's stalled.

## References

- Fava: `src/fava/beans/load.py`
- beancount: `beancount.loader._load` (private)
- Memory: `.claude/memory/fava_contract_surface.md`

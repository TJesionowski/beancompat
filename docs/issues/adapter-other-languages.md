# Adapters: Dart / Zig / Clojure efforts

**Status:** open (tracking)
**Tier:** TBD per project

## Problem

The mailing list thread and surrounding community discussion mention beancount work in Dart, Zig, and Clojure, but none are concrete enough to have a row in `docs/references/README.md` or a directory under `implementations/`. This issue exists so the interest is captured in one place rather than dropped. As any of these mature into something invokable, split it out into its own `adapter-<name>.md` and remove its bullet from this file.

This is *not* a commitment to wrap every implementation that ever gets mentioned — only the ones that reach "actually parses beancount source" status are worth an adapter. The bar is the same as for other adapters: a CLI or library surface beancompat can drive black-box, plus a maintainer who's responding to issues.

## Context

- **Adapter pattern:** Subprocess-based, JSON-out — same as `implementations/beancountparserlima/` (Rust binary), `implementations/beancountparser/` (Python lark-based via `-c`), or `implementations/beancountv2/` (separate venv). Pick whichever pattern matches the implementation language.
- **Adapter skill:** `/update-implementations`.

## Tracking

Update this section as projects firm up:

- **Dart:** Project URL TBD. Mentioned in the mailing list thread.
- **Zig:** Project URL TBD. Mentioned in the mailing list thread.
- **Clojure:** Project URL TBD. Mentioned in the mailing list thread.

When any project becomes concrete:

1. Add it to `docs/references/README.md` "Implementations in scope" table with language, author, and notes.
2. Create a stub directory under `implementations/<name>/`.
3. Split a dedicated `docs/issues/adapter-<name>.md` off this file.
4. Remove the project's bullet from the Tracking list above.

## Acceptance criteria

This issue closes when either:

- All three projects have been split into their own adapter issues, OR
- The community signals that the projects have stalled and the bullets can be removed.

## References

- Mailing list: https://groups.google.com/g/beancount/c/EOoD755XNP0
- beancompat: `docs/references/README.md`, `implementations/`
- Skill: `/update-implementations`

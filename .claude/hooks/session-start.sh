#!/bin/bash
# SessionStart hook: bootstrap beancompat's test environment.
#
# Minimal by default (~11s cold, ~0s warm): Python venvs for the beancount v3
# reference adapter, the beancount-v2 adapter, and the beancount-parser adapter.
#
# Set BEANCOMPAT_BUILD_LIMA=1 to additionally build the Rust lima helper
# binary (~4min cold, required for the beancount-parser-lima adapter).
set -euo pipefail

# Only run in the remote (Claude Code on the web) environment. Locally,
# developers use the Nix flake devshell.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
    exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

PYTHON="$(command -v python3.12 || command -v python3)"
MAIN_VENV="$CLAUDE_PROJECT_DIR/.venv"
V2_VENV="$CLAUDE_PROJECT_DIR/.venv-beancount-v2"

if [ ! -x "$MAIN_VENV/bin/python" ]; then
    "$PYTHON" -m venv "$MAIN_VENV"
    "$MAIN_VENV/bin/pip" install -q --upgrade pip
    "$MAIN_VENV/bin/pip" install -q \
        beancount \
        beanquery \
        beancount-parser \
        pytest \
        hypothesis
fi

if [ ! -x "$V2_VENV/bin/python" ]; then
    "$PYTHON" -m venv "$V2_VENV"
    "$V2_VENV/bin/pip" install -q --upgrade pip
    "$V2_VENV/bin/pip" install -q beancount==2.3.6 beanquery
fi

if [ "${BEANCOMPAT_BUILD_LIMA:-0}" = "1" ]; then
    LIMA_DIR="$CLAUDE_PROJECT_DIR/implementations/beancountparserlima"
    if [ ! -x "$LIMA_DIR/target/release/lima-parse-helper" ]; then
        if ! command -v cargo >/dev/null 2>&1; then
            echo "session-start.sh: cargo not found; skipping lima build" >&2
        else
            (cd "$LIMA_DIR" && cargo build --release --quiet)
        fi
    fi
fi

# Persist PATH and BEANCOUNT_V2_VENV for the session so pytest and the v2
# adapter resolve the right interpreters without extra wrapper scripts.
{
    echo "export PATH=\"$MAIN_VENV/bin:\$PATH\""
    echo "export BEANCOUNT_V2_VENV=\"$V2_VENV\""
} >> "$CLAUDE_ENV_FILE"

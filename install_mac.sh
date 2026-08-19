#!/usr/bin/env bash
#
# One-command install for macOS.
#
#   ./install_mac.sh                # set up, build the .app, install it
#   ./install_mac.sh --run          # set up and run from source (no build)
#   ./install_mac.sh --test-keyboard# set up and go straight to the hardware test
#
# Everything is local: a virtualenv in .venv, the app in /Applications, and
# game data under ~/Library/Application Support/TypeScholar.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MODE="install"
for arg in "$@"; do
    case "$arg" in
        --run)           MODE="run" ;;
        --test-keyboard) MODE="keyboard" ;;
        -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; exit 1 ;;
    esac
done

info() { printf '\033[36m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[33m[!]\033[0m %s\n' "$1"; }
die()  { printf '\033[31m[x]\033[0m %s\n' "$1" >&2; exit 1; }

printf '\n\033[1m  Type Scholar — setup\033[0m\n\n'

[[ "$(uname -s)" == "Darwin" ]] || die "This installer is for macOS. On Linux/Windows use: pip install -r requirements.txt"

info "Mac: $(uname -m), macOS $(sw_vers -productVersion 2>/dev/null || echo '?')"

# -- python ----------------------------------------------------------------

PYTHON=""
for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
            PYTHON="$candidate"; break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    warn "No Python 3.10+ found."
    echo "    Install it with either:"
    echo "      brew install python@3.12"
    echo "      or download from https://www.python.org/downloads/macos/"
    exit 1
fi
info "Using $($PYTHON --version) at $(command -v "$PYTHON")"

# -- virtualenv ------------------------------------------------------------

if [[ ! -d "$ROOT/.venv" ]]; then
    info "Creating virtualenv (.venv)"
    "$PYTHON" -m venv "$ROOT/.venv"
fi
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"

info "Installing dependencies (this takes a minute the first time)"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt || die "Dependency install failed."

if python -c 'import hid' 2>/dev/null; then
    info "hidapi ready — Logitech per-key lighting can be attempted"
else
    warn "hidapi unavailable. The game still runs with on-screen highlighting."
    warn "For keyboard lighting: brew install hidapi && pip install hidapi"
fi

info "Checking the game logic"
python -m pytest tests/ -q >/dev/null 2>&1 \
    && info "All tests pass" \
    || warn "Some tests failed — the game will still run; see: python -m pytest tests/ -q"

# -- modes -----------------------------------------------------------------

case "$MODE" in
    keyboard)
        printf '\n'
        info "Starting the hardware test utility"
        exec python keyboard_test.py
        ;;
    run)
        printf '\n'
        info "Starting Type Scholar from source"
        exec python -m app.main
        ;;
esac

# -- build + install -------------------------------------------------------

info "Building the .app bundle"
bash packaging/build_mac.sh || die "Build failed."

APP="dist/Type Scholar.app"
[[ -d "$APP" ]] || die "Build finished but $APP is missing."

TARGET="/Applications/Type Scholar.app"
if [[ -w /Applications ]]; then
    info "Installing to /Applications"
    rm -rf "$TARGET"
    cp -R "$APP" "$TARGET"
    INSTALLED="$TARGET"
else
    mkdir -p "$HOME/Applications"
    TARGET="$HOME/Applications/Type Scholar.app"
    info "Installing to ~/Applications (no write access to /Applications)"
    rm -rf "$TARGET"
    cp -R "$APP" "$TARGET"
    INSTALLED="$TARGET"
fi

cat <<EOF

$(printf '\033[32m  Installed.\033[0m')

  App        : $INSTALLED
  Launch     : open "$INSTALLED"
  Keyboard   : ./install_mac.sh --test-keyboard
  Run source : ./install_mac.sh --run

  First launch may need a right-click > Open (the build is ad-hoc signed).

  Plug the PRO X 60 in by USB and run the keyboard test first — it will tell
  you whether per-key lighting works before you sit down with your child.

EOF

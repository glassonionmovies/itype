#!/usr/bin/env bash
#
# Build "Type Scholar.app" (and optionally a .dmg) on macOS.
#
#   ./packaging/build_mac.sh          # build the .app
#   ./packaging/build_mac.sh --dmg    # build the .app and a .dmg
#   ./packaging/build_mac.sh --clean  # remove build artefacts first
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

APP_NAME="Type Scholar"
DIST="$ROOT/dist"
APP_PATH="$DIST/$APP_NAME.app"

MAKE_DMG=0
CLEAN=0
for arg in "$@"; do
    case "$arg" in
        --dmg)   MAKE_DMG=1 ;;
        --clean) CLEAN=1 ;;
        -h|--help)
            sed -n '2,10p' "$0"; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; exit 1 ;;
    esac
done

info() { printf '\033[36m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[33m[!]\033[0m %s\n' "$1"; }
die()  { printf '\033[31m[x]\033[0m %s\n' "$1" >&2; exit 1; }

if [[ "$(uname -s)" != "Darwin" ]]; then
    die "This builds a macOS .app and must run on macOS (found $(uname -s))."
fi

ARCH="$(uname -m)"
info "Architecture: $ARCH"
[[ "$ARCH" == "arm64" ]] && info "Apple Silicon: the bundle will be arm64-native."

# -- python ----------------------------------------------------------------

PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null || die "python3 not found."

PY_VERSION="$($PYTHON -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
info "Python $PY_VERSION ($PYTHON)"
$PYTHON - <<'EOF' || exit 1
import sys
if sys.version_info < (3, 10):
    sys.exit("Python 3.10 or newer is required.")
EOF

# Building inside a venv keeps the bundle free of unrelated site-packages.
VENV="$ROOT/.venv-build"
if [[ ! -d "$VENV" ]]; then
    info "Creating build virtualenv at .venv-build"
    "$PYTHON" -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

info "Installing dependencies"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
python -m pip install --quiet pyinstaller pytest

# -- clean -----------------------------------------------------------------

if [[ $CLEAN -eq 1 ]]; then
    info "Cleaning build/ and dist/"
    rm -rf "$ROOT/build" "$DIST"
fi

# -- sanity check ----------------------------------------------------------

info "Running tests before packaging"
python -m pytest tests/ -q || die "Tests failed; not packaging a broken build."

# -- icon ------------------------------------------------------------------

if [[ ! -f "$ROOT/packaging/icon.icns" ]]; then
    info "Generating app icon"
    python "$ROOT/packaging/make_icon.py" || warn "Icon generation failed; building without one."
fi

# -- build -----------------------------------------------------------------

info "Building $APP_NAME.app"
pyinstaller packaging/TypeScholar.spec --noconfirm --distpath "$DIST" \
    --workpath "$ROOT/build"

[[ -d "$APP_PATH" ]] || die "Build finished but $APP_PATH is missing."

# Ad-hoc signature. Without this, Gatekeeper on Apple Silicon refuses to launch
# an unsigned bundle at all; with it the app runs locally (users may still need
# to right-click > Open the first time).
info "Ad-hoc code signing"
codesign --force --deep --sign - "$APP_PATH" 2>/dev/null \
    || warn "codesign failed; you may need to right-click > Open on first launch."

SIZE="$(du -sh "$APP_PATH" | cut -f1)"
info "Built $APP_PATH ($SIZE)"

# -- smoke test ------------------------------------------------------------

info "Verifying the bundle launches"
if "$APP_PATH/Contents/MacOS/Type Scholar" --version >/dev/null 2>&1; then
    info "Bundle responds to --version"
else
    warn "Could not run --version from the bundle; test it by hand."
fi

# -- dmg -------------------------------------------------------------------

if [[ $MAKE_DMG -eq 1 ]]; then
    info "Building TypeScholar.dmg"
    DMG_DIR="$(mktemp -d)"
    cp -R "$APP_PATH" "$DMG_DIR/"
    ln -s /Applications "$DMG_DIR/Applications"
    rm -f "$DIST/TypeScholar.dmg"
    hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_DIR" -ov -format UDZO \
        "$DIST/TypeScholar.dmg" >/dev/null
    rm -rf "$DMG_DIR"
    info "Built $DIST/TypeScholar.dmg"
fi

cat <<EOF

$(printf '\033[32mDone.\033[0m')

  App : $APP_PATH
  Run : open "$APP_PATH"
  Install: drag it into /Applications

  Before playing, check the keyboard with:
      python3 keyboard_test.py

EOF

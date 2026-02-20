#!/usr/bin/env bash
# hyprquotes installer
# Usage: ./install.sh [--prefix /usr/local] [--user]

set -euo pipefail

# ── Defaults ────────────────────────────────────────────────────────────────
PREFIX="/usr/local"
USER_INSTALL=false
INSTALL_DIR=""
QUOTES_DEST=""

# ── Colours ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[hyprquotes]${NC} $*"; }
warn()    { echo -e "${YELLOW}[hyprquotes]${NC} $*"; }
error()   { echo -e "${RED}[hyprquotes] ERROR:${NC} $*" >&2; exit 1; }

# ── Argument parsing ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix) PREFIX="$2"; shift 2 ;;
    --user)   USER_INSTALL=true; shift ;;
    -h|--help)
      echo "Usage: $0 [--prefix DIR] [--user]"
      echo "  --prefix DIR   Install to DIR/bin and DIR/share (default: /usr/local)"
      echo "  --user         Install to ~/.local (overrides --prefix)"
      exit 0 ;;
    *) error "Unknown argument: $1" ;;
  esac
done

if $USER_INSTALL; then
  PREFIX="$HOME/.local"
fi

INSTALL_DIR="$PREFIX/share/hyprquotes"
BIN_DIR="$PREFIX/bin"
QUOTES_DEST="$HOME/.config/hyprquotes"

# ── Dependency check ─────────────────────────────────────────────────────────
info "Checking dependencies..."

check_python() {
  if ! command -v python3 &>/dev/null; then
    error "python3 not found. Install python3 (>= 3.8) and try again."
  fi
  local ver
  ver=$(python3 -c 'import sys; print(sys.version_info >= (3,8))')
  [[ "$ver" == "True" ]] || error "Python >= 3.8 required."
}

check_gi() {
  if ! python3 -c "import gi" &>/dev/null; then
    error "PyGObject (gi) not found.\n  Arch:   sudo pacman -S python-gobject\n  Debian: sudo apt install python3-gi"
  fi
}

check_gtk() {
  if ! python3 -c "import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk" &>/dev/null; then
    error "GTK3 GI bindings not found.\n  Arch:   sudo pacman -S gtk3\n  Debian: sudo apt install gir1.2-gtk-3.0"
  fi
}

check_wl_copy() {
  if ! command -v wl-copy &>/dev/null; then
    warn "wl-copy not found — clipboard support will be disabled."
    warn "  Arch:   sudo pacman -S wl-clipboard"
    warn "  Debian: sudo apt install wl-clipboard"
  fi
}

check_hyprctl() {
  if ! command -v hyprctl &>/dev/null; then
    warn "hyprctl not found — workspace detection requires Hyprland to be running."
  fi
}

check_python
check_gi
check_gtk
check_wl_copy
check_hyprctl

# ── Install ───────────────────────────────────────────────────────────────────
info "Installing to $INSTALL_DIR ..."

if $USER_INSTALL; then
  mkdir -p "$INSTALL_DIR" "$BIN_DIR"
else
  sudo mkdir -p "$INSTALL_DIR" "$BIN_DIR"
fi

# Copy application files
if $USER_INSTALL; then
  cp hyprquotes.py "$INSTALL_DIR/hyprquotes.py"
  chmod 644 "$INSTALL_DIR/hyprquotes.py"
else
  sudo cp hyprquotes.py "$INSTALL_DIR/hyprquotes.py"
  sudo chmod 644 "$INSTALL_DIR/hyprquotes.py"
fi

# Copy default quotes file (only if user doesn't already have one)
mkdir -p "$QUOTES_DEST"
if [[ ! -f "$QUOTES_DEST/programming-quotes.json" ]]; then
  cp assets/programming-quotes.json "$QUOTES_DEST/programming-quotes.json"
  info "Installed default quotes to $QUOTES_DEST/programming-quotes.json"
else
  warn "Existing quotes file found at $QUOTES_DEST/programming-quotes.json — not overwriting."
fi

# Create launcher wrapper in bin/
LAUNCHER="$BIN_DIR/hyprquotes"
LAUNCHER_CONTENT="#!/usr/bin/env bash
exec python3 $INSTALL_DIR/hyprquotes.py \"\$@\""

if $USER_INSTALL; then
  echo "$LAUNCHER_CONTENT" > "$LAUNCHER"
  chmod +x "$LAUNCHER"
else
  echo "$LAUNCHER_CONTENT" | sudo tee "$LAUNCHER" > /dev/null
  sudo chmod +x "$LAUNCHER"
fi

info "Launcher installed at $LAUNCHER"

# ── Autostart hint ────────────────────────────────────────────────────────────
HYPR_CONF="$HOME/.config/hypr/hyprland.conf"
info "Done! To autostart hyprquotes with Hyprland, add this to $HYPR_CONF:"
echo ""
echo "    exec-once = hyprquotes"
echo ""
info "Run 'hyprquotes' to start manually."

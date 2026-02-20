#!/usr/bin/env bash
# hyprquotes uninstaller

set -euo pipefail

PREFIX="/usr/local"
USER_INSTALL=false

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[hyprquotes]${NC} $*"; }
warn() { echo -e "${YELLOW}[hyprquotes]${NC} $*"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix) PREFIX="$2"; shift 2 ;;
    --user)   USER_INSTALL=true; shift ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

$USER_INSTALL && PREFIX="$HOME/.local"

INSTALL_DIR="$PREFIX/share/hyprquotes"
BIN_DIR="$PREFIX/bin"

if $USER_INSTALL; then
  rm -rf "$INSTALL_DIR"
  rm -f  "$BIN_DIR/hyprquotes"
else
  sudo rm -rf "$INSTALL_DIR"
  sudo rm -f  "$BIN_DIR/hyprquotes"
fi

info "hyprquotes removed."
warn "Your quotes file at ~/.config/hyprquotes/ was NOT removed."
warn "Delete it manually if you no longer need it."

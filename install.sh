#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fastfetch-designer"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
SRC_DIR="$(dirname "$0")/src"
DATA_DIR="$(dirname "$0")/data"

mkdir -p "$APP_DIR/src" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
cp -f "$SRC_DIR/fastfetch_designer.py" "$APP_DIR/src/fastfetch_designer.py"
cp -f "$DATA_DIR/fastfetch-designer.svg" "$ICON_DIR/fastfetch-designer.svg"
chmod +x "$APP_DIR/src/fastfetch_designer.py"

# The source in the repository is the source that gets installed.
# No install-time source patching is required.
ln -sf "$APP_DIR/src/fastfetch_designer.py" "$BIN_DIR/fastfetch-designer"

cat > "$DESKTOP_DIR/fastfetch-designer.desktop" <<EOF
[Desktop Entry]
Name=Fastfetch Designer
Comment=Lightweight graphical editor for Fastfetch
Exec=$BIN_DIR/fastfetch-designer
Icon=$ICON_DIR/fastfetch-designer.svg
Terminal=false
Type=Application
Categories=Utility;System;
Keywords=fastfetch;system;terminal;customization;
StartupNotify=true
EOF

rm -f "$DESKTOP_DIR/fasfetch-designer.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

echo
echo "Fastfetch Designer installed successfully."
echo "Command: $BIN_DIR/fastfetch-designer"
echo "Launcher: Fastfetch Designer (with application icon)"
if ! command -v fastfetch >/dev/null 2>&1; then
  echo "Warning: fastfetch is not installed or not in PATH."
fi

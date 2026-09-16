#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fastfetch-designer"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

mkdir -p "$APP_DIR/src" "$BIN_DIR" "$DESKTOP_DIR"
cp -f "$(dirname "$0")/src/fastfetch_designer.py" "$APP_DIR/src/fastfetch_designer.py"
chmod +x "$APP_DIR/src/fastfetch_designer.py"
ln -sf "$APP_DIR/src/fastfetch_designer.py" "$BIN_DIR/fastfetch-designer"

cat > "$DESKTOP_DIR/fastfetch-designer.desktop" <<EOF
[Desktop Entry]
Name=Fastfetch Designer
Comment=Lightweight graphical editor for Fastfetch
Exec=$BIN_DIR/fastfetch-designer
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=Utility;System;
Keywords=fastfetch;system;terminal;customization;
StartupNotify=true
EOF

# Update the desktop database when the command is available.
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

echo
echo "Fastfetch Designer installed successfully."
echo "Command: $BIN_DIR/fastfetch-designer"
echo "Launcher: Fastfetch Designer (application menu)"
if ! command -v fastfetch >/dev/null 2>&1; then
  echo "Warning: fastfetch is not installed or not in PATH."
fi

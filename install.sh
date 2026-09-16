#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fastfetch-designer"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"

command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required." >&2; exit 1; }
python3 -c 'import gi; gi.require_version("Gtk", "4.0"); from gi.repository import Gtk' >/dev/null 2>&1 || {
  echo "Error: GTK4 PyGObject is required." >&2
  echo "Install it with: sudo pacman -S --needed gtk4 python python-gobject" >&2
  exit 1
}
command -v fastfetch >/dev/null 2>&1 || {
  echo "Error: fastfetch is required." >&2
  echo "Install it with: sudo pacman -S --needed fastfetch" >&2
  exit 1
}

mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"

install -m 755 "$PROJECT_DIR/src/fastfetch_designer.py" "$APP_DIR/fastfetch_designer.py"
install -m 644 "$PROJECT_DIR/data/fastfetch-designer.svg" "$ICON_DIR/fastfetch-designer.svg"

cat > "$BIN_DIR/fastfetch-designer" <<EOF
#!/usr/bin/env bash
exec python3 "$APP_DIR/fastfetch_designer.py" "\$@"
EOF
chmod 755 "$BIN_DIR/fastfetch-designer"

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

# Validate the installed Python source before reporting success.
python3 -m py_compile "$APP_DIR/fastfetch_designer.py"

printf '\nFastfetch Designer installed successfully.\n'
printf 'Command: %s\n' "$BIN_DIR/fastfetch-designer"
printf 'Launcher: Fastfetch Designer (with application icon)\n'
printf 'Config detection: automatic\n'

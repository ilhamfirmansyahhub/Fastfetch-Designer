#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fastfetch-designer"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"

mkdir -p "$APP_DIR/src" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
cp -f "$(dirname "$0")/src/fastfetch_designer.py" "$APP_DIR/src/fastfetch_designer.py"
cp -f "$(dirname "$0")/data/fastfetch-designer.svg" "$ICON_DIR/fastfetch-designer.svg"
chmod +x "$APP_DIR/src/fastfetch_designer.py"

# The font selector was intentionally removed from the installed UI.
# Fastfetch does not control the terminal emulator's actual font.
python3 - "$APP_DIR/src/fastfetch_designer.py" <<'PY'
from pathlib import Path
import re
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

# Remove the Preview font controls from Appearance.
s = re.sub(
    r"\n        font = Gtk\.FontDialogButton\(\).*?card\.append\(hint\)\n",
    "\n",
    s,
    flags=re.S,
)
s = re.sub(
    r"\n        self\.font_button = Gtk\.FontDialogButton\(\).*?card\.append\(hint\)\n",
    "\n",
    s,
    flags=re.S,
)

# Remove preview-only font application.
s = s.replace(" text.add_css_class('preview-font');", "")
s = s.replace(" text.add_css_class('terminal-text'); text.add_css_class('preview-font')", " text.add_css_class('terminal-text')")
s = s.replace(" self.preview_font_css(text);", "")

s = re.sub(
    r"\n    def preview_font_css\(self, widget\):.*?(?=\n    def builtin_logo\(self, source\):)",
    "",
    s,
    flags=re.S,
)

p.write_text(s, encoding="utf-8")
PY

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

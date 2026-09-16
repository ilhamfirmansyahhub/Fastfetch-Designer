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

python3 - "$APP_DIR/src/fastfetch_designer.py" <<'PY'
from pathlib import Path
import re
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

# Project/application name.
s = s.replace("APP_NAME = 'Fastfetch Designer'", "APP_NAME = 'Fasfetch Designer'")
s = s.replace('>Fastfetch Designer</span>', '>Fasfetch Designer</span>')
s = s.replace("message='Fastfetch Designer'", "message='Fasfetch Designer'")

# Remove the preview-only font selector from older source revisions.
s = re.sub(
    r"\n        font = Gtk\.FontDialogButton\(\).*?card\.append\(hint\)\n",
    "\n", s, flags=re.S,
)
s = re.sub(
    r"\n        self\.font_button = Gtk\.FontDialogButton\(\).*?card\.append\(hint\)\n",
    "\n", s, flags=re.S,
)
s = s.replace("        text.add_css_class('terminal-text'); text.add_css_class('preview-font')\n", "        text.add_css_class('terminal-text')\n")
s = s.replace("        self.preview_font_css(text)\n", "")
s = re.sub(
    r"\n    def preview_font_css\(self, widget\):.*?(?=\n    def builtin_logo\(self, source\):)",
    "\n", s, flags=re.S,
)

# High-contrast default colors inspired by the clean, readable reference layout.
s = s.replace(
    "'Default': {'keys': '#D8DEE9', 'title': '#8FBCBB', 'output': '#D8DEE9', 'separator': '#81A1C1'},",
    "'Default': {'keys': '#E6E6E6', 'title': '#F0F0F0', 'output': '#D8DEE9', 'separator': '#9AA6AC'},",
)
s = s.replace(
    "[('keys','Keys','#D8DEE9'), ('title','Title','#8FBCBB'), ('output','Output','#D8DEE9'), ('separator','Separator','#81A1C1')]",
    "[('keys','Keys','#E6E6E6'), ('title','Title','#F0F0F0'), ('output','Output','#D8DEE9'), ('separator','Separator','#9AA6AC')]",
)

# Explicit foregrounds stop a dark desktop GTK theme from making labels almost black.
s = s.replace(
    "        .terminal-text { color: #D8DEE9; }\n",
    "        .terminal-text { color: #D8DEE9; }\n"
    "        .shell label, .sidebar label, .preview-shell label { color: #D8DEE9; }\n"
    "        .sidebar .muted, .preview-shell .muted { color: #8E9EA4; }\n"
    "        entry { background: #202A2D; color: #D8DEE9; caret-color: #D8DEE9; }\n"
    "        combobox { color: #D8DEE9; }\n",
)

# Replace the fixed ~/.config loader with Fastfetch's own current search order.
start = s.find('def load_config():\n')
if start != -1:
    end = s.find('\n\nclass FastfetchDesigner', start)
    if end != -1:
        replacement = '''def discover_fastfetch_config():\n    """Find the first existing config in Fastfetch's own search order."""\n    try:\n        result = subprocess.run(\n            ['fastfetch', '--list-config-paths'],\n            capture_output=True, text=True, timeout=3, check=False,\n        )\n        for raw in result.stdout.splitlines():\n            line = raw.strip()\n            if not line or line.startswith(('#', '//')):\n                continue\n            if ' -> ' in line:\n                line = line.split(' -> ', 1)[0].strip()\n            path = Path(os.path.expandvars(os.path.expanduser(line)))\n            if path.is_file() and path.suffix in {'.jsonc', '.json', '.conf'}:\n                return path\n    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):\n        pass\n    return Path.home() / '.config' / 'fastfetch' / 'config.jsonc'\n\n\ndef load_config():\n    global CONFIG_PATH\n    CONFIG_PATH = discover_fastfetch_config()\n    if not CONFIG_PATH.exists():\n        return {\n            '$schema': 'https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json',\n            'logo': {'type': 'auto', 'source': 'auto'},\n            'display': {'color': {'keys': '#E6E6E6', 'title': '#F0F0F0', 'output': '#D8DEE9', 'separator': '#9AA6AC'}},\n            'modules': [name for _, name in MODULES],\n        }\n    try:\n        return json.loads(strip_jsonc(CONFIG_PATH.read_text(encoding='utf-8')))\n    except Exception as e:\n        raise RuntimeError(f'Could not parse {CONFIG_PATH}: {e}')\n'''
        s = s[:start] + replacement + s[end:]

# Refresh now reloads the active config instead of only re-rendering stale UI state.
if 'def reload_and_refresh(self, *_):' not in s:
    insert_at = s.find('    def choose_logo(self, *_):')
    if insert_at != -1:
        method = '''    def reload_and_refresh(self, *_):\n        try:\n            self.config = load_config()\n            self.populate_from_config()\n            self.refresh_preview()\n        except Exception as e:\n            self.show_error(str(e))\n\n'''
        s = s[:insert_at] + method + s[insert_at:]

s = s.replace("refresh.connect('clicked', lambda *_: self.refresh_preview())", "refresh.connect('clicked', self.reload_and_refresh)")
p.write_text(s, encoding='utf-8')
PY

ln -sf "$APP_DIR/src/fastfetch_designer.py" "$BIN_DIR/fastfetch-designer"

cat > "$DESKTOP_DIR/fasfetch-designer.desktop" <<EOF
[Desktop Entry]
Name=Fasfetch Designer
Comment=Lightweight graphical editor for Fastfetch
Exec=$BIN_DIR/fastfetch-designer
Icon=$ICON_DIR/fastfetch-designer.svg
Terminal=false
Type=Application
Categories=Utility;System;
Keywords=fastfetch;fasfetch;system;terminal;customization;
StartupNotify=true
EOF

rm -f "$DESKTOP_DIR/fastfetch-designer.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

echo
echo "Fasfetch Designer installed successfully."
echo "Command: $BIN_DIR/fastfetch-designer"
echo "Launcher: Fasfetch Designer (with application icon)"
if ! command -v fastfetch >/dev/null 2>&1; then
  echo "Warning: fastfetch is not installed or not in PATH."
fi

#!/usr/bin/env python3
import copy
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Gio, GLib

APP_ID = "io.github.ilhamfirmansyahhub.FastfetchDesigner"
APP_NAME = "Fastfetch Designer"
DEFAULT_CONFIG = Path.home() / ".config" / "fastfetch" / "config.jsonc"
LOGO_DIR = Path.home() / ".config" / "fastfetch" / "logos"
ICON_NAME = "fastfetch-designer"

MODULES = [
    ("OS", "os"),
    ("Kernel", "kernel"),
    ("Uptime", "uptime"),
    ("Packages", "packages"),
    ("Shell", "shell"),
    ("Display", "display"),
    ("DE", "de"),
    ("WM", "wm"),
    ("Theme", "theme"),
    ("Icons", "icons"),
    ("Terminal", "terminal"),
    ("CPU", "cpu"),
    ("GPU", "gpu"),
    ("Memory", "memory"),
    ("Disk", "disk"),
]

PRESETS = {
    "Default": {
        "keys": "#E6E6E6",
        "title": "#F0F0F0",
        "output": "#D8DEE9",
        "separator": "#9AA6AC",
    },
    "Gruvbox": {
        "keys": "#EBDBB2",
        "title": "#D79921",
        "output": "#FBF1C7",
        "separator": "#B8BB26",
    },
    "Catppuccin": {
        "keys": "#CDD6F4",
        "title": "#89B4FA",
        "output": "#CDD6F4",
        "separator": "#A6E3A1",
    },
    "Nord": {
        "keys": "#D8DEE9",
        "title": "#88C0D0",
        "output": "#E5E9F0",
        "separator": "#81A1C1",
    },
    "Monochrome": {
        "keys": "#D0D0D0",
        "title": "#FFFFFF",
        "output": "#B8B8B8",
        "separator": "#808080",
    },
}


def strip_jsonc(text: str) -> str:
    out = []
    i = 0
    in_string = False
    escape = False
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ""
        if in_string:
            out.append(c)
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
            out.append(c)
        elif c == "/" and n == "/":
            i += 2
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue
        elif c == "/" and n == "*":
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        else:
            out.append(c)
        i += 1
    return re.sub(r",\s*([}\]])", r"\1", "".join(out))


def discover_config() -> Path:
    candidates = []

    env = os.environ.get("FASTFETCH_CONFIG") or os.environ.get("FASTFETCH_CONFIG_PATH")
    if env:
        candidates.append(Path(os.path.expandvars(os.path.expanduser(env))))

    try:
        result = subprocess.run(
            ["fastfetch", "--list-config-paths"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        for raw in result.stdout.splitlines():
            line = raw.strip()
            if not line or line.startswith(("#", "//")):
                continue
            # Some versions annotate paths with an arrow or status text.
            if " -> " in line:
                line = line.split(" -> ", 1)[0].strip()
            line = line.strip('"')
            p = Path(os.path.expandvars(os.path.expanduser(line)))
            if p.is_file():
                candidates.append(p)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        pass

    candidates.extend([
        DEFAULT_CONFIG,
        Path.home() / ".config" / "fastfetch" / "config.json",
    ])

    seen = set()
    for path in candidates:
        try:
            path = path.resolve()
        except OSError:
            pass
        if str(path) in seen:
            continue
        seen.add(str(path))
        if path.is_file():
            return path
    return DEFAULT_CONFIG


def load_config(path: Path):
    if not path.exists():
        return {
            "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
            "logo": {"type": "builtin", "source": "auto"},
            "display": {
                "color": copy.deepcopy(PRESETS["Default"]),
                "brightColor": True,
            },
            "modules": [name for _, name in MODULES],
        }
    return json.loads(strip_jsonc(path.read_text(encoding="utf-8")))


class FastfetchDesigner(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.connect("activate", self.on_activate)
        self.config_path = discover_config()
        self.config = load_config(self.config_path)
        self.module_checks = {}

    def on_activate(self, app):
        if getattr(self, "window", None) is not None:
            self.window.present()
            return

        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title(APP_NAME)
        self.window.set_default_size(1280, 780)
        self.window.set_size_request(980, 650)
        self.apply_css()
        self.window.set_child(self.build_ui())
        self.populate_from_config()
        self.refresh_preview()
        self.window.present()

    def apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(b"""
        window { background: #11171A; }
        .root { background: #11171A; }
        .sidebar { background: #10161A; border-right: 1px solid #39464A; }
        .preview-area { background: #182124; }
        .card { background: #1D272A; border: 1px solid #39484D; border-radius: 10px; padding: 10px; }
        .heading { color: #F0F3F4; font-weight: 700; }
        .body-text { color: #D8DEE9; }
        .muted { color: #93A2A8; font-size: 12px; }
        .terminal { background: #202A2D; border: 1px solid #405055; border-radius: 10px; padding: 18px; }
        .terminal-bar { color: #9FAEB3; font-size: 12px; }
        entry { background: #202A2D; color: #E6E6E6; caret-color: #E6E6E6; }
        spinbutton, dropdown, combobox { color: #E6E6E6; }
        checkbutton { color: #D8DEE9; min-height: 28px; }
        button { min-height: 30px; }
        """, -1)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("root")

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.set_margin_start(16)
        header.set_margin_end(16)
        header.set_margin_top(12)
        header.set_margin_bottom(10)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(label=APP_NAME)
        title.set_xalign(0)
        title.add_css_class("heading")
        subtitle = Gtk.Label(label="Visual editor for the active Fastfetch configuration")
        subtitle.set_xalign(0)
        subtitle.add_css_class("muted")
        title_box.append(title)
        title_box.append(subtitle)
        header.append(title_box)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.append(spacer)

        refresh = Gtk.Button(label="Refresh")
        refresh.connect("clicked", self.reload_config)
        header.append(refresh)

        save = Gtk.Button(label="Save config")
        save.add_css_class("suggested-action")
        save.connect("clicked", self.save_config)
        header.append(save)
        root.append(header)

        paned = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        paned.set_position(325)
        root.append(paned)

        sidebar = Gtk.ScrolledWindow()
        sidebar.set_vexpand(True)
        sidebar.set_min_content_width(300)
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        side.add_css_class("sidebar")
        side.set_margin_start(12)
        side.set_margin_end(12)
        side.set_margin_top(8)
        side.set_margin_bottom(12)
        sidebar.set_child(side)
        self.build_logo_card(side)
        self.build_colors_card(side)
        self.build_modules_card(side)
        self.build_advanced_card(side)
        paned.set_start_child(sidebar)

        preview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        preview.add_css_class("preview-area")
        preview.set_margin_start(12)
        preview.set_margin_end(14)
        preview.set_margin_top(8)
        preview.set_margin_bottom(12)

        label = Gtk.Label(label="Current Fastfetch")
        label.set_xalign(0)
        label.add_css_class("heading")
        preview.append(label)

        self.terminal = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.terminal.add_css_class("terminal")
        self.terminal.set_vexpand(True)
        preview.append(self.terminal)

        self.status = Gtk.Label(label=str(self.config_path))
        self.status.set_xalign(0)
        self.status.add_css_class("muted")
        preview.append(self.status)
        paned.set_end_child(preview)
        return root

    def card(self, parent, title, hint=None):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        box.add_css_class("card")
        label = Gtk.Label(label=title)
        label.set_xalign(0)
        label.add_css_class("heading")
        box.append(label)
        if hint:
            h = Gtk.Label(label=hint)
            h.set_xalign(0)
            h.set_wrap(True)
            h.add_css_class("muted")
            box.append(h)
        parent.append(box)
        return box

    def row(self, parent, label, widget):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lab = Gtk.Label(label=label)
        lab.set_xalign(0)
        lab.set_hexpand(True)
        lab.add_css_class("body-text")
        row.append(lab)
        row.append(widget)
        parent.append(row)

    def spin_row(self, parent, label, value, low, high):
        spin = Gtk.SpinButton.new_with_range(low, high, 1)
        spin.set_value(value)
        spin.set_width_chars(5)
        spin.connect("value-changed", lambda *_: self.refresh_preview())
        self.row(parent, label, spin)
        return spin

    def build_logo_card(self, parent):
        card = self.card(parent, "Logo", "Choose a built-in emblem or import an image.")
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        upload = Gtk.Button(label="Upload image")
        upload.connect("clicked", self.choose_logo)
        reset = Gtk.Button(label="Reset")
        reset.connect("clicked", self.reset_logo)
        buttons.append(upload)
        buttons.append(reset)
        card.append(buttons)

        self.logo_type = Gtk.DropDown.new_from_strings(["builtin", "file", "kitty", "sixel", "chafa"])
        self.row(card, "Type", self.logo_type)
        self.logo_source = Gtk.Entry()
        self.logo_source.set_placeholder_text("auto, arch, or /path/to/image")
        self.row(card, "Source", self.logo_source)

        self.logo_x = self.spin_row(card, "X", 0, -999, 999)
        self.logo_y = self.spin_row(card, "Y", 0, -999, 999)
        self.logo_w = self.spin_row(card, "W", 48, 1, 300)
        self.logo_h = self.spin_row(card, "H", 29, 1, 300)
        self.logo_gap = self.spin_row(card, "Gap", 3, 0, 100)

    def build_colors_card(self, parent):
        card = self.card(parent, "Appearance", "Use bright, readable colors similar to the reference Fastfetch layout.")
        self.preset = Gtk.DropDown.new_from_strings(["Custom"] + list(PRESETS.keys()))
        self.preset.connect("notify::selected", self.apply_preset)
        self.row(card, "Preset", self.preset)

        self.colors = {}
        defaults = PRESETS["Default"]
        for key, label in [("keys", "Keys"), ("title", "Title"), ("output", "Output"), ("separator", "Separator")]:
            entry = Gtk.Entry()
            entry.set_text(defaults[key])
            entry.connect("changed", lambda *_: self.refresh_preview())
            self.colors[key] = entry
            self.row(card, label, entry)

        self.bright = Gtk.CheckButton(label="Bright key/title/logo colors")
        self.bright.set_active(True)
        self.bright.connect("toggled", lambda *_: self.refresh_preview())
        card.append(self.bright)

    def build_modules_card(self, parent):
        card = self.card(parent, "Modules", "Toggle the common modules shown by Fastfetch.")
        grid = Gtk.Grid(column_spacing=12, row_spacing=2)
        for i, (label, key) in enumerate(MODULES):
            check = Gtk.CheckButton(label=label)
            check.connect("toggled", lambda *_: self.refresh_preview())
            self.module_checks[key] = check
            grid.attach(check, i % 2, i // 2, 1, 1)
        card.append(grid)

    def build_advanced_card(self, parent):
        card = self.card(parent, "Advanced", "The active config is detected automatically. Edit it manually only when needed.")
        edit = Gtk.Button(label="Open config in editor")
        edit.connect("clicked", self.open_editor)
        card.append(edit)
        self.editor = Gtk.Entry()
        self.editor.set_text(os.environ.get("EDITOR", "micro"))
        self.row(card, "Editor", self.editor)
        backup = Gtk.Label(label="Save creates config.jsonc.bak before replacing an existing config.")
        backup.set_xalign(0)
        backup.set_wrap(True)
        backup.add_css_class("muted")
        card.append(backup)

    def populate_from_config(self):
        logo = self.config.get("logo") or {}
        if not isinstance(logo, dict):
            logo = {}
        type_name = str(logo.get("type", "builtin"))
        types = ["builtin", "file", "kitty", "sixel", "chafa"]
        self.logo_type.set_selected(types.index(type_name) if type_name in types else 0)
        self.logo_source.set_text(str(logo.get("source", "auto")))
        padding = logo.get("padding") if isinstance(logo.get("padding"), dict) else {}
        self.logo_x.set_value(float(padding.get("left", 0)))
        self.logo_y.set_value(float(padding.get("top", 0)))
        self.logo_gap.set_value(float(padding.get("right", 3)))
        self.logo_w.set_value(float(logo.get("width", 48) or 48))
        self.logo_h.set_value(float(logo.get("height", 29) or 29))

        display = self.config.get("display") if isinstance(self.config.get("display"), dict) else {}
        color = display.get("color") if isinstance(display.get("color"), dict) else {}
        for key, entry in self.colors.items():
            entry.set_text(str(color.get(key, PRESETS["Default"][key])))
        self.bright.set_active(bool(display.get("brightColor", True)))

        mods = self.config.get("modules") or []
        active = set()
        for item in mods:
            if isinstance(item, str):
                active.add(item)
            elif isinstance(item, dict) and item.get("type"):
                active.add(str(item["type"]))
        for key, check in self.module_checks.items():
            check.set_active(key in active if active else True)

    def apply_preset(self, dropdown, _pspec):
        index = dropdown.get_selected()
        names = ["Custom"] + list(PRESETS.keys())
        if index <= 0 or index >= len(names):
            return
        preset = PRESETS[names[index]]
        for key, value in preset.items():
            self.colors[key].set_text(value)
        self.refresh_preview()

    def choose_logo(self, *_):
        dialog = Gtk.FileDialog(title="Choose Fastfetch logo")
        filter_img = Gtk.FileFilter()
        filter_img.set_name("Images")
        for mime in ["image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml"]:
            filter_img.add_mime_type(mime)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_img)
        dialog.set_filters(filters)
        dialog.set_default_filter(filter_img)
        dialog.open(self.window, None, self.on_logo_selected)

    def on_logo_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return
        path = Path(file.get_path())
        LOGO_DIR.mkdir(parents=True, exist_ok=True)
        target = LOGO_DIR / path.name
        try:
            if path.resolve() != target.resolve():
                shutil.copy2(path, target)
            self.logo_type.set_selected(1)
            self.logo_source.set_text(str(target))
            self.refresh_preview()
        except OSError as exc:
            self.show_error(str(exc))

    def reset_logo(self, *_):
        self.logo_type.set_selected(0)
        self.logo_source.set_text("auto")
        self.logo_x.set_value(0)
        self.logo_y.set_value(0)
        self.logo_w.set_value(48)
        self.logo_h.set_value(29)
        self.logo_gap.set_value(3)
        self.refresh_preview()

    def reload_config(self, *_):
        try:
            self.config_path = discover_config()
            self.config = load_config(self.config_path)
            self.populate_from_config()
            self.refresh_preview()
        except Exception as exc:
            self.show_error(str(exc))

    def current_state(self):
        types = ["builtin", "file", "kitty", "sixel", "chafa"]
        return {
            "logo_type": types[self.logo_type.get_selected()],
            "logo_source": self.logo_source.get_text().strip() or "auto",
            "x": int(self.logo_x.get_value()),
            "y": int(self.logo_y.get_value()),
            "w": int(self.logo_w.get_value()),
            "h": int(self.logo_h.get_value()),
            "gap": int(self.logo_gap.get_value()),
            "keys": self.colors["keys"].get_text().strip() or PRESETS["Default"]["keys"],
            "title": self.colors["title"].get_text().strip() or PRESETS["Default"]["title"],
            "output": self.colors["output"].get_text().strip() or PRESETS["Default"]["output"],
            "separator": self.colors["separator"].get_text().strip() or PRESETS["Default"]["separator"],
            "bright": self.bright.get_active(),
            "modules": [key for _, key in MODULES if self.module_checks[key].get_active()],
        }

    def make_config(self):
        state = self.current_state()
        cfg = copy.deepcopy(self.config)
        logo = cfg.setdefault("logo", {})
        logo["type"] = state["logo_type"]
        logo["source"] = state["logo_source"]
        logo["width"] = state["w"]
        logo["height"] = state["h"]
        logo["padding"] = {
            "left": state["x"],
            "top": state["y"],
            "right": state["gap"],
        }

        display = cfg.setdefault("display", {})
        display["color"] = {
            "keys": state["keys"],
            "title": state["title"],
            "output": state["output"],
            "separator": state["separator"],
        }
        display["brightColor"] = state["bright"]

        existing_objects = {
            str(item.get("type")): item
            for item in cfg.get("modules", [])
            if isinstance(item, dict) and item.get("type")
        }
        cfg["modules"] = [existing_objects.get(key, key) for key in state["modules"]]
        cfg.setdefault("$schema", "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json")
        return cfg

    def save_config(self, *_):
        try:
            new_cfg = self.make_config()
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            if self.config_path.exists():
                backup = self.config_path.with_name(self.config_path.name + ".bak")
                shutil.copy2(self.config_path, backup)
            self.config_path.write_text(
                json.dumps(new_cfg, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            self.config = new_cfg
            self.status.set_text(f"Saved: {self.config_path}")
            self.refresh_preview()
        except Exception as exc:
            self.show_error(str(exc))

    def open_editor(self, *_):
        editor = self.editor.get_text().strip() or "micro"
        try:
            subprocess.Popen(editor.split() + [str(self.config_path)])
        except OSError as exc:
            self.show_error(f"Could not launch editor: {exc}")

    def preview_command(self):
        try:
            temp = Path(GLib.get_tmp_dir()) / f"fastfetch-designer-{os.getpid()}.jsonc"
            temp.write_text(json.dumps(self.make_config(), ensure_ascii=False), encoding="utf-8")
            try:
                result = subprocess.run(
                    ["fastfetch", "--config", str(temp), "--pipe"],
                    capture_output=True,
                    text=True,
                    timeout=6,
                    check=False,
                )
            finally:
                try:
                    temp.unlink()
                except OSError:
                    pass
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return result.stderr.strip() or "Fastfetch produced no output."
        except FileNotFoundError:
            return "fastfetch is not installed or not available in PATH."
        except subprocess.TimeoutExpired:
            return "Fastfetch preview timed out."
        except Exception as exc:
            return f"Preview error: {exc}"

    def render_preview(self, output):
        child = self.terminal.get_first_child()
        while child is not None:
            self.terminal.remove(child)
            child = self.terminal.get_first_child()

        bar = Gtk.Label(label="●  ●  ●    Current Fastfetch")
        bar.set_xalign(0)
        bar.add_css_class("terminal-bar")
        self.terminal.append(bar)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        body.set_vexpand(True)
        body.set_margin_top(18)
        body.set_margin_bottom(18)

        state = self.current_state()
        source = state["logo_source"]
        image_path = Path(os.path.expanduser(source))
        if state["logo_type"] in {"file", "kitty", "sixel", "chafa"} and image_path.is_file():
            picture = Gtk.Picture.new_for_filename(str(image_path))
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_size_request(260, 300)
            body.append(picture)
        else:
            logo = Gtk.Label(label=self.builtin_logo(source))
            logo.set_xalign(0)
            logo.set_yalign(0)
            logo.set_vexpand(True)
            logo.add_css_class("body-text")
            body.append(logo)

        text = Gtk.Label()
        text.set_xalign(0)
        text.set_yalign(0)
        text.set_selectable(True)
        text.set_use_markup(True)
        text.set_hexpand(True)
        text.set_wrap(False)
        text.set_markup(self.format_output(output, state))
        text.add_css_class("body-text")
        body.append(text)
        self.terminal.append(body)

    def format_output(self, output, state):
        lines = []
        for raw in output.splitlines():
            line = raw.rstrip()
            if not line:
                lines.append("")
                continue
            match = re.match(r"^(.*?)(:\s+)(.*)$", line)
            if match:
                key, sep, value = match.groups()
                lines.append(
                    f'<span foreground="{html.escape(state["keys"])}">{html.escape(key)}</span>'
                    f'<span foreground="{html.escape(state["separator"])}">{html.escape(sep)}</span>'
                    f'<span foreground="{html.escape(state["output"])}">{html.escape(value)}</span>'
                )
            else:
                lines.append(f'<span foreground="{html.escape(state["title"])}">{html.escape(line)}</span>')
        return "\n".join(lines)

    @staticmethod
    def builtin_logo(source):
        if source in {"arch", "auto", ""}:
            return "\n".join([
                "        /\\",
                "       /  \\",
                "      / /\\ \\",
                "     / /  \\ \\",
                "    /_/    \\_\\",
            ])
        return "\n".join([
            "   █████████",
            "  ██  LOGO  ██",
            " ██           ██",
            "  ██         ██",
            "   ███████████",
        ])

    def refresh_preview(self, *_):
        if not hasattr(self, "terminal"):
            return
        output = self.preview_command()
        self.render_preview(output)
        self.status.set_text(f"Active config: {self.config_path}")

    def show_error(self, message):
        dialog = Gtk.AlertDialog(message=APP_NAME)
        dialog.set_detail(str(message))
        dialog.show(self.window)


def main():
    return FastfetchDesigner().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())

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

APP_NAME = "Fastfetch Designer"
APP_ID = "io.github.ilhamfirmansyahhub.FastfetchDesigner"
CONFIG_FALLBACK = Path.home() / ".config" / "fastfetch" / "config.jsonc"
ASSET_DIR = Path.home() / ".config" / "fastfetch" / "assets"

MODULES = [
    ("OS", "os"), ("Kernel", "kernel"), ("Uptime", "uptime"),
    ("Packages", "packages"), ("Shell", "shell"), ("Display", "display"),
    ("DE", "de"), ("WM", "wm"), ("Theme", "theme"), ("Icons", "icons"),
    ("Terminal", "terminal"), ("CPU", "cpu"), ("GPU", "gpu"),
    ("Memory", "memory"), ("Disk", "disk"),
]

COLORS = {
    "Default": {"keys": "#EBDBB2", "title": "#F0F0F0", "output": "#D8DEE9", "separator": "#928374"},
    "Gruvbox": {"keys": "#EBDBB2", "title": "#FABD2F", "output": "#FBF1C7", "separator": "#B8BB26"},
    "Catppuccin": {"keys": "#CDD6F4", "title": "#89B4FA", "output": "#CDD6F4", "separator": "#A6E3A1"},
    "Nord": {"keys": "#D8DEE9", "title": "#88C0D0", "output": "#E5E9F0", "separator": "#81A1C1"},
    "Monochrome": {"keys": "#FFFFFF", "title": "#FFFFFF", "output": "#D0D0D0", "separator": "#888888"},
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
        elif c == "/" and n == "*":
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
        else:
            out.append(c)
        i += 1
    return re.sub(r",\s*([}\]])", r"\1", "".join(out))


def discover_config() -> Path:
    candidates = []
    for env_name in ("FASTFETCH_CONFIG", "FASTFETCH_CONFIG_PATH"):
        value = os.environ.get(env_name)
        if value:
            p = Path(os.path.expandvars(os.path.expanduser(value)))
            if p.is_file():
                candidates.append(p)

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
            line = line.split(" -> ", 1)[0].strip().strip('"')
            line = os.path.expandvars(os.path.expanduser(line))
            p = Path(line)
            if p.is_dir():
                p = p / "config.jsonc"
            if p.is_file():
                candidates.append(p)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        pass

    xdg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    candidates.extend([xdg / "fastfetch" / "config.jsonc", xdg / "fastfetch" / "config.json", CONFIG_FALLBACK])

    seen = set()
    for p in candidates:
        try:
            key = str(p.resolve())
        except OSError:
            key = str(p)
        if key in seen:
            continue
        seen.add(key)
        if p.is_file():
            return p
    return CONFIG_FALLBACK


def read_config(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(strip_jsonc(path.read_text(encoding="utf-8")))
    except Exception as exc:
        raise RuntimeError(f"Could not parse {path}: {exc}")


def module_key(item):
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        value = item.get("type") or item.get("name")
        return value if isinstance(value, str) else None
    return None


def resolve_logo(config_path: Path, logo: dict):
    if not isinstance(logo, dict):
        return None
    source = logo.get("source")
    if not isinstance(source, str) or not source or source in {"auto", "none", "builtin"}:
        return None
    expanded = os.path.expandvars(os.path.expanduser(source.strip()))
    paths = [Path(expanded)]
    if not Path(expanded).is_absolute():
        paths.extend([config_path.parent / expanded, Path.home() / expanded, ASSET_DIR / expanded])
    for p in paths:
        try:
            if p.is_file():
                return p
        except OSError:
            pass
    return None


def run_fastfetch(config_path: Path):
    cmd = ["fastfetch"]
    if config_path.is_file():
        cmd += ["--config", str(config_path)]
    cmd += ["--logo", "none", "--pipe"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=8, check=False)
    except FileNotFoundError:
        return "", "Fastfetch is not installed or not available in PATH."
    except subprocess.TimeoutExpired:
        return "", "Fastfetch preview timed out."
    if result.returncode != 0:
        return result.stdout.rstrip("\n"), result.stderr.strip() or "Fastfetch returned an error."
    return result.stdout.rstrip("\n"), ""


class FastfetchDesigner(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.connect("activate", self.on_activate)
        self.config_path = discover_config()
        self.config = read_config(self.config_path)
        self.syncing = False
        self.text_edited = False
        self.loading_text = False

    def on_activate(self, app):
        if getattr(self, "window", None):
            self.window.present()
            return
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title(APP_NAME)
        self.window.set_default_size(1280, 800)
        self.window.set_size_request(1050, 680)
        self.apply_css()
        self.window.set_child(self.build_ui())
        self.build_state_from_config()
        self.window.present()

    def apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(b"""
        * { color: #D8DEE9; }
        window { background: #11171A; }
        .root { background: #11171A; }
        .card { background: #1B2528; border: 1px solid #354247; border-radius: 10px; padding: 10px; }
        .heading { color: #F4F6F7; font-weight: 700; }
        .muted { color: #8F9CA2; font-size: 12px; }
        .preview-shell { background: #1B2225; border: 1px solid #405055; border-radius: 10px; padding: 10px; }
        textview, textview.view { background: #202A2D; color: #D8DEE9; font-family: monospace; font-size: 13px; }
        entry, spinbutton, dropdown { background: #202A2D; color: #E6E6E6; }
        checkbutton { color: #D8DEE9; }
        """, -1)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("root")
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.set_margin_start(16); header.set_margin_end(16); header.set_margin_top(12); header.set_margin_bottom(10)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(label=APP_NAME); title.set_xalign(0); title.add_css_class("heading")
        subtitle = Gtk.Label(label="Edit your current Fastfetch setup visually"); subtitle.set_xalign(0); subtitle.add_css_class("muted")
        title_box.append(title); title_box.append(subtitle); header.append(title_box)
        spacer = Gtk.Box(); spacer.set_hexpand(True); header.append(spacer)
        refresh = Gtk.Button(label="Reload current config"); refresh.connect("clicked", self.reload_config); header.append(refresh)
        save = Gtk.Button(label="Save"); save.add_css_class("suggested-action"); save.connect("clicked", self.save); header.append(save)
        root.append(header)

        paned = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL); paned.set_position(350); root.append(paned)
        scroll = Gtk.ScrolledWindow(); scroll.set_min_content_width(320)
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        side.set_margin_start(12); side.set_margin_end(12); side.set_margin_top(4); side.set_margin_bottom(12)
        scroll.set_child(side)
        self.build_logo_panel(side); self.build_color_panel(side); self.build_modules_panel(side); self.build_advanced_panel(side)
        paned.set_start_child(scroll)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right.set_margin_start(12); right.set_margin_end(14); right.set_margin_top(8); right.set_margin_bottom(12)
        current = Gtk.Label(label="Current Fastfetch"); current.set_xalign(0); current.add_css_class("heading"); right.append(current)
        self.preview_shell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); self.preview_shell.add_css_class("preview-shell"); self.preview_shell.set_vexpand(True)
        self.preview = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18); self.preview.set_vexpand(True)
        self.preview_shell.append(self.preview)

        self.logo = Gtk.Picture(); self.logo.set_content_fit(Gtk.ContentFit.CONTAIN); self.logo.set_size_request(240, 300)
        self.logo_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); self.logo_box.set_size_request(250, -1); self.logo_box.set_halign(Gtk.Align.START); self.logo_box.set_valign(Gtk.Align.START)
        self.logo_box.append(self.logo); self.preview.append(self.logo_box)

        self.text_view = Gtk.TextView(); self.text_view.set_monospace(True); self.text_view.set_wrap_mode(Gtk.WrapMode.NONE); self.text_view.set_hexpand(True); self.text_view.set_vexpand(True)
        self.text_view.set_top_margin(14); self.text_view.set_bottom_margin(14); self.text_view.set_left_margin(8); self.text_view.set_right_margin(10)
        self.text_buffer = self.text_view.get_buffer(); self.text_buffer.connect("changed", self.on_text_changed)
        self.preview.append(self.text_view); right.append(self.preview_shell)

        hint = Gtk.Label(label="Edit the Fastfetch output directly here. Save converts manually edited text into Fastfetch custom modules.")
        hint.set_xalign(0); hint.set_wrap(True); hint.add_css_class("muted"); right.append(hint)
        self.status = Gtk.Label(); self.status.set_xalign(0); self.status.add_css_class("muted"); right.append(self.status)
        paned.set_end_child(right)
        return root

    def card(self, parent, title, hint=None):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7); box.add_css_class("card")
        label = Gtk.Label(label=title); label.set_xalign(0); label.add_css_class("heading"); box.append(label)
        if hint:
            h = Gtk.Label(label=hint); h.set_xalign(0); h.set_wrap(True); h.add_css_class("muted"); box.append(h)
        parent.append(box); return box

    def row(self, parent, label, widget):
        r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        l = Gtk.Label(label=label); l.set_xalign(0); l.set_hexpand(True); r.append(l); r.append(widget); parent.append(r)

    def spin(self, parent, label, value, low, high):
        w = Gtk.SpinButton.new_with_range(low, high, 1); w.set_value(value); self.row(parent, label, w); return w

    def build_logo_panel(self, parent):
        c = self.card(parent, "Logo", "The currently configured image is loaded automatically when possible.")
        b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        choose = Gtk.Button(label="Choose image"); choose.connect("clicked", self.choose_logo)
        reset = Gtk.Button(label="Use configured"); reset.connect("clicked", lambda *_: self.build_state_from_config())
        b.append(choose); b.append(reset); c.append(b)
        self.logo_source = Gtk.Entry(); self.logo_source.set_placeholder_text("auto / image path"); self.row(c, "Source", self.logo_source)
        self.logo_x = self.spin(c, "X", 0, -500, 500); self.logo_y = self.spin(c, "Y", 0, -500, 500)
        self.logo_w = self.spin(c, "Width", 40, 1, 500); self.logo_h = self.spin(c, "Height", 22, 1, 500); self.logo_gap = self.spin(c, "Gap", 4, 0, 100)
        for w in (self.logo_x, self.logo_y, self.logo_w, self.logo_h, self.logo_gap): w.connect("value-changed", lambda *_: self.apply_logo_geometry())

    def build_color_panel(self, parent):
        c = self.card(parent, "Appearance", "Edit the colors used by the Fastfetch display.")
        self.preset = Gtk.DropDown.new_from_strings(["Custom"] + list(COLORS.keys())); self.preset.connect("notify::selected", self.apply_preset); self.row(c, "Preset", self.preset)
        self.color_entries = {}
        for key, label in (("keys", "Keys"), ("title", "Title"), ("output", "Output"), ("separator", "Separator")):
            e = Gtk.Entry(); e.set_width_chars(11); e.connect("changed", lambda *_: self.apply_text_css()); self.color_entries[key] = e; self.row(c, label, e)

    def build_modules_panel(self, parent):
        c = self.card(parent, "Modules", "Toggle standard Fastfetch modules. Changes update Current Fastfetch.")
        grid = Gtk.Grid(column_spacing=12, row_spacing=2); self.checks = {}
        for i, (label, key) in enumerate(MODULES):
            cb = Gtk.CheckButton(label=label); cb.connect("toggled", lambda *_: self.on_modules_changed()); self.checks[key] = cb; grid.attach(cb, i % 2, i // 2, 1, 1)
        c.append(grid)

    def build_advanced_panel(self, parent):
        c = self.card(parent, "Advanced", "Open the actual JSONC when you need full manual control.")
        edit = Gtk.Button(label="Open config in editor"); edit.connect("clicked", self.open_editor); c.append(edit)
        self.editor = Gtk.Entry(); self.editor.set_text(os.environ.get("EDITOR", "micro")); self.row(c, "Editor", self.editor)

    def build_state_from_config(self):
        try:
            self.config_path = discover_config(); self.config = read_config(self.config_path)
        except Exception as exc:
            self.show_error(str(exc)); return
        logo = self.config.get("logo") if isinstance(self.config, dict) else {}; logo = logo if isinstance(logo, dict) else {}
        self.logo_source.set_text(str(logo.get("source", "auto")))
        padding = logo.get("padding") if isinstance(logo.get("padding"), dict) else {}
        self.syncing = True
        self.logo_x.set_value(float(padding.get("left", 0) or 0)); self.logo_y.set_value(float(padding.get("top", 0) or 0)); self.logo_gap.set_value(float(padding.get("right", 4) or 4))
        self.logo_w.set_value(float(logo.get("width", 40) or 40)); self.logo_h.set_value(float(logo.get("height", 22) or 22))
        display = self.config.get("display") if isinstance(self.config.get("display"), dict) else {}
        colors = display.get("color") if isinstance(display.get("color"), dict) else {}
        for key, entry in self.color_entries.items(): entry.set_text(str(colors.get(key, COLORS["Default"][key])))
        modules = self.config.get("modules") or []
        active = {module_key(item) for item in modules if module_key(item)}
        for key, cb in self.checks.items(): cb.set_active(key in active if active else True)
        self.syncing = False
        logo_path = resolve_logo(self.config_path, logo)
        if logo_path:
            self.logo.set_filename(str(logo_path)); self.logo.set_visible(True)
        else:
            self.logo.set_visible(False)
        self.apply_logo_geometry(); self.text_edited = False; self.refresh_output(); self.status.set_text(f"Loaded: {self.config_path}")

    def reload_config(self, *_): self.build_state_from_config()

    def refresh_output(self):
        output, error = run_fastfetch(self.config_path)
        self.loading_text = True
        self.text_buffer.set_text(error if error and not output else output)
        self.loading_text = False
        self.text_edited = False
        self.apply_text_css()

    def on_text_changed(self, _buffer):
        if not self.loading_text:
            self.text_edited = True

    def on_modules_changed(self):
        if self.syncing or self.text_edited:
            return
        self.refresh_output()

    def apply_text_css(self):
        if not hasattr(self, "text_view"): return
        value = self.color_entries["output"].get_text().strip()
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value): value = COLORS["Default"]["output"]
        provider = Gtk.CssProvider(); provider.load_from_data(f"textview.view {{ color: {value}; font-family: monospace; font-size: 13px; }}".encode(), -1)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def apply_preset(self, dropdown, _pspec):
        names = ["Custom"] + list(COLORS.keys()); idx = dropdown.get_selected()
        if idx <= 0 or idx >= len(names): return
        for key, value in COLORS[names[idx]].items(): self.color_entries[key].set_text(value)
        self.apply_text_css()

    def apply_logo_geometry(self):
        if not hasattr(self, "logo_box") or self.syncing: return
        self.logo_box.set_margin_start(max(0, self.logo_x.get_value_as_int())); self.logo_box.set_margin_top(max(0, self.logo_y.get_value_as_int()))
        self.logo.set_size_request(self.logo_w.get_value_as_int() * 7, self.logo_h.get_value_as_int() * 14)

    def choose_logo(self, *_):
        dialog = Gtk.FileDialog(title="Choose Fastfetch logo")
        filt = Gtk.FileFilter(); filt.set_name("Images")
        for mime in ("image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml"): filt.add_mime_type(mime)
        filters = Gio.ListStore.new(Gtk.FileFilter); filters.append(filt); dialog.set_filters(filters); dialog.set_default_filter(filt); dialog.open(self.window, None, self.logo_selected)

    def logo_selected(self, dialog, result):
        try: file = dialog.open_finish(result)
        except GLib.Error: return
        source = Path(file.get_path()); ASSET_DIR.mkdir(parents=True, exist_ok=True); target = ASSET_DIR / source.name
        try:
            if source.resolve() != target.resolve(): shutil.copy2(source, target)
            self.logo_source.set_text(str(target)); self.logo.set_filename(str(target)); self.logo.set_visible(True); self.apply_logo_geometry()
        except OSError as exc:
            self.show_error(str(exc))

    def open_editor(self, *_):
        editor = self.editor.get_text().strip() or "micro"
        try: subprocess.Popen(editor.split() + [str(self.config_path)])
        except OSError as exc: self.show_error(str(exc))

    def save(self, *_):
        try:
            cfg = copy.deepcopy(self.config)
            logo = cfg.setdefault("logo", {})
            logo["source"] = self.logo_source.get_text().strip() or "auto"
            logo["width"] = self.logo_w.get_value_as_int(); logo["height"] = self.logo_h.get_value_as_int()
            logo["padding"] = {"left": max(0, self.logo_x.get_value_as_int()), "top": max(0, self.logo_y.get_value_as_int()), "right": max(0, self.logo_gap.get_value_as_int())}
            display = cfg.setdefault("display", {}); color = display.setdefault("color", {})
            for key, entry in self.color_entries.items():
                value = entry.get_text().strip()
                if re.fullmatch(r"#[0-9A-Fa-f]{6}", value): color[key] = value
            if self.text_edited:
                raw = self.text_buffer.get_text(self.text_buffer.get_start_iter(), self.text_buffer.get_end_iter(), False)
                lines = [line for line in raw.splitlines() if line.strip()]
                cfg["modules"] = [{"type": "custom", "format": line} for line in lines]
            else:
                modules = [key for _, key in MODULES if self.checks[key].get_active()]
                if modules:
                    existing = {module_key(item): item for item in cfg.get("modules", []) if isinstance(item, dict) and module_key(item)}
                    cfg["modules"] = [existing.get(key, key) for key in modules]
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            if self.config_path.is_file(): shutil.copy2(self.config_path, self.config_path.with_name(self.config_path.name + ".bak"))
            self.config_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            self.config = cfg; self.text_edited = False; self.status.set_text(f"Saved: {self.config_path}"); self.refresh_output()
        except Exception as exc:
            self.show_error(str(exc))

    def show_error(self, message):
        dialog = Gtk.AlertDialog(message=APP_NAME); dialog.set_detail(str(message)); dialog.show(self.window)


def main():
    return FastfetchDesigner().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
import copy
import json
import os
import re
import shlex
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
    "Default": {"keys": "#EBDBB2", "title": "#FABD2F", "output": "#FBF1C7", "separator": "#928374"},
    "Gruvbox": {"keys": "#EBDBB2", "title": "#FABD2F", "output": "#FBF1C7", "separator": "#B8BB26"},
    "Catppuccin": {"keys": "#CDD6F4", "title": "#89B4FA", "output": "#CDD6F4", "separator": "#A6E3A1"},
    "Nord": {"keys": "#D8DEE9", "title": "#88C0D0", "output": "#E5E9F0", "separator": "#81A1C1"},
    "Monochrome": {"keys": "#FFFFFF", "title": "#FFFFFF", "output": "#E6E6E6", "separator": "#AAAAAA"},
}

# Fastfetch can return ANSI SGR/cursor sequences when piped. Never show
# those control codes inside the editable GTK TextView.
ANSI_RE = re.compile(r"\x1B(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1B\\))")


def strip_ansi(text: str) -> str:
    text = ANSI_RE.sub("", text)
    return "".join(c for c in text if c in "\n\r\t" or ord(c) >= 32)


def strip_jsonc(text: str) -> str:
    out, i, quoted, escaped = [], 0, False, False
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ""
        if quoted:
            out.append(c)
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
            i += 1
            continue
        if c == '"':
            quoted = True; out.append(c); i += 1
        elif c == "/" and n == "/":
            i += 2
            while i < len(text) and text[i] not in "\r\n": i += 1
        elif c == "/" and n == "*":
            i += 2
            while i + 1 < len(text) and text[i:i + 2] != "*/": i += 1
            i += 2
        else:
            out.append(c); i += 1
    return re.sub(r",\s*([}\]])", r"\1", "".join(out))


def discover_config() -> Path:
    candidates = []
    for env_name in ("FASTFETCH_CONFIG", "FASTFETCH_CONFIG_PATH"):
        value = os.environ.get(env_name)
        if value:
            p = Path(os.path.expandvars(os.path.expanduser(value)))
            if p.is_file(): candidates.append(p)
    try:
        r = subprocess.run(["fastfetch", "--list-config-paths"], capture_output=True, text=True, timeout=3, check=False)
        for raw in r.stdout.splitlines():
            line = raw.strip()
            if not line or line.startswith(("#", "//")): continue
            p = Path(os.path.expandvars(os.path.expanduser(line.split(" -> ", 1)[0].strip().strip('"')))
            if p.is_dir(): p = p / "config.jsonc"
            if p.is_file(): candidates.append(p)
    except (OSError, subprocess.TimeoutExpired):
        pass
    xdg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    candidates += [xdg / "fastfetch" / "config.jsonc", xdg / "fastfetch" / "config.json", CONFIG_FALLBACK]
    seen = set()
    for p in candidates:
        try: key = str(p.resolve())
        except OSError: key = str(p)
        if key in seen: continue
        seen.add(key)
        if p.is_file(): return p
    return CONFIG_FALLBACK


def read_config(path: Path) -> dict:
    if not path.is_file(): return {}
    try: return json.loads(strip_jsonc(path.read_text(encoding="utf-8")))
    except Exception as exc: raise RuntimeError(f"Could not parse {path}: {exc}")


def module_key(item):
    if isinstance(item, str): return item
    if isinstance(item, dict):
        value = item.get("type") or item.get("name")
        return value if isinstance(value, str) else None
    return None


def resolve_logo(config_path: Path, source: str | None):
    if not source or source in {"auto", "none", "builtin"}: return None
    expanded = os.path.expandvars(os.path.expanduser(source.strip()))
    paths = [Path(expanded)]
    if not Path(expanded).is_absolute():
        paths += [config_path.parent / expanded, Path.home() / expanded, ASSET_DIR / expanded]
    for p in paths:
        try:
            if p.is_file(): return p
        except OSError:
            pass
    return None


def run_fastfetch(config_path: Path):
    cmd = ["fastfetch"]
    if config_path.is_file(): cmd += ["--config", str(config_path)]
    cmd += ["--logo", "none", "--pipe"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8, check=False)
    except FileNotFoundError:
        return "", "Fastfetch is not installed or not available in PATH."
    except subprocess.TimeoutExpired:
        return "", "Fastfetch preview timed out."
    out, err = strip_ansi(r.stdout.rstrip("\n")), strip_ansi(r.stderr.strip())
    if r.returncode != 0: return out, err or "Fastfetch returned an error."
    return out, ""


class FastfetchDesigner(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.connect("activate", self.on_activate)
        self.config_path = discover_config()
        self.config = read_config(self.config_path)
        self.syncing = False
        self.loading_text = False
        self.text_edited = False
        self.checks = {}

    def on_activate(self, app):
        if getattr(self, "window", None):
            self.window.present(); return
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title(APP_NAME)
        self.window.set_default_size(1280, 800)
        self.window.set_size_request(1040, 680)
        self.apply_css()
        self.window.set_child(self.build_ui())
        self.build_state_from_config()
        self.window.present()

    def apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(b"""
        * { color: #E6E6E6; }
        window, .root { background: #11171A; }
        .card { background: #1B2528; border: 1px solid #354247; border-radius: 10px; padding: 10px; }
        .heading { color: #F7F7F7; font-weight: 700; }
        .muted { color: #A5B0B5; font-size: 12px; }
        .preview-shell { background: #202A2D; border: 1px solid #405055; border-radius: 10px; padding: 14px; }
        .preview-text, textview.view { color: #F1E7C9; background: #202A2D; font-family: monospace; font-size: 14px; }
        entry, spinbutton, dropdown { background: #202A2D; color: #F0F0F0; }
        checkbutton { color: #E0E5E7; }
        button { min-height: 30px; }
        """, -1)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0); root.add_css_class("root")
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.set_margin_start(16); header.set_margin_end(16); header.set_margin_top(12); header.set_margin_bottom(10)
        tb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        t = Gtk.Label(label=APP_NAME); t.set_xalign(0); t.add_css_class("heading")
        s = Gtk.Label(label="Edit your current Fastfetch setup visually"); s.set_xalign(0); s.add_css_class("muted")
        tb.append(t); tb.append(s); header.append(tb)
        spacer = Gtk.Box(); spacer.set_hexpand(True); header.append(spacer)
        reload_btn = Gtk.Button(label="Reload current config"); reload_btn.connect("clicked", self.reload_config); header.append(reload_btn)
        save_btn = Gtk.Button(label="Save"); save_btn.add_css_class("suggested-action"); save_btn.connect("clicked", self.save); header.append(save_btn)
        root.append(header)

        paned = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL); paned.set_position(350); root.append(paned)
        scroll = Gtk.ScrolledWindow(); scroll.set_min_content_width(320)
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10); side.set_margin_start(12); side.set_margin_end(12); side.set_margin_bottom(12); side.set_margin_top(4)
        scroll.set_child(side)
        self.build_logo_panel(side); self.build_color_panel(side); self.build_modules_panel(side); self.build_advanced_panel(side)
        paned.set_start_child(scroll)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); right.set_margin_start(12); right.set_margin_end(14); right.set_margin_top(8); right.set_margin_bottom(12)
        title = Gtk.Label(label="Current Fastfetch"); title.set_xalign(0); title.add_css_class("heading"); right.append(title)
        shell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); shell.add_css_class("preview-shell"); shell.set_vexpand(True)
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18); content.set_vexpand(True); shell.append(content)
        self.logo = Gtk.Picture(); self.logo.set_content_fit(Gtk.ContentFit.CONTAIN); self.logo.set_size_request(250, 350)
        content.append(self.logo)
        text_scroll = Gtk.ScrolledWindow(); text_scroll.set_hexpand(True); text_scroll.set_vexpand(True)
        self.text_view = Gtk.TextView(); self.text_view.set_monospace(True); self.text_view.set_wrap_mode(Gtk.WrapMode.NONE); self.text_view.set_top_margin(8); self.text_view.set_bottom_margin(8); self.text_view.set_left_margin(8); self.text_view.set_right_margin(8); self.text_view.add_css_class("preview-text")
        self.text_buffer = self.text_view.get_buffer(); self.text_buffer.connect("changed", self.on_text_changed)
        text_scroll.set_child(self.text_view); content.append(text_scroll); right.append(shell)
        hint = Gtk.Label(label="Edit the Fastfetch output directly here. Save converts manually edited lines into custom modules."); hint.set_xalign(0); hint.set_wrap(True); hint.add_css_class("muted"); right.append(hint)
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
        c = self.card(parent, "Logo", "The current configured image is loaded automatically when possible.")
        b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        choose = Gtk.Button(label="Choose image"); choose.connect("clicked", self.choose_logo)
        use = Gtk.Button(label="Use configured"); use.connect("clicked", lambda *_: self.build_state_from_config())
        b.append(choose); b.append(use); c.append(b)
        self.logo_source = Gtk.Entry(); self.logo_source.set_placeholder_text("auto / image path"); self.row(c, "Source", self.logo_source)
        self.logo_x = self.spin(c, "X", 0, -500, 500); self.logo_y = self.spin(c, "Y", 0, -500, 500)
        self.logo_w = self.spin(c, "Width", 40, 1, 500); self.logo_h = self.spin(c, "Height", 22, 1, 500); self.logo_gap = self.spin(c, "Gap", 4, 0, 100)

    def build_color_panel(self, parent):
        c = self.card(parent, "Appearance", "Edit the colors used by the Fastfetch display.")
        self.preset = Gtk.DropDown.new_from_strings(["Custom"] + list(COLORS.keys())); self.preset.connect("notify::selected", self.apply_preset); self.row(c, "Preset", self.preset)
        self.color_entries = {}
        for key, label in (("keys", "Keys"), ("title", "Title"), ("output", "Output"), ("separator", "Separator")):
            e = Gtk.Entry(); e.set_width_chars(11); e.connect("changed", lambda *_: self.apply_text_css()); self.color_entries[key] = e; self.row(c, label, e)

    def build_modules_panel(self, parent):
        c = self.card(parent, "Modules", "Toggle common Fastfetch modules. Changes update Current Fastfetch.")
        grid = Gtk.Grid(column_spacing=12, row_spacing=2); self.checks = {}
        for i, (label, key) in enumerate(MODULES):
            cb = Gtk.CheckButton(label=label); cb.connect("toggled", lambda *_: self.on_modules_changed()); self.checks[key] = cb; grid.attach(cb, i % 2, i // 2, 1, 1)
        c.append(grid)

    def build_advanced_panel(self, parent):
        c = self.card(parent, "Advanced", "Open the actual JSONC when you need full manual control.")
        e = Gtk.Button(label="Open config in editor"); e.connect("clicked", self.open_editor); c.append(e)
        self.editor = Gtk.Entry(); self.editor.set_text(os.environ.get("EDITOR", "micro")); self.row(c, "Editor", self.editor)

    def build_state_from_config(self):
        try:
            self.config_path = discover_config(); self.config = read_config(self.config_path)
        except Exception as exc:
            self.show_error(str(exc)); return
        logo = self.config.get("logo") if isinstance(self.config.get("logo"), dict) else {}
        self.syncing = True
        self.logo_source.set_text(str(logo.get("source", "auto")))
        padding = logo.get("padding") if isinstance(logo.get("padding"), dict) else {}
        self.logo_x.set_value(float(padding.get("left", 0) or 0)); self.logo_y.set_value(float(padding.get("top", 0) or 0)); self.logo_gap.set_value(float(padding.get("right", 4) or 4))
        self.logo_w.set_value(float(logo.get("width", 40) or 40)); self.logo_h.set_value(float(logo.get("height", 22) or 22))
        display = self.config.get("display") if isinstance(self.config.get("display"), dict) else {}
        colors = display.get("color") if isinstance(display.get("color"), dict) else {}
        for key, entry in self.color_entries.items(): entry.set_text(str(colors.get(key, COLORS["Default"][key])))
        active = {module_key(item) for item in (self.config.get("modules") or []) if module_key(item)}
        for key, cb in self.checks.items(): cb.set_active(key in active if active else True)
        self.syncing = False
        logo_path = resolve_logo(self.config_path, logo.get("source"))
        self.logo.set_filename(str(logo_path)) if logo_path else self.logo.set_filename(None)
        self.text_edited = False; self.refresh_output(); self.status.set_text(f"Loaded: {self.config_path}")

    def reload_config(self, *_): self.build_state_from_config()

    def refresh_output(self):
        output, error = run_fastfetch(self.config_path)
        self.loading_text = True
        self.text_buffer.set_text(error if error and not output else output)
        self.loading_text = False
        self.text_edited = False
        self.apply_text_css()

    def on_text_changed(self, _buffer):
        if not self.loading_text: self.text_edited = True

    def on_modules_changed(self):
        if self.syncing or self.text_edited: return
        self.refresh_output()

    def apply_text_css(self):
        if not hasattr(self, "text_view"): return
        value = self.color_entries["output"].get_text().strip()
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value): value = COLORS["Default"]["output"]
        css = Gtk.CssProvider(); css.load_from_data(f"textview.view {{ color: {value}; font-family: monospace; font-size: 14px; }}".encode(), -1)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def apply_preset(self, dropdown, _pspec):
        names = ["Custom"] + list(COLORS.keys()); i = dropdown.get_selected()
        if i <= 0 or i >= len(names): return
        self.syncing = True
        for key, value in COLORS[names[i]].items(): self.color_entries[key].set_text(value)
        self.syncing = False
        self.apply_text_css()

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
            self.logo_source.set_text(str(target)); self.logo.set_filename(str(target))
        except OSError as exc: self.show_error(str(exc))

    def open_editor(self, *_):
        try: subprocess.Popen(shlex.split(self.editor.get_text().strip() or "micro") + [str(self.config_path)])
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
                cfg["modules"] = [{"type": "custom", "format": line} for line in raw.splitlines() if line.strip()]
            else:
                selected = [key for _, key in MODULES if self.checks[key].get_active()]
                if selected:
                    existing = {module_key(x): x for x in cfg.get("modules", []) if isinstance(x, dict) and module_key(x)}
                    cfg["modules"] = [existing.get(key, key) for key in selected]
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            if self.config_path.is_file(): shutil.copy2(self.config_path, self.config_path.with_name(self.config_path.name + ".bak"))
            self.config_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            self.config = cfg; self.text_edited = False; self.status.set_text(f"Saved: {self.config_path}"); self.refresh_output()
        except Exception as exc: self.show_error(str(exc))

    def show_error(self, message):
        dialog = Gtk.AlertDialog(message=APP_NAME); dialog.set_detail(str(message)); dialog.show(self.window)


def main():
    return FastfetchDesigner().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())

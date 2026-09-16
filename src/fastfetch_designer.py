#!/usr/bin/env python3
import json
import os
import re
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, Gio, GLib, Pango

APP_ID = 'io.fastfetch.Designer'
APP_NAME = 'Fastfetch Designer'
CONFIG_PATH = Path.home() / '.config' / 'fastfetch' / 'config.jsonc'
LOGO_DIR = Path.home() / '.config' / 'fastfetch' / 'logos'

MODULES = [
    ('OS', 'os'), ('Kernel', 'kernel'), ('Uptime', 'uptime'), ('Packages', 'packages'),
    ('Shell', 'shell'), ('Display', 'display'), ('DE', 'de'), ('WM', 'wm'),
    ('Theme', 'theme'), ('Icons', 'icons'), ('Terminal', 'terminal'), ('CPU', 'cpu'),
    ('GPU', 'gpu'), ('Memory', 'memory'), ('Disk', 'disk'),
]

PRESETS = {
    'Default': {'keys': '#D8DEE9', 'title': '#8FBCBB', 'output': '#D8DEE9', 'separator': '#81A1C1'},
    'Gruvbox': {'keys': '#EBDBB2', 'title': '#D79921', 'output': '#FBF1C7', 'separator': '#B8BB26'},
    'Catppuccin': {'keys': '#CDD6F4', 'title': '#89B4FA', 'output': '#CDD6F4', 'separator': '#A6E3A1'},
    'Nord': {'keys': '#D8DEE9', 'title': '#88C0D0', 'output': '#E5E9F0', 'separator': '#81A1C1'},
    'Monochrome': {'keys': '#D0D0D0', 'title': '#FFFFFF', 'output': '#B8B8B8', 'separator': '#808080'},
}


def strip_jsonc(text: str) -> str:
    out = []
    i = 0
    in_string = False
    escape = False
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ''
        if in_string:
            out.append(c)
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
            out.append(c)
            i += 1
        elif c == '/' and n == '/':
            i += 2
            while i < len(text) and text[i] not in '\r\n':
                i += 1
        elif c == '/' and n == '*':
            i += 2
            while i + 1 < len(text) and not (text[i] == '*' and text[i + 1] == '/'):
                i += 1
            i += 2
        else:
            out.append(c)
            i += 1
    cleaned = ''.join(out)
    return re.sub(r',\s*([}\]])', r'\1', cleaned)


def load_config():
    if not CONFIG_PATH.exists():
        return {
            '$schema': 'https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json',
            'logo': {'type': 'builtin', 'source': 'auto'},
            'display': {'color': {'keys': '#D8DEE9', 'title': '#8FBCBB', 'output': '#D8DEE9', 'separator': '#81A1C1'}},
            'modules': [name for _, name in MODULES],
        }
    try:
        return json.loads(strip_jsonc(CONFIG_PATH.read_text(encoding='utf-8')))
    except Exception as e:
        raise RuntimeError(f'Could not parse {CONFIG_PATH}: {e}')


class FastfetchDesigner(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect('activate', self.on_activate)
        self.config = load_config()
        self.logo_path = None
        self.module_checks = {}
        self.logo_info = Gtk.Label(label='No logo loaded')

    def on_activate(self, app):
        win = Gtk.ApplicationWindow(application=app)
        win.set_title(APP_NAME)
        win.set_default_size(1280, 780)
        win.set_size_request(980, 650)
        self.window = win
        self.apply_css()
        win.set_child(self.build_ui())
        self.populate_from_config()
        self.refresh_preview()
        win.present()

    def apply_css(self):
        css = Gtk.CssProvider()
        css.load_from_data(b'''
        window { background: #11171A; }
        .shell { background: #11171A; }
        .sidebar { background: #10161A; border-right: 1px solid #39464A; }
        .preview-shell { background: #182124; }
        .card { background: #182124; border: 1px solid #364247; border-radius: 12px; padding: 10px; }
        .muted { color: #87979D; font-size: 12px; }
        .terminal { background: #202A2D; border: 1px solid #405055; border-radius: 12px; padding: 18px; }
        .terminal-title { color: #96A7AC; font-size: 12px; }
        .terminal-text { color: #D8DEE9; }
        checkbutton { min-height: 28px; }
        entry { background: #202A2D; }
        ''' , -1)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class('shell')
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.set_margin_start(16); header.set_margin_end(16); header.set_margin_top(12); header.set_margin_bottom(10)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(); title.set_xalign(0); title.set_markup('<span size="large" weight="bold">Fastfetch Designer</span>')
        subtitle = Gtk.Label(label='Visual editor for ~/.config/fastfetch/config.jsonc'); subtitle.set_xalign(0); subtitle.add_css_class('muted')
        title_box.append(title); title_box.append(subtitle); header.append(title_box)
        spacer = Gtk.Box(); spacer.set_hexpand(True); header.append(spacer)
        refresh = Gtk.Button(label='Refresh'); refresh.connect('clicked', lambda *_: self.refresh_preview()); header.append(refresh)
        save = Gtk.Button(label='Save config'); save.add_css_class('suggested-action'); save.connect('clicked', self.save_config); header.append(save)
        root.append(header)

        paned = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL); paned.set_position(325); root.append(paned)
        sidebar = Gtk.ScrolledWindow(); sidebar.set_vexpand(True); sidebar.set_min_content_width(300)
        side_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); side_box.add_css_class('sidebar')
        side_box.set_margin_start(12); side_box.set_margin_end(12); side_box.set_margin_top(8); side_box.set_margin_bottom(12)
        sidebar.set_child(side_box)
        self.build_logo_card(side_box); self.build_appearance_card(side_box); self.build_modules_card(side_box); self.build_advanced_card(side_box)
        paned.set_start_child(sidebar)

        preview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); preview.add_css_class('preview-shell')
        preview.set_margin_start(12); preview.set_margin_end(14); preview.set_margin_top(8); preview.set_margin_bottom(12)
        label = Gtk.Label(); label.set_xalign(0); label.set_markup('<span weight="bold">Live Preview</span>'); preview.append(label)
        self.terminal = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10); self.terminal.add_css_class('terminal'); self.terminal.set_vexpand(True); preview.append(self.terminal)
        self.status = Gtk.Label(label='Ready'); self.status.set_xalign(0); self.status.add_css_class('muted'); preview.append(self.status)
        paned.set_end_child(preview)
        return root

    def section_card(self, parent, title, hint=None):
        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7); frame.add_css_class('card')
        lab = Gtk.Label(); lab.set_xalign(0); lab.set_markup(f'<span weight="bold">{title}</span>'); frame.append(lab)
        if hint:
            h = Gtk.Label(label=hint); h.set_xalign(0); h.add_css_class('muted'); h.set_wrap(True); frame.append(h)
        parent.append(frame); return frame

    def row(self, label, widget, parent):
        b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        l = Gtk.Label(label=label); l.set_xalign(0); l.set_hexpand(True); b.append(l); b.append(widget); parent.append(b)

    def spin_row(self, label, value, low, high, parent):
        spin = Gtk.SpinButton.new_with_range(low, high, 1); spin.set_value(value); spin.set_width_chars(5); self.row(label, spin, parent); return spin

    def build_logo_card(self, parent):
        card = self.section_card(parent, 'Logo', 'Pick a built-in emblem or an image file. X/Y map to left/top padding.')
        chooser = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        upload = Gtk.Button(label='Upload image'); upload.connect('clicked', self.choose_logo)
        reset = Gtk.Button(label='Reset'); reset.connect('clicked', self.reset_logo)
        chooser.append(upload); chooser.append(reset); card.append(chooser)
        self.logo_source = Gtk.ComboBoxText()
        for item in ['builtin', 'file', 'chafa', 'kitty', 'sixel']: self.logo_source.append_text(item)
        self.row('Type', self.logo_source, card)
        self.logo_entry = Gtk.Entry(); self.logo_entry.set_placeholder_text('arch or /path/to/image.png'); self.row('Source', self.logo_entry, card)
        self.spin_x = self.spin_row('X', 0, -999, 999, card); self.spin_y = self.spin_row('Y', 0, -999, 999, card)
        self.spin_w = self.spin_row('W', 48, 1, 300, card); self.spin_h = self.spin_row('H', 29, 1, 300, card); self.spin_gap = self.spin_row('Gap', 3, 0, 100, card)
        self.logo_info.set_xalign(0); self.logo_info.add_css_class('muted'); card.append(self.logo_info)
        for s in [self.spin_x, self.spin_y, self.spin_w, self.spin_h, self.spin_gap]: s.connect('value-changed', lambda *_: self.refresh_preview())
        self.logo_source.connect('changed', lambda *_: self.refresh_preview()); self.logo_entry.connect('changed', lambda *_: self.refresh_preview())

    def build_appearance_card(self, parent):
        card = self.section_card(parent, 'Appearance', 'Fastfetch supports named colors and RGB hex colors such as #EBDBB2.')
        preset = Gtk.ComboBoxText(); preset.append_text('Custom')
        for p in PRESETS: preset.append_text(p)
        self.row('Preset', preset, card); self.preset = preset; preset.connect('changed', self.apply_preset)
        for key, label, default in [('keys','Keys','#D8DEE9'), ('title','Title','#8FBCBB'), ('output','Output','#D8DEE9'), ('separator','Separator','#81A1C1')]:
            entry = Gtk.Entry(); entry.set_text(default); entry.set_width_chars(10); entry.connect('changed', lambda *_: self.refresh_preview()); setattr(self, f'color_{key}', entry); self.row(label, entry, card)
        self.bright = Gtk.CheckButton(label='Bright key/title/logo colors'); self.bright.set_active(True); self.bright.connect('toggled', lambda *_: self.refresh_preview()); card.append(self.bright)
        self.font_button = Gtk.FontDialogButton(); self.font_button.set_dialog(Gtk.FontDialog()); self.row('Preview font', self.font_button, card)
        self.font_button.connect('notify::font-desc', lambda *_: self.refresh_preview())
        hint = Gtk.Label(label='Font is preview-only. The actual terminal font is controlled by Ghostty, Kitty, foot, etc.'); hint.add_css_class('muted'); hint.set_wrap(True); hint.set_xalign(0); card.append(hint)

    def build_modules_card(self, parent):
        card = self.section_card(parent, 'Modules', 'Toggle the standard Fastfetch modules shown in the preview/config.')
        grid = Gtk.Grid(column_spacing=12, row_spacing=2)
        for i, (label, key) in enumerate(MODULES):
            check = Gtk.CheckButton(label=label); check.set_active(True); check.connect('toggled', lambda *_: self.refresh_preview()); self.module_checks[key] = check; grid.attach(check, i % 2, i // 2, 1, 1)
        card.append(grid)

    def build_advanced_card(self, parent):
        card = self.section_card(parent, 'Advanced', 'Open the generated JSONC directly when needed.')
        btn = Gtk.Button(label='Open config in editor'); btn.connect('clicked', self.open_editor); card.append(btn)
        self.editor_entry = Gtk.Entry(); self.editor_entry.set_text(os.environ.get('EDITOR', 'micro')); self.row('Editor', self.editor_entry, card)
        backup = Gtk.Label(label='Every Save creates config.jsonc.bak when an existing config is present.'); backup.set_wrap(True); backup.set_xalign(0); backup.add_css_class('muted'); card.append(backup)

    def populate_from_config(self):
        logo = self.config.get('logo') or {}
        typ = logo.get('type', 'builtin') if isinstance(logo, dict) else 'builtin'
        if typ not in ['builtin', 'file', 'chafa', 'kitty', 'sixel']: typ = 'builtin'
        self.logo_source.set_active_id(typ); self.logo_entry.set_text(str(logo.get('source', 'arch')) if isinstance(logo, dict) else 'arch')
        pad = logo.get('padding', {}) if isinstance(logo, dict) else {}
        self.spin_x.set_value(float(pad.get('left', 0))); self.spin_y.set_value(float(pad.get('top', 0))); self.spin_gap.set_value(float(pad.get('right', 3)))
        self.spin_w.set_value(float(logo.get('width', 48) or 48)); self.spin_h.set_value(float(logo.get('height', 29) or 29))
        display = self.config.get('display') or {}; color = display.get('color') or {}
        for key in ['keys','title','output','separator']: getattr(self, f'color_{key}').set_text(str(color.get(key, PRESETS['Default'][key])))
        self.bright.set_active(display.get('brightColor', True))
        mods = self.config.get('modules', []); modkeys = set()
        for item in mods:
            if isinstance(item, str): modkeys.add(item)
            elif isinstance(item, dict) and item.get('type'): modkeys.add(item['type'])
        for key, check in self.module_checks.items(): check.set_active(key in modkeys if modkeys else True)

    def apply_preset(self, combo):
        text = combo.get_active_text()
        if not text or text == 'Custom': return
        for key, value in PRESETS[text].items(): getattr(self, f'color_{key}').set_text(value)
        self.refresh_preview()

    def choose_logo(self, *_):
        dialog = Gtk.FileDialog(title='Choose Fastfetch logo image')
        f = Gtk.FileFilter(); f.set_name('Images')
        for mime in ['image/png','image/jpeg','image/webp','image/gif','image/svg+xml']: f.add_mime_type(mime)
        ff = Gio.ListStore.new(Gtk.FileFilter); ff.append(f); dialog.set_filters(ff); dialog.set_default_filter(f); dialog.open(self.window, None, self.logo_chosen)

    def logo_chosen(self, dialog, result):
        try: file = dialog.open_finish(result)
        except GLib.Error: return
        path = Path(file.get_path()); LOGO_DIR.mkdir(parents=True, exist_ok=True); target = LOGO_DIR / path.name
        try:
            if path.resolve() != target.resolve(): shutil.copy2(path, target)
            self.logo_path = target; self.logo_entry.set_text(str(target)); self.logo_source.set_active_id('kitty' if path.suffix.lower() in ['.png','.jpg','.jpeg','.webp'] else 'file'); self.logo_info.set_text(f'Copied to {target}')
        except Exception as e: self.show_error(str(e))
        self.refresh_preview()

    def reset_logo(self, *_):
        self.logo_path = None; self.logo_source.set_active_id('builtin'); self.logo_entry.set_text('arch'); self.spin_x.set_value(0); self.spin_y.set_value(0); self.spin_w.set_value(48); self.spin_h.set_value(29); self.spin_gap.set_value(3); self.logo_info.set_text('Built-in Arch logo'); self.refresh_preview()

    def selected_modules(self): return [key for _, key in MODULES if self.module_checks[key].get_active()]

    def current_ui_state(self):
        return {
            'logo_type': self.logo_source.get_active_text() or 'builtin', 'logo_source': self.logo_entry.get_text().strip() or 'arch',
            'x': int(self.spin_x.get_value()), 'y': int(self.spin_y.get_value()), 'w': int(self.spin_w.get_value()), 'h': int(self.spin_h.get_value()), 'gap': int(self.spin_gap.get_value()),
            'keys': self.color_keys.get_text().strip() or '#D8DEE9', 'title': self.color_title.get_text().strip() or '#8FBCBB', 'output': self.color_output.get_text().strip() or '#D8DEE9', 'separator': self.color_separator.get_text().strip() or '#81A1C1',
            'bright': self.bright.get_active(), 'modules': self.selected_modules(),
        }

    def make_config(self):
        cfg = deepcopy(self.config); st = self.current_ui_state()
        logo = cfg.setdefault('logo', {}); logo.clear(); logo.update({'type': st['logo_type'], 'source': st['logo_source'], 'width': st['w'], 'height': st['h'], 'padding': {'left': st['x'], 'top': st['y'], 'right': st['gap']}})
        disp = cfg.setdefault('display', {}); colors = disp.setdefault('color', {}); colors.update({'keys': st['keys'], 'title': st['title'], 'output': st['output'], 'separator': st['separator']}); disp['brightColor'] = st['bright']
        existing = {m.get('type'): m for m in cfg.get('modules', []) if isinstance(m, dict) and m.get('type')}; cfg['modules'] = [existing.get(m, m) for m in st['modules']]
        cfg.setdefault('$schema', 'https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json'); return cfg

    def save_config(self, *_):
        try:
            new_cfg = self.make_config(); CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            if CONFIG_PATH.exists(): shutil.copy2(CONFIG_PATH, CONFIG_PATH.with_suffix(CONFIG_PATH.suffix + '.bak'))
            CONFIG_PATH.write_text(json.dumps(new_cfg, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'); self.config = new_cfg; self.status.set_text(f'Saved {CONFIG_PATH}'); self.refresh_preview()
        except Exception as e: self.show_error(str(e))

    def open_editor(self, *_):
        editor = self.editor_entry.get_text().strip() or 'micro'
        if not CONFIG_PATH.exists(): self.save_config()
        try: subprocess.Popen(editor.split() + [str(CONFIG_PATH)])
        except Exception as e: self.show_error(f'Could not launch editor: {e}')

    def run_fastfetch(self):
        try:
            tmp = Path(GLib.get_tmp_dir()) / f'fastfetch-designer-{os.getpid()}.jsonc'; tmp.write_text(json.dumps(self.make_config(), indent=2, ensure_ascii=False), encoding='utf-8')
            res = subprocess.run(['fastfetch', '--config', str(tmp), '--pipe'], capture_output=True, text=True, timeout=5)
            try: tmp.unlink()
            except OSError: pass
            return res.stdout.strip() if res.returncode == 0 and res.stdout.strip() else (res.stderr.strip() or 'Fastfetch produced no output.')
        except FileNotFoundError: return 'fastfetch was not found in PATH. Install fastfetch and press Refresh.'
        except Exception as e: return f'Preview error: {e}'

    def render_preview(self, output_text):
        while self.terminal.get_first_child() is not None: self.terminal.remove(self.terminal.get_first_child())
        bar = Gtk.Label(label='●  ●  ●   Fastfetch preview'); bar.set_xalign(0); bar.add_css_class('terminal-title'); self.terminal.append(bar)
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18); body.set_vexpand(True); body.set_margin_top(16); body.set_margin_bottom(16)
        st = self.current_ui_state(); source = st['logo_source']
        if st['logo_type'] in ('kitty','sixel','chafa') and source and Path(os.path.expanduser(source)).is_file():
            pic = Gtk.Picture.new_for_filename(os.path.expanduser(source)); pic.set_can_shrink(True); pic.set_content_fit(Gtk.ContentFit.CONTAIN); pic.set_size_request(220, 260); body.append(pic)
        else:
            logo_label = Gtk.Label(label=self.builtin_logo(source)); logo_label.set_xalign(0); logo_label.set_yalign(0); logo_label.set_valign(Gtk.Align.CENTER); logo_label.add_css_class('terminal-text'); body.append(logo_label)
        text = Gtk.Label(); text.set_xalign(0); text.set_yalign(0); text.set_selectable(True); text.set_wrap(False); text.add_css_class('terminal-text'); text.set_markup(self.format_output_markup(output_text)); self.preview_font_css(text); body.append(text); self.terminal.append(body)

    def format_output_markup(self, output_text):
        import html
        st = self.current_ui_state(); lines = []
        for raw in output_text.splitlines():
            line = raw.rstrip()
            if not line: lines.append(''); continue
            m = re.match(r'^(.*?)(:\s*)(.*)$', line)
            if m:
                k, separator, value = m.groups(); lines.append(f'<span foreground="{html.escape(st["keys"])}">{html.escape(k)}</span><span foreground="{html.escape(st["separator"])}">{html.escape(separator)}</span><span foreground="{html.escape(st["output"])}">{html.escape(value)}</span>')
            else: lines.append(f'<span foreground="{html.escape(st["title"])}">{html.escape(line)}</span>')
        return '\n'.join(lines)

    def preview_font_css(self, widget):
        try: desc = self.font_button.get_font_desc()
        except Exception: desc = None
        if not desc: return
        provider = Gtk.CssProvider(); provider.load_from_data(f'.preview-font {{ font: {desc.to_string()}; }}'.encode(), -1); widget.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def builtin_logo(self, source):
        if source == 'arch': return '\n'.join(['        /\\','       /  \\','      / /\\ \\','     / /  \\ \\','    /_/    \\_\\'])
        return '\n'.join(['   █████████','  ██         ██',' ██  logo     ██','  ██         ██','   █████████'])

    def refresh_preview(self):
        if not hasattr(self, 'terminal'): return
        self.render_preview(self.run_fastfetch()); self.status.set_text('Preview updated')

    def show_error(self, message):
        dlg = Gtk.AlertDialog(message='Fastfetch Designer'); dlg.set_detail(message); dlg.show(self.window)


def main(): return FastfetchDesigner().run(sys.argv)
if __name__ == '__main__': raise SystemExit(main())

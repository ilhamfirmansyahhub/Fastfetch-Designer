# Fastfetch Designer

A lightweight native Linux GUI for editing your **existing Fastfetch setup visually**.

Open the app and your current Fastfetch configuration is loaded automatically. The **Current Fastfetch** area is the main editor: you can edit the displayed text directly, see your configured logo, move/resize it, change colors, toggle modules, and save the result without manually opening `config.jsonc`.

## Screenshot

![Fastfetch Designer preview](docs/fastfetch-designer-preview.svg)

## What you get

- Automatically loads the Fastfetch config found through the normal Fastfetch config search paths.
- Shows the **actual configured logo/image** when it can be resolved to a local file.
- **Current Fastfetch** is directly editable.
- Edit displayed text and save it as Fastfetch custom modules.
- Drag the logo in the preview to adjust its position.
- Change logo width, height, X, Y, and gap.
- Import a new PNG, JPEG, WebP, GIF, or SVG logo.
- Change Keys, Title, Output, and Separator colors.
- Presets: Default, Gruvbox, Catppuccin, Nord, Monochrome.
- Toggle common Fastfetch modules from the GUI.
- Refresh to reload the current configuration from disk.
- Save creates `config.jsonc.bak` before replacing an existing config.
- Optional button to open the real JSONC configuration in your editor.
- No Electron, no web runtime, no daemon, and no background service.
- Installs as a normal desktop application with a dedicated launcher icon.

## Current Fastfetch

The application intentionally treats **Current Fastfetch** as the important part of the UI.

On startup it:

```text
Fastfetch config search
        ↓
load current config
        ↓
run installed Fastfetch
        ↓
show current output + configured logo
        ↓
edit visually
        ↓
Save
```

The application first checks `FASTFETCH_CONFIG` / `FASTFETCH_CONFIG_PATH`, then Fastfetch's `--list-config-paths` output, and finally the normal `~/.config/fastfetch/config.jsonc` / `config.json` locations.

## Editing the displayed text

Click inside **Current Fastfetch** and edit the text directly, just like a simple text editor.

When you press **Save**, manually edited lines are stored as Fastfetch `custom` modules. This keeps the workflow simple for people who do not want to learn the Fastfetch JSONC structure.

When the text has not been manually edited, the existing module configuration is kept and the module checkboxes continue to control the standard modules.

## Logo

The configured logo is loaded automatically when its `source` points to an accessible local image.

You can also choose a new image from the GUI. Imported images are copied to:

```text
~/.config/fastfetch/assets/
```

The logo controls let you change its position and size without manually editing JSONC.

## Colors

Fastfetch Designer provides independent color fields for:

- Keys
- Title
- Output
- Separator

RGB hex values such as `#EBDBB2` are supported.

## Fonts

There is intentionally **no font selector**. Fastfetch Designer does not manage terminal fonts. Configure the font in your terminal emulator or system instead.

## Requirements

For Arch Linux / CachyOS:

```bash
sudo pacman -S --needed git fastfetch gtk4 python python-gobject
```

## Install

Clone the repository:

```bash
git clone https://github.com/ilhamfirmansyahhub/Fastfetch-Designer.git
cd Fastfetch-Designer
chmod +x install.sh
./install.sh
```

Or paste this one block:

```bash
sudo pacman -S --needed git fastfetch gtk4 python python-gobject && git clone https://github.com/ilhamfirmansyahhub/Fastfetch-Designer.git && cd Fastfetch-Designer && chmod +x install.sh && ./install.sh
```

After installation, open **Fastfetch Designer** from your normal application launcher. You do not need to open a terminal, `.desktop` file, or `config.jsonc` manually.

Run from terminal when needed:

```bash
fastfetch-designer
```

## Installed files

```text
~/.local/share/fastfetch-designer/fastfetch_designer.py
~/.local/bin/fastfetch-designer
~/.local/share/applications/fastfetch-designer.desktop
~/.local/share/icons/hicolor/scalable/apps/fastfetch-designer.svg
```

Your Fastfetch configuration remains where Fastfetch normally finds it, for example:

```text
~/.config/fastfetch/config.jsonc
```

## Uninstall

```bash
rm -rf ~/.local/share/fastfetch-designer
rm -f ~/.local/bin/fastfetch-designer
rm -f ~/.local/share/applications/fastfetch-designer.desktop
rm -f ~/.local/share/icons/hicolor/scalable/apps/fastfetch-designer.svg
```

Your Fastfetch configuration and assets are not removed.

## Design goals

Fastfetch Designer stays intentionally simple:

- Native GTK4 + Python GObject
- User-local installation
- Direct visual editing
- Current configuration loaded automatically
- Lightweight preview/editor
- Safe config backup before saving
- No unnecessary services or runtime layers

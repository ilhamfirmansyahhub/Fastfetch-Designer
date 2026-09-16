# Fasfetch Designer

A lightweight Linux GUI for customizing Fastfetch without manually editing `~/.config/fastfetch/config.jsonc`.

Fasfetch Designer is intentionally small and focused: a simple controls panel on the left and a live Fastfetch preview on the right.

## Features

### Logo / emblem
- Built-in Fastfetch logo support.
- Import PNG, JPEG, WebP, GIF, or SVG images.
- Imported images are copied to `~/.config/fastfetch/logos/`.
- Configure logo type/source, width, height, X/Y padding, and gap.

### Colors
- Keys
- Title
- Output
- Separator
- RGB hex colors such as `#EBDBB2`.
- Presets: Default, Gruvbox, Catppuccin, Nord, Monochrome.
- The default UI/preview text uses a bright, readable composition designed for dark GTK/Wayland themes.

### Modules
Toggle common modules from the GUI:
`OS`, `Kernel`, `Uptime`, `Packages`, `Shell`, `Display`, `DE`, `WM`, `Theme`, `Icons`, `Terminal`, `CPU`, `GPU`, `Memory`, and `Disk`.

### Automatic configuration loading
Fasfetch Designer asks Fastfetch for its own configuration search paths with `fastfetch --list-config-paths` and loads the first existing configuration it finds. This avoids assuming that a single hard-coded path is always the active file. Fastfetch documents this command as the way to list its config search paths. citeturn459802search2turn459802search0

The **Refresh** button reloads that configuration from disk, so changes made externally can be pulled into the GUI without restarting the application.

### Safe config editing
- Changes are previewed with a temporary Fastfetch config.
- **Save config** writes to the currently loaded config file.
- Existing configs are backed up to `config.jsonc.bak` before overwrite.
- Existing per-module object settings are preserved where possible.
- An editor button is available for direct editing when needed.

### Fonts
There is intentionally no font selector. Fastfetch controls terminal content/layout; the actual terminal font belongs to the terminal emulator or system configuration.

### Application launcher
Installation creates a normal desktop application entry called **Fasfetch Designer** and installs a dedicated scalable SVG icon. After installation, open it from your usual application launcher—no manual `.desktop` or icon setup is required.

## Requirements

For Arch Linux / CachyOS:

```bash
sudo pacman -S --needed git fastfetch gtk4 python python-gobject
```

`desktop-file-utils` is optional.

## Installation

Clone the repository:

```bash
git clone https://github.com/ilhamfirmansyahhub/Fasfetch-Designer.git
cd Fasfetch-Designer
chmod +x install.sh
./install.sh
```

Or use one copy-paste block:

```bash
sudo pacman -S --needed git fastfetch gtk4 python python-gobject && git clone https://github.com/ilhamfirmansyahhub/Fasfetch-Designer.git && cd Fasfetch-Designer && chmod +x install.sh && ./install.sh
```

Then search for **Fasfetch Designer** in your application launcher.

You can also start it from the terminal:

```bash
fastfetch-designer
```

The installer does not require `sudo` for the application itself. It installs user-local files under `~/.local/share/`, `~/.local/bin/`, `~/.local/share/applications/`, and `~/.local/share/icons/`.

## Installed files

```text
~/.local/share/fastfetch-designer/src/fastfetch_designer.py
~/.local/bin/fastfetch-designer
~/.local/share/applications/fasfetch-designer.desktop
~/.local/share/icons/hicolor/scalable/apps/fastfetch-designer.svg
```

Fastfetch config:

```text
~/.config/fastfetch/config.jsonc
```

Custom logos:

```text
~/.config/fastfetch/logos/
```

## Uninstall

```bash
rm -rf ~/.local/share/fastfetch-designer
rm -f ~/.local/bin/fastfetch-designer
rm -f ~/.local/share/applications/fasfetch-designer.desktop
rm -f ~/.local/share/icons/hicolor/scalable/apps/fastfetch-designer.svg
```

Your Fastfetch config and custom logos are not removed.

## Design goals

- Lightweight GTK4 + Python GObject application.
- No daemon.
- No background service.
- No database.
- No Electron/web wrapper.
- User-local installation.
- Backup before overwriting Fastfetch config.
- Focused on Fastfetch customization, not terminal font management.

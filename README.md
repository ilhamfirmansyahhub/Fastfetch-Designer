# Fastfetch Designer

A lightweight graphical editor for [Fastfetch](https://github.com/fastfetch-cli/fastfetch) on Linux.

Fastfetch Designer is built for users who want to customize their Fastfetch without repeatedly opening and editing `~/.config/fastfetch/config.jsonc` by hand.

The interface follows a simple layout: controls on the left and a live Fastfetch-style preview on the right.

## What you get

After installation, you get a normal desktop application called **Fastfetch Designer**. An application launcher entry is installed, so you can open it directly from your desktop environment or application launcher without typing commands or manually editing the Fastfetch configuration.

The application does not run as a daemon and does not add a background service. It is a small GUI editor that writes your Fastfetch configuration when you press **Save config**.

## Features

### Logo / emblem

- Choose a built-in Fastfetch logo source.
- Import a custom PNG, JPEG, WebP, GIF, or SVG image.
- Imported images are copied into:
  `~/.config/fastfetch/logos/`
- Configure logo type/source.
- Adjust logo width and height.
- Adjust X/Y padding and the gap between logo and text.

### Full color controls

Change the main Fastfetch text colors independently:

- Keys
- Title
- Output
- Separator

RGB hex colors such as `#EBDBB2` are supported.

Built-in presets:

- Default
- Gruvbox
- Catppuccin
- Nord
- Monochrome

### Modules

Enable or disable common Fastfetch modules from the GUI:

- OS
- Kernel
- Uptime
- Packages
- Shell
- Display
- DE
- WM
- Theme
- Icons
- Terminal
- CPU
- GPU
- Memory
- Disk

### Live preview

The preview uses the installed `fastfetch` binary with a temporary configuration, so you can see changes without overwriting your real configuration first.

### Config management

- Save directly to `~/.config/fastfetch/config.jsonc`.
- Existing configurations are backed up as `config.jsonc.bak` before being overwritten.
- Open the generated config in your preferred editor (`$EDITOR`, with `micro` as the default).
- Existing per-module object settings are preserved where possible when modules are toggled.

## Fonts

Fastfetch itself controls terminal content and layout; the actual terminal font is normally controlled by your terminal emulator such as Ghostty, Kitty, or foot.

For that reason, **Preview font** changes the font used by the Fastfetch Designer preview only. It does not write a fake font setting into Fastfetch's `config.jsonc`.

## Requirements

This project targets Linux systems with GTK4 and Python GObject. On Arch Linux and CachyOS, install the dependencies with:

```bash
sudo pacman -S --needed fastfetch gtk4 python python-gobject
```

Optional, for refreshing the desktop application database immediately after installation:

```bash
sudo pacman -S --needed desktop-file-utils
```

`desktop-file-utils` is optional because most desktop environments will discover the `.desktop` entry without it.

## Easy installation

Clone the repository:

```bash
git clone https://github.com/ilhamfirmansyahhub/simple-fastfetch-manager-full-colors.git
cd simple-fastfetch-manager-full-colors
```

Install the dependencies:

```bash
sudo pacman -S --needed fastfetch gtk4 python python-gobject
```

Run the installer:

```bash
chmod +x install.sh
./install.sh
```

Then open **Fastfetch Designer** from your application launcher.

You can also start it directly from the terminal:

```bash
fastfetch-designer
```

No `sudo` is required for the project installer. The application is installed for the current user under `~/.local/share/`, `~/.local/bin/`, and `~/.local/share/applications/`.

## One-copy-paste installation

For a fresh Arch/CachyOS system, the following can be pasted as one block:

```bash
sudo pacman -S --needed git fastfetch gtk4 python python-gobject && \
git clone https://github.com/ilhamfirmansyahhub/simple-fastfetch-manager-full-colors.git && \
cd simple-fastfetch-manager-full-colors && \
chmod +x install.sh && \
./install.sh
```

After that, search for **Fastfetch Designer** in your normal application launcher.

## Where files are installed

The installer uses user-local paths:

```text
~/.local/share/fastfetch-designer/src/fastfetch_designer.py
~/.local/bin/fastfetch-designer
~/.local/share/applications/fastfetch-designer.desktop
```

Your Fastfetch configuration is not moved:

```text
~/.config/fastfetch/config.jsonc
```

Custom imported logo images are stored in:

```text
~/.config/fastfetch/logos/
```

## Uninstall

Remove the installed application files with:

```bash
rm -rf ~/.local/share/fastfetch-designer
rm -f ~/.local/bin/fastfetch-designer
rm -f ~/.local/share/applications/fastfetch-designer.desktop
```

This does **not** remove your Fastfetch configuration or your custom logos.

## Design goals

Fastfetch Designer intentionally stays small and focused:

- No daemon
- No background service
- No database
- No Electron
- No web application wrapper
- No unnecessary configuration framework
- User-local installation
- Backup before overwriting Fastfetch config

The goal is to make Fastfetch customization approachable while keeping the tool lightweight and simple.

## License

See the repository for the current license and project history.

# Fasfetch Designer

A lightweight graphical editor for [Fastfetch](https://github.com/fastfetch-cli/fastfetch) on Linux.

Fasfetch Designer is built for users who want to customize their Fastfetch without repeatedly opening and editing `~/.config/fastfetch/config.jsonc` by hand.

The interface follows a simple layout: controls on the left and a live Fastfetch-style preview on the right.

## What you get

After installation, you get a normal desktop application called **Fasfetch Designer** with its own application icon. A `.desktop` launcher entry and a scalable SVG icon are installed, so you can open it directly from your desktop environment or application launcher without typing commands or manually editing the Fastfetch configuration.

The application does not run as a daemon and does not add a background service. It is a small GUI editor that writes your Fastfetch configuration when you press **Save config**.

## Features

### Logo / emblem

- Choose a built-in Fastfetch logo source.
- Import a custom PNG, JPEG, WebP, GIF, or SVG image.
- Imported images are copied into `~/.config/fastfetch/logos/`.
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

## Application icon

Fasfetch Designer includes a dedicated launcher icon matching the project's terminal/customization theme. The icon is installed as a scalable SVG at:

```text
~/.local/share/icons/hicolor/scalable/apps/fastfetch-designer.svg
```

The desktop entry points to this icon, so the application appears with its proper icon in application menus and launchers rather than using a generic terminal icon.

## Fonts

Fastfetch does not manage the actual terminal font. Font selection is handled by the user's terminal emulator or desktop/system font settings, such as Ghostty, Kitty, foot, or the system font configuration.

Fasfetch Designer intentionally does **not** include a font selector. This keeps the application focused on Fastfetch configuration and avoids duplicating settings that belong to the terminal or system.

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
git clone https://github.com/ilhamfirmansyahhub/Fasfetch-Designer.git
cd Fasfetch-Designer
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

Then open **Fasfetch Designer** from your application launcher. It should have the project's custom icon.

You can also start it directly from the terminal:

```bash
fastfetch-designer
```

No `sudo` is required for the project installer. The application is installed for the current user under `~/.local/share/`, `~/.local/bin/`, `~/.local/share/applications/`, and `~/.local/share/icons/`.

## One-copy-paste installation

For a fresh Arch/CachyOS system, the following can be pasted as one block:

```bash
sudo pacman -S --needed git fastfetch gtk4 python python-gobject && \
git clone https://github.com/ilhamfirmansyahhub/Fasfetch-Designer.git && \
cd Fasfetch-Designer && \
chmod +x install.sh && \
./install.sh
```

After that, search for **Fasfetch Designer** in your normal application launcher. No manual `.desktop` file or icon setup is required.

## Where files are installed

The installer uses user-local paths:

```text
~/.local/share/fastfetch-designer/src/fastfetch_designer.py
~/.local/bin/fastfetch-designer
~/.local/share/applications/fastfetch-designer.desktop
~/.local/share/icons/hicolor/scalable/apps/fastfetch-designer.svg
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
rm -f ~/.local/share/icons/hicolor/scalable/apps/fastfetch-designer.svg
```

This does **not** remove your Fastfetch configuration or your custom logos.

## Design goals

Fasfetch Designer intentionally stays small and focused:

- No daemon
- No background service
- No database
- No Electron
- No web application wrapper
- No unnecessary configuration framework
- User-local installation
- Backup before overwriting Fastfetch config
- Dedicated lightweight SVG launcher icon
- No terminal font management

The goal is to make Fastfetch customization approachable while keeping the tool lightweight and simple.

## License

See the repository for the current license and project history.

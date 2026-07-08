# Tempus GNOME Shell widget

A panel indicator that mirrors the Tempus timer: a session-coloured dot with a
live `MM:SS` countdown in the top bar, plus play/pause, reset, skip and session
switching. The dot takes the colour of the running session (red Focus, green
short break, blue long break, purple custom); it hollows out when idle and greys
out when Tempus is closed — clicking it launches the app.

It talks to the running app over D-Bus, so it stays in sync while Tempus is open.

Requires Tempus **0.6+** (older builds don't export the D-Bus interface) and
GNOME Shell 45–50.

## Install

The easiest way, once it's published, is one click from
[extensions.gnome.org](https://extensions.gnome.org). To install straight from
this repo instead:

Symlink (or copy) this folder into the extensions directory using the UUID as
the name:

```bash
ln -s "$PWD/shell-extension" \
  ~/.local/share/gnome-shell/extensions/tempus@emalica.github.io
```

Then reload GNOME Shell so it picks up the new extension:

- **Wayland:** log out and back in (the shell can't hot-load new extensions).
- **X11:** press `Alt+F2`, type `r`, Enter.

Enable it:

```bash
gnome-extensions enable tempus@emalica.github.io
```

or flip it on in the **Extensions** app.

## Use

Open Tempus. The coloured dot and countdown show up in the panel. Click the
indicator for the controls. Close Tempus and the indicator greys out — clicking
it (or "Open Tempus") launches the app again.

## Uninstall

```bash
gnome-extensions disable tempus@emalica.github.io
rm ~/.local/share/gnome-shell/extensions/tempus@emalica.github.io
```

## How it works

The app owns `io.github.EmaLica.Tempus` on the session bus and exports an object
at `/io/github/EmaLica/Tempus/Timer` (interface `io.github.EmaLica.Tempus.Timer`)
with the timer state as properties and `Toggle`/`Reset`/`Skip`/`SetSessionType`/
`Present` methods. The extension watches the bus name, proxies that object and
subscribes to `PropertiesChanged` for live updates.

Poke it by hand to see the contract:

```bash
gdbus introspect --session --dest io.github.EmaLica.Tempus \
  --object-path /io/github/EmaLica/Tempus/Timer
```

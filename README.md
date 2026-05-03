# Tempus

A focused Pomodoro timer for GNOME, built with GTK4 and libadwaita.

## Features

- **Four session types** — Focus, Short Break, Long Break, Custom — each with independently configurable durations
- **Auto-cycle** — Tempus suggests the right break after each focus session and resets automatically after a long break
- **Session dots** — visual indicator showing progress through the current Pomodoro cycle
- **Todo list** — add and check off tasks in-app; load from or export to a Markdown file
- **Desktop notifications** when a session ends
- **Preferences** — tweak every timer duration and the cycle length without touching a config file

## Running locally (development)

### Requirements

- Python ≥ 3.11
- GTK4
- libadwaita ≥ 1.4
- `python3-gobject` / `pygobject`
- `glib-compile-schemas` (part of `glib2-devel` / `libglib2.0-dev-bin`)

On Fedora:
```bash
sudo dnf install python3-gobject gtk4 libadwaita glib2-devel
```

### Run

```bash
chmod +x run.sh
./run.sh
```

`run.sh` compiles the GSettings schema into `data/` and sets `GSETTINGS_SCHEMA_DIR` so the app can find it without a system install.

## Todo Markdown format

Tempus reads and writes standard GFM task-list syntax:

```markdown
# Todo

- [ ] Write the report
- [x] Review the PR
- [ ] Fix bug #42
```

Plain `- item` lines (without a checkbox) are also imported as uncompleted tasks.

## Flatpak / Flathub

See [`flatpak/io.github.EmaLica.Tempus.yml`](flatpak/io.github.EmaLica.Tempus.yml) for the manifest.

```bash
flatpak-builder --user --install --force-clean build-dir flatpak/io.github.EmaLica.Tempus.yml
flatpak run io.github.EmaLica.Tempus
```

## License

GPL-3.0-or-later

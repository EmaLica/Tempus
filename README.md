<div align="center">

<img src="docs/logo.png" alt="Tempus logo" width="128"/>

# Tempus

**A Pomodoro timer for GNOME that stays out of your way.**

Focus in clean 25 minute blocks, tag what you're working on, and see exactly where your hours go. Native GTK4 and libadwaita, no clutter, no settings you'll never touch.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![GNOME](https://img.shields.io/badge/GNOME-GTK4%20%2B%20Adwaita-4A86CF)](https://www.gnome.org/)

<img src="docs/screenshot-tasks.png?v=2" alt="Focus session with todo list" width="440"/>
<img src="docs/screenshot-stats.png?v=2" alt="Focus time broken down by subject" width="440"/>

</div>

---

## Features

- **Four session types.** Focus, Short Break, Long Break and Custom, each with a duration you can change on the fly.
- **A ring that shows where you are.** The progress ring is colour-coded per session type, with dots underneath counting the focus sessions in your current cycle.
- **Auto-cycle.** Finish a focus block and Tempus lines up the right break and advances on its own.
- **Todo list that sticks around.** Add tasks inline or import them from Markdown, export them back when you're done. Standard GFM checkboxes, nothing proprietary.
- **Subjects.** Tag any task with a subject like Thesis, Coursework or Reading, each with its own colour shown as a dot beside the task. Add them on the fly or manage them in Preferences.
- **Per-task pomodoro count.** Every task keeps a running tally of the focus sessions you've poured into it.
- **History that actually adds up.** Flip between Today, Week, Month and Semester. Today breaks down by task, longer ranges group your time by subject in matching colours so you can see exactly where the hours went.
- **Semester view.** Defaults to the last six months, or pin a fixed start and end date if your term has real boundaries.
- **Focus mode.** Silences GNOME notifications while a session runs and restores them the moment you stop.
- **Live countdown in the window title.** Glance at the taskbar and read `12:34 · Focus` without switching back to the app.
- **Sound alerts with volume control.** A chime when a session starts and ends. Mute the start sound if it gets on your nerves.
- **Desktop notifications.** Pinged the moment a session ends, even with the window minimised.
- **No restart, ever.** Change any duration or the cycle length in Preferences and it applies live.

<div align="center">
<img src="docs/screenshot-preferences.png?v=2" alt="Preferences" width="440"/>
<img src="docs/screenshot-subjects.png?v=2" alt="Subjects with custom colours" width="440"/>
</div>

---

## Installation

### Flathub *(coming soon)*

```bash
flatpak install flathub io.github.EmaLica.Tempus
flatpak run io.github.EmaLica.Tempus
```

---

### Build from source

The quickest way to run Tempus without packaging it.

#### Requirements

<details>
<summary><strong>Fedora 40 / 41 / 42 / 44</strong></summary>

```bash
sudo dnf install python3-gobject gtk4 libadwaita glib2-devel
```

</details>

<details>
<summary><strong>Ubuntu / Debian / Linux Mint</strong></summary>

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 \
                 gir1.2-adw-1 libglib2.0-dev
```

</details>

<details>
<summary><strong>Arch Linux / Manjaro</strong></summary>

```bash
sudo pacman -S python-gobject gtk4 libadwaita glib2
```

</details>

#### Run

```bash
git clone https://github.com/EmaLica/Tempus
cd Tempus
chmod +x run.sh
./run.sh
```

`run.sh` compiles the GSettings schema locally and launches the app directly — no system install needed.

---

### Build and install as a local Flatpak

Use this if you want to test Tempus exactly as it will appear on Flathub, or if you want a proper desktop entry and app icon without touching your system Python.

#### Step 1 — Install the build tools

<details>
<summary><strong>Fedora 40 / 41 / 42 / 44</strong></summary>

```bash
sudo dnf install flatpak flatpak-builder
```

</details>

<details>
<summary><strong>Ubuntu / Debian</strong></summary>

```bash
sudo apt install flatpak flatpak-builder
```

</details>

<details>
<summary><strong>Arch Linux</strong></summary>

```bash
sudo pacman -S flatpak flatpak-builder
```

</details>

#### Step 2 — Add Flathub and install the GNOME runtime

This only needs to be done once per machine.

```bash
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//48 org.gnome.Sdk//48
```

> **Note:** if `48` is not yet available on your system, try `47` or run
> `flatpak remote-ls flathub | grep org.gnome.Platform` to see which versions are listed.

#### Step 3 — Clone the repository

```bash
git clone https://github.com/EmaLica/Tempus
cd Tempus
```

#### Step 4 — Build and install

```bash
flatpak-builder --user --install --force-clean build-dir flatpak/io.github.EmaLica.Tempus.yml
```

What each flag does:

| Flag | Meaning |
|---|---|
| `--user` | Installs only for your user, no `sudo` needed |
| `--install` | Installs the result right after building |
| `--force-clean` | Wipes `build-dir/` before building, avoids stale artefacts |

The first build downloads the GNOME SDK modules and can take a few minutes. Subsequent builds are cached and much faster.

#### Step 5 — Run

```bash
flatpak run io.github.EmaLica.Tempus
```

Tempus will also appear in GNOME Shell's application grid after installation.

#### Uninstall

```bash
flatpak uninstall io.github.EmaLica.Tempus
```

---

## Todo list — Markdown format

Tempus imports and exports the standard GFM task-list syntax:

```markdown
- [ ] Write the report
- [x] Review the PR
- [ ] Fix bug #42
```

Plain `- item` lines without a checkbox are imported as uncompleted tasks.

---

## Contributing

Bug reports and pull requests are welcome on the [issue tracker](https://github.com/EmaLica/Tempus/issues).

## License

Tempus is released under the [GNU General Public License v3.0](LICENSE).

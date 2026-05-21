<div align="center">

# Tempus

**A focused Pomodoro timer for GNOME**

Built with GTK4 and libadwaita. Stays out of your way while you work.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![GNOME](https://img.shields.io/badge/GNOME-GTK4%20%2B%20Adwaita-4A86CF)](https://www.gnome.org/)

<!-- screenshot placeholder — add one before submitting to Flathub -->
<!-- ![Tempus screenshot](docs/screenshot.png) -->

</div>

---

## Features

- **Four session types** — Focus, Short Break, Long Break, and Custom, each with its own configurable duration
- **Circular progress ring** — colour-coded by session type so you can tell at a glance where you are
- **Auto-cycle** — after each focus session Tempus suggests the right break and advances automatically
- **Session dots** — shows how many focus sessions you have completed in the current cycle
- **Todo list** — add tasks inline or load them from a Markdown file; export back to Markdown when you're done
- **Desktop notifications** — notified the moment a session ends, even if the window is minimised
- **Preferences** — change every duration and the cycle length live, no restart needed

## Installation

### Flathub *(coming soon)*

```bash
flatpak install flathub io.github.EmaLica.Tempus
flatpak run io.github.EmaLica.Tempus
```

### Build from source

**Requirements** (Fedora):
```bash
sudo dnf install python3-gobject gtk4 libadwaita glib2-devel
```

**Run without installing:**
```bash
git clone https://github.com/EmaLica/Tempus
cd Tempus
chmod +x run.sh && ./run.sh
```

`run.sh` compiles the GSettings schema locally and launches the app directly — no system install needed for development.

**Build as Flatpak locally:**
```bash
flatpak install flathub org.gnome.Platform//47 org.gnome.Sdk//47
flatpak-builder --user --install --force-clean build-dir flatpak/io.github.EmaLica.Tempus.yml
flatpak run io.github.EmaLica.Tempus
```

## Todo list — Markdown format

Tempus imports and exports the standard GFM task-list syntax:

```markdown
- [ ] Write the report
- [x] Review the PR
- [ ] Fix bug #42
```

Plain `- item` lines without a checkbox are imported as uncompleted tasks.

## Contributing

Bug reports and pull requests are welcome on the [issue tracker](https://github.com/EmaLica/Tempus/issues).

## License

Tempus is released under the [GNU General Public License v3.0](LICENSE).

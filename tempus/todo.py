import re
import uuid
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject, GLib

from . import storage


class TodoItem(GObject.Object):
    __gtype_name__ = "TempusTodoItem"

    def __init__(self, text: str, done: bool = False,
                 item_id: str | None = None, pomodoros: int = 0,
                 estimate: int = 0):
        super().__init__()
        self.id = item_id or str(uuid.uuid4())
        self.text = text
        self.done = done
        self.pomodoros = pomodoros
        self.estimate = estimate


class TodoPanel(Gtk.Box):
    __gtype_name__ = "TempusTodoPanel"

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.items: list[TodoItem] = []
        self._active_id: str | None = None
        self._active_row: Adw.ActionRow | None = None
        self._badge_labels: dict[str, Gtk.Label] = {}
        self._build_ui()
        self._load_saved()

    def _load_saved(self) -> None:
        raw = storage.load_tasks()
        for r in raw:
            item = TodoItem(
                text=r.get("text", ""),
                done=r.get("done", False),
                item_id=r.get("id"),
                pomodoros=r.get("pomodoros", 0),
                estimate=r.get("estimate", 0),
            )
            self.add_item(item)

    def _save(self) -> None:
        storage.save_tasks([
            {
                "id": it.id,
                "text": it.text,
                "done": it.done,
                "pomodoros": it.pomodoros,
                "estimate": it.estimate,
            }
            for it in self.items
        ])

    def get_active_id(self) -> str | None:
        return self._active_id

    def get_active_item(self):
        if self._active_id is None:
            return None
        for item in self.items:
            if item.id == self._active_id:
                return item
        return None

    def set_active(self, item_id: str | None) -> None:
        if self._active_row is not None:
            self._active_row.remove_css_class("accent")
            self._active_row = None
        self._active_id = item_id

    def add_pomodoro(self, task_id: str) -> None:
        for item in self.items:
            if item.id == task_id:
                item.pomodoros += 1
                label = self._badge_labels.get(task_id)
                if label:
                    label.set_label(f"● {item.pomodoros}")
                    label.set_visible(True)
                self._save()
                return
        print(f"[tempus] add_pomodoro: task {task_id!r} not found, session not attributed")

    def _build_ui(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        header.set_margin_start(12)
        header.set_margin_end(8)
        header.set_margin_top(8)
        header.set_margin_bottom(8)

        title = Gtk.Label(label="Todo")
        title.add_css_class("heading")
        title.set_hexpand(True)
        title.set_halign(Gtk.Align.START)
        header.append(title)

        load_btn = Gtk.Button(icon_name="document-open-symbolic")
        load_btn.add_css_class("flat")
        load_btn.set_tooltip_text("Load from Markdown file")
        load_btn.connect("clicked", self._on_load)
        header.append(load_btn)

        save_btn = Gtk.Button(icon_name="document-save-symbolic")
        save_btn.add_css_class("flat")
        save_btn.set_tooltip_text("Export as Markdown file")
        save_btn.connect("clicked", self._on_save)
        header.append(save_btn)

        self.append(header)
        self.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        list_wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        list_wrapper.set_margin_start(12)
        list_wrapper.set_margin_end(12)
        list_wrapper.set_margin_top(8)
        list_wrapper.set_margin_bottom(8)

        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)

        placeholder = Gtk.Label(label="No tasks yet — add one below")
        placeholder.add_css_class("dim-label")
        placeholder.set_margin_top(16)
        placeholder.set_margin_bottom(16)
        self.list_box.set_placeholder(placeholder)

        list_wrapper.append(self.list_box)
        scroll.set_child(list_wrapper)
        self.append(scroll)

        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        entry_box.set_margin_start(12)
        entry_box.set_margin_end(12)
        entry_box.set_margin_top(8)
        entry_box.set_margin_bottom(8)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("New task…")
        self.entry.set_hexpand(True)
        self.entry.connect("activate", self._on_add)

        add_btn = Gtk.Button(label="Add")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_add)

        entry_box.append(self.entry)
        entry_box.append(add_btn)
        self.append(entry_box)

    def add_item(self, item: TodoItem):
        self.items.append(item)
        self.list_box.append(self._build_row(item))

    def _build_row(self, item: TodoItem) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.set_title(GLib.markup_escape_text(item.text))
        if item.done:
            row.add_css_class("dim-label")

        check = Gtk.CheckButton()
        check.set_active(item.done)
        check.set_valign(Gtk.Align.CENTER)
        check.connect("toggled", self._on_toggle, item, row)
        row.add_prefix(check)

        badge = Gtk.Label()
        badge.add_css_class("caption")
        badge.add_css_class("accent")
        badge.set_valign(Gtk.Align.CENTER)
        badge.set_margin_end(4)
        if item.pomodoros > 0:
            badge.set_label(f"● {item.pomodoros}")
            badge.set_visible(True)
        else:
            badge.set_label("")
            badge.set_visible(False)
        self._badge_labels[item.id] = badge
        row.add_suffix(badge)

        del_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.add_css_class("flat")
        del_btn.set_valign(Gtk.Align.CENTER)
        del_btn.connect("clicked", self._on_delete, item, row)
        row.add_suffix(del_btn)

        row.set_activatable(True)
        row.connect("activated", self._on_row_activated, item)

        return row

    def _on_row_activated(self, row: Adw.ActionRow, item: TodoItem) -> None:
        if self._active_row is not None:
            self._active_row.remove_css_class("accent")

        if self._active_id == item.id:
            self._active_id = None
            self._active_row = None
        else:
            self._active_id = item.id
            self._active_row = row
            row.add_css_class("accent")

    def _clear(self):
        self.items.clear()
        self._active_id = None
        self._badge_labels.clear()
        child = self.list_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.list_box.remove(child)
            child = nxt

    def _on_add(self, *_):
        text = self.entry.get_text().strip()
        if text:
            self.add_item(TodoItem(text))
            self.entry.set_text("")
            self._save()

    def _on_toggle(self, check: Gtk.CheckButton, item: TodoItem, row: Adw.ActionRow):
        item.done = check.get_active()
        if item.done:
            row.add_css_class("dim-label")
        else:
            row.remove_css_class("dim-label")
        self._save()

    def _on_delete(self, _btn, item: TodoItem, row: Adw.ActionRow):
        if self._active_id == item.id:
            self._active_id = None
        self._badge_labels.pop(item.id, None)
        self.items.remove(item)
        self.list_box.remove(row)
        self._save()

    def load_from_markdown(self, path: str):
        try:
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
        except OSError as exc:
            self._show_error(f"Could not open file:\n{exc}")
            return

        self._clear()
        for line in content.splitlines():
            line = line.strip()
            if m := re.match(r"^- \[( |x|X)\] (.+)$", line):
                done = m.group(1).lower() == "x"
                self.add_item(TodoItem(m.group(2).strip(), done))
            elif m := re.match(r"^[-*+] (.+)$", line):
                self.add_item(TodoItem(m.group(1).strip()))
        self._save()

    def to_markdown(self) -> str:
        lines = ["# Todo", ""]
        for item in self.items:
            mark = "x" if item.done else " "
            lines.append(f"- [{mark}] {item.text}")
        return "\n".join(lines) + "\n"

    def _on_load(self, _btn):
        dialog = Gtk.FileDialog()
        dialog.set_title("Load Todo from Markdown")
        f = Gtk.FileFilter()
        f.set_name("Markdown files (*.md)")
        f.add_pattern("*.md")
        f.add_pattern("*.markdown")
        store = Gio.ListStore.new(Gtk.FileFilter)
        store.append(f)
        dialog.set_filters(store)
        dialog.open(self.get_root(), None, self._on_load_done)

    def _on_load_done(self, dialog: Gtk.FileDialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.load_from_markdown(file.get_path())
        except Exception:
            pass

    def _on_save(self, _btn):
        dialog = Gtk.FileDialog()
        dialog.set_title("Save Todo as Markdown")
        dialog.set_initial_name("todo.md")
        dialog.save(self.get_root(), None, self._on_save_done)

    def _on_save_done(self, dialog: Gtk.FileDialog, result):
        try:
            file = dialog.save_finish(result)
            if file:
                with open(file.get_path(), "w", encoding="utf-8") as fh:
                    fh.write(self.to_markdown())
        except Exception:
            pass

    def _show_error(self, message: str):
        dlg = Adw.AlertDialog()
        dlg.set_heading("Error")
        dlg.set_body(message)
        dlg.add_response("ok", "OK")
        dlg.present(self.get_root())

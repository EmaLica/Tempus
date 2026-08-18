"""Parsing dei file Markdown importati nella todo list."""

import os
import re

CHECKBOX_RE = re.compile(r"^- \[( |x|X)\] (.+)$")
BULLET_RE = re.compile(r"^[-*+] (.+)$")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$")
PREFIX_RE = re.compile(r"^\[\s*(\d+)\s*🍅\s*([^\]]*?)\s*\]\s*(.*)$")

WAVES = ("alpha", "beta", "gamma")
NOTE_INDENT = "  "


def parse_prefix(text: str) -> tuple[str, int, str | None]:
    """`[3🍅 beta] Fare X` -> (`Fare X`, 3, `beta`)."""
    m = PREFIX_RE.match(text)
    if not m:
        return text, 0, None
    wave = m.group(2).lower() or None
    if wave not in WAVES:
        wave = None
    title = m.group(3).strip()
    return (title or text), int(m.group(1)), wave


def _tokens(s: str) -> list[str]:
    return re.sub(r"\W+", " ", s.lower(), flags=re.UNICODE).split()


def match_subject(heading: str, subjects) -> str | None:
    """Cerca il nome di una materia esistente dentro il testo dell'header.

    Match su sequenza di token contigui, non su substring: "Archi I" non deve
    agganciarsi a una parola qualsiasi che contiene "archi".
    """
    words = _tokens(heading)
    for name in subjects:
        needle = _tokens(name)
        if not needle:
            continue
        for i in range(len(words) - len(needle) + 1):
            if words[i:i + len(needle)] == needle:
                return name
    return None


def parse(content: str, subjects=()) -> list[dict]:
    """Estrae i task dal Markdown, ereditando la materia dall'header corrente.

    Le righe indentate che seguono un task ne diventano la nota, così il titolo
    resta corto e il dettaglio finisce nel sottotitolo invece che nella riga.
    """
    tasks = []
    heading_subject = None
    notes: list[str] = []
    open_note = False

    def flush():
        nonlocal open_note
        if tasks and notes:
            tasks[-1]["note"] = " ".join(notes)
        notes.clear()
        open_note = False

    for i, raw in enumerate(content.splitlines()):
        line = raw.strip()
        indented = raw[:1].isspace()

        if open_note and indented and line and not CHECKBOX_RE.match(line):
            notes.append(line.lstrip("-*+ \t"))
            continue

        flush()

        if m := HEADING_RE.match(line):
            heading_subject = match_subject(m.group(1), subjects)
            continue

        line_no = None
        if m := CHECKBOX_RE.match(line):
            done = m.group(1).lower() == "x"
            body = m.group(2).strip()
            line_no = i
        elif not indented and (m := BULLET_RE.match(line)):
            done = False
            body = m.group(1).strip()
        else:
            continue

        text, estimate, wave = parse_prefix(body)
        # sotto un header generico (tipo "Extra") la materia può stare nel task stesso
        subject = heading_subject or match_subject(text, subjects)
        tasks.append({
            "text": text,
            "done": done,
            "estimate": estimate,
            "wave": wave,
            "subject": subject,
            "note": "",
            "line": line_no,
        })
        open_note = True

    flush()
    return tasks


def format_prefix(text: str, estimate: int, wave: str | None) -> str:
    if not estimate:
        return text
    inner = f"{estimate}🍅 {wave}" if wave else f"{estimate}🍅"
    return f"[{inner}] {text}"


def format_task(text: str, done: bool, estimate: int,
                wave: str | None, note: str = "") -> list[str]:
    mark = "x" if done else " "
    lines = [f"- [{mark}] {format_prefix(text, estimate, wave)}"]
    if note:
        lines.append(NOTE_INDENT + note)
    return lines


def _checkbox_body(raw: str) -> str | None:
    m = CHECKBOX_RE.match(raw.strip())
    return m.group(2).strip() if m else None


def _find_checkbox(lines: list[str], body: str) -> int | None:
    for i, raw in enumerate(lines):
        if _checkbox_body(raw) == body:
            return i
    return None


def toggle_done_in_file(path: str, line: int | None, done: bool, text: str,
                        estimate: int, wave: str | None) -> bool:
    """Rispecchia lo stato done nella riga del file sorgente. True se riuscito.

    L'indice di riga può essere disallineato se il file è cambiato dopo
    l'import: in quel caso si ricerca la riga per contenuto.
    """
    try:
        content = open(path, encoding="utf-8").read()
    except OSError:
        return False

    lines = content.splitlines()
    body = format_prefix(text, estimate, wave)

    idx = line if line is not None and 0 <= line < len(lines) else None
    if idx is None or _checkbox_body(lines[idx]) != body:
        idx = _find_checkbox(lines, body)
    if idx is None:
        return False

    indent = lines[idx][:len(lines[idx]) - len(lines[idx].lstrip())]
    mark = "x" if done else " "
    lines[idx] = f"{indent}- [{mark}] {body}"

    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + ("\n" if content.endswith("\n") else ""))
    os.replace(tmp, path)
    return True

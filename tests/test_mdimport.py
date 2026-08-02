from tempus import mdimport


def test_parse_prefix_reads_pomodoros_and_wave():
    assert mdimport.parse_prefix("[3🍅 beta] Fare X") == ("Fare X", 3, "beta")


def test_parse_prefix_without_wave():
    assert mdimport.parse_prefix("[2🍅] Fare X") == ("Fare X", 2, None)


def test_parse_prefix_ignores_unknown_wave():
    assert mdimport.parse_prefix("[1🍅 delta] Fare X") == ("Fare X", 1, None)


def test_parse_prefix_leaves_plain_text_alone():
    assert mdimport.parse_prefix("Fare X") == ("Fare X", 0, None)


def test_parse_prefix_keeps_text_when_only_prefix():
    text, est, _ = mdimport.parse_prefix("[2🍅 alpha]")
    assert text == "[2🍅 alpha]"
    assert est == 2


def test_match_subject_finds_name_in_heading():
    subjects = ["LFA", "Mat. Continuo"]
    assert mdimport.match_subject("📐 Mat. Continuo — successioni", subjects) == "Mat. Continuo"


def test_match_subject_ignores_headings_without_a_subject():
    assert mdimport.match_subject("➕ Extra (se hai 7-8h)", ["LFA"]) is None


def test_match_subject_needs_whole_words():
    assert mdimport.match_subject("Archivio dei temi", ["Archi I"]) is None


def test_parse_inherits_subject_from_heading():
    md = """# Giorno 1

## 📐 Mat. Continuo — logica
- [ ] [2🍅 alpha] Induzione
- [x] [1🍅 beta] Binomiale

## 🔧 Programmazione — puntatori
- [ ] [3🍅 beta] Lezione 11
"""
    tasks = mdimport.parse(md, ["Mat. Continuo", "Programmazione"])
    assert [t["subject"] for t in tasks] == ["Mat. Continuo", "Mat. Continuo", "Programmazione"]
    assert [t["estimate"] for t in tasks] == [2, 1, 3]
    assert [t["done"] for t in tasks] == [False, True, False]
    assert tasks[0]["text"] == "Induzione"


def test_parse_resets_subject_on_unmatched_heading():
    md = """## LFA
- [ ] [1🍅] Automi

## ➕ Extra
- [ ] [2🍅] Ripasso
"""
    tasks = mdimport.parse(md, ["LFA"])
    assert tasks[0]["subject"] == "LFA"
    assert tasks[1]["subject"] is None


def test_parse_falls_back_to_subject_named_in_the_task():
    md = """## ➕ Extra
- [ ] [2🍅] Mat. Continuo: teoremi sui limiti
- [ ] [1🍅] Ripasso generico
"""
    tasks = mdimport.parse(md, ["Mat. Continuo"])
    assert tasks[0]["subject"] == "Mat. Continuo"
    assert tasks[1]["subject"] is None


def test_heading_subject_wins_over_the_task_text():
    md = """## LFA
- [ ] [1🍅] Automi, poi Mat. Continuo se avanza tempo
"""
    tasks = mdimport.parse(md, ["LFA", "Mat. Continuo"])
    assert tasks[0]["subject"] == "LFA"


def test_parse_accepts_plain_bullets():
    tasks = mdimport.parse("- Fare la spesa\n* Chiamare Anna\n")
    assert [t["text"] for t in tasks] == ["Fare la spesa", "Chiamare Anna"]
    assert all(t["estimate"] == 0 for t in tasks)


def test_parse_skips_tables_and_prose():
    md = """Testo qualsiasi.

| Fase | Giorni |
|---|---|
| 1 | 22 |

- [ ] [1🍅] Vero task
"""
    assert len(mdimport.parse(md)) == 1


def test_indented_lines_become_the_note():
    md = """- [ ] [2🍅 alpha] Automa minimo
  Sintesi ottima, visita in ampiezza.
  Applicalo su due automi a mano.
"""
    task = mdimport.parse(md)[0]
    assert task["text"] == "Automa minimo"
    assert task["note"] == "Sintesi ottima, visita in ampiezza. Applicalo su due automi a mano."


def test_note_strips_nested_bullets():
    task = mdimport.parse("- [ ] Fare X\n  - primo\n  - secondo\n")[0]
    assert task["note"] == "primo secondo"


def test_blank_line_ends_the_note():
    md = """- [ ] Fare X
  dettaglio

  testo che non c'entra piu
"""
    tasks = mdimport.parse(md)
    assert len(tasks) == 1
    assert tasks[0]["note"] == "dettaglio"


def test_indented_checkbox_is_its_own_task():
    tasks = mdimport.parse("- [ ] Padre\n  - [ ] Figlio\n")
    assert [t["text"] for t in tasks] == ["Padre", "Figlio"]
    assert tasks[0]["note"] == ""


def test_note_does_not_leak_to_the_next_task():
    tasks = mdimport.parse("- [ ] Uno\n  nota di uno\n- [ ] Due\n")
    assert tasks[0]["note"] == "nota di uno"
    assert tasks[1]["note"] == ""


def test_format_task_roundtrips_with_note():
    md = "- [x] [3🍅 beta] Automa minimo\n  Visita in ampiezza di G_L.\n"
    task = mdimport.parse(md)[0]
    out = mdimport.format_task(task["text"], task["done"], task["estimate"],
                               task["wave"], task["note"])
    assert mdimport.parse("\n".join(out))[0] == task


def test_format_prefix_roundtrips():
    text, est, wave = mdimport.parse_prefix("[4🍅 gamma] Ripasso errori")
    assert mdimport.format_prefix(text, est, wave) == "[4🍅 gamma] Ripasso errori"


def test_format_prefix_omits_empty_estimate():
    assert mdimport.format_prefix("Fare X", 0, None) == "Fare X"

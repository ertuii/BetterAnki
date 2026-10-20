"""Thin facade over Anki's own backend. UI (pywebview js_api) and MCP both call these methods.

Every public method takes/returns plain JSON-able values.
"""

import functools
import html
import os
import re
import sys
import threading
from pathlib import Path

from anki.collection import (
    Collection,
    DeckIdLimit,
    ExportAnkiPackageOptions,
    ImportAnkiPackageOptions,
    ImportAnkiPackageRequest,
    ImportCsvRequest,
)
from anki.lang import set_lang
from anki.sound import SoundOrVideoTag

set_lang("de_DE")  # interval labels, undo names, import messages in German


def data_dir() -> Path:
    if os.environ.get("BETTERANKI_DIR"):  # separate profile, e.g. for testing
        base = Path(os.environ["BETTERANKI_DIR"])
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ["APPDATA"])
    else:
        base = Path.home() / ".local" / "share"
    d = base if os.environ.get("BETTERANKI_DIR") else base / "BetterAnki"
    d.mkdir(parents=True, exist_ok=True)
    return d


def collection_path() -> str:
    return str(data_dir() / "collection.anki2")


def _locked(fn):
    @functools.wraps(fn)
    def wrapper(self, *a, **kw):
        with self._lock:
            return fn(self, *a, **kw)

    return wrapper


def _strip(text: str) -> str:
    text = re.sub(r"<style.*?</style>|<script.*?</script>|\[sound:[^\]]+\]", "", text, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"[\u2068\u2069]", "", text).strip()


class Core:
    def __init__(self, path: str | None = None):
        self._col = Collection(path or collection_path())
        self._lock = threading.RLock()  # ponytail: one lock for everything, the collection is single-user anyway
        self._window = None  # set by app.py for file dialogs
        self._current = None  # (card, states) of the card being studied

    def _close(self):
        self._col.close()

    # ---------- decks ----------

    @_locked
    def decks(self) -> list[dict]:
        def walk(node, prefix=""):
            name = f"{prefix}::{node.name}" if prefix else node.name
            return {
                "id": node.deck_id,
                "name": name,
                "short": node.name,
                "new": node.new_count,
                "learn": node.learn_count,
                "review": node.review_count,
                "collapsed": node.collapsed,
                "filtered": node.filtered,
                "children": [walk(c, name) for c in node.children],
            }

        root = self._col.sched.deck_due_tree()
        return [walk(c) for c in root.children]

    @_locked
    def create_deck(self, name: str) -> int:
        return self._col.decks.id(name.strip())

    @_locked
    def rename_deck(self, deck_id: int, name: str) -> None:
        self._col.decks.rename(deck_id, name.strip())

    @_locked
    def delete_deck(self, deck_id: int) -> None:
        self._col.decks.remove([deck_id])

    @_locked
    def set_collapsed(self, deck_id: int, collapsed: bool) -> None:
        self._col.decks.set_collapsed(deck_id, collapsed, scope=0)  # 0 = REVIEWER scope

    # ---------- studying ----------

    def _render(self, card, side: str) -> str:
        out = card.render_output(reload=side == "q")
        text = out.question_text if side == "q" else out.answer_text
        tags = out.question_av_tags if side == "q" else out.answer_av_tags

        def audio(m):
            tag = tags[int(m.group(2))] if int(m.group(2)) < len(tags) else None
            if isinstance(tag, SoundOrVideoTag):
                return f'<audio controls {"autoplay" if m.group(1) == side else ""} src="{html.escape(tag.filename)}"></audio>'
            return ""  # TTS tags: not supported yet

        return re.sub(r"\[anki:play:(q|a):(\d+)\]", audio, text)

    @_locked
    def next_card(self, deck_id: int) -> dict | None:
        self._col.decks.select(deck_id)
        queued = self._col.sched.get_queued_cards()
        if not queued.cards:
            self._current = None
            return None
        qc = queued.cards[0]
        card = self._col.get_card(qc.card.id)
        card.start_timer()
        self._current = (card, qc.states)
        labels = self._col.sched.describe_next_states(qc.states)
        return {
            "card_id": card.id,
            "note_id": card.nid,
            "ord": card.ord,
            "question": self._render(card, "q"),
            "answer": self._render(card, "a"),
            "css": card.render_output().css,
            "buttons": [_strip(x) for x in labels],  # interval labels for Again/Hard/Good/Easy
            "counts": {"new": queued.new_count, "learn": queued.learning_count, "review": queued.review_count},
            "queue": qc.queue,  # 0 new, 1 learning, 2 review
        }

    @_locked
    def answer(self, card_id: int, ease: int) -> None:
        card, states = self._current or (None, None)
        if not card or card.id != card_id:
            raise ValueError("card is no longer current")
        answer = self._col.sched.build_answer(card=card, states=states, rating=ease - 1)
        self._col.sched.answer_card(answer)
        self._current = None

    @_locked
    def undo(self) -> str | None:
        name = self._col.undo_status().undo
        if name:
            self._col.undo()
        return name or None

    @_locked
    def bury_card(self, card_id: int) -> None:
        self._col.sched.bury_cards([card_id])

    # ---------- notes ----------

    @_locked
    def note_types(self) -> list[dict]:
        return [
            {"id": m["id"], "name": m["name"], "fields": [f["name"] for f in m["flds"]], "cloze": m["type"] == 1, "basic": m.get("originalStockKind") == 1}
            for m in self._col.models.all()
            if m.get("originalStockKind") != 6  # ponytail: image occlusion needs its own editor, phase 2
        ]

    def _notetype(self, notetype):
        m = self._col.models.by_name(notetype) if isinstance(notetype, str) else self._col.models.get(notetype)
        if not m and notetype in ("Basic", "Cloze"):  # stock names differ per language ("Einfach", "Lückentext")
            kind = 5 if notetype == "Cloze" else 1  # originalStockKind
            m = next((x for x in self._col.models.all() if x.get("originalStockKind") == kind), None)
        if not m:
            raise ValueError(f"unknown note type: {notetype}")
        return m

    def _fill(self, note, fields):
        names = list(note.keys())
        if isinstance(fields, list):
            fields = dict(zip(names, fields))
        aliases = {"Front": 0, "Text": 0, "Back": 1, "Back Extra": 1}  # English stock names on a German collection
        for k, v in fields.items():
            if k not in names and aliases.get(k, 99) < len(names):
                k = names[aliases[k]]
            if k not in names:
                raise ValueError(f"unknown field '{k}', expected one of {names}")
            note[k] = v

    @_locked
    def add_note(self, notetype, deck, fields, tags: list[str] | None = None) -> int:
        """notetype/deck: name or id. fields: {name: value} or list in field order."""
        note = self._col.new_note(self._notetype(notetype))
        self._fill(note, fields)
        note.tags = tags or []
        deck_id = deck if isinstance(deck, int) else self._col.decks.id(deck)
        if not note.fields[0].strip():
            raise ValueError("first field must not be empty")
        self._col.add_note(note, deck_id)
        return note.id

    @_locked
    def get_note(self, note_id: int) -> dict:
        note = self._col.get_note(note_id)
        cards = note.cards()
        return {
            "id": note.id,
            "notetype": note.note_type()["name"],
            "notetype_id": note.mid,
            "fields": dict(note.items()),
            "tags": note.tags,
            "deck_id": cards[0].did if cards else None,
            "card_ids": [c.id for c in cards],
        }

    @_locked
    def update_note(self, note_id: int, fields: dict | None = None, tags: list[str] | None = None, deck=None) -> None:
        note = self._col.get_note(note_id)
        if fields:
            self._fill(note, fields)
        if tags is not None:
            note.tags = tags
        self._col.update_note(note)
        if deck is not None:
            deck_id = deck if isinstance(deck, int) else self._col.decks.id(deck)
            self._col.set_deck(note.card_ids(), deck_id)

    @_locked
    def delete_notes(self, note_ids: list[int]) -> int:
        return self._col.remove_notes(note_ids).count

    # ---------- browser ----------

    @_locked
    def search(self, query: str = "", limit: int = 500) -> list[dict]:
        """Anki search syntax, e.g. 'deck:Spanish tag:verb is:due'. Returns one row per card."""
        rows = []
        decks = {d.id: d.name for d in self._col.decks.all_names_and_ids()}
        for cid in self._col.find_cards(query, order=True)[:limit]:
            card = self._col.get_card(cid)
            note = card.note()
            sortf = note.note_type()["sortf"]
            rows.append({
                "card_id": cid,
                "note_id": note.id,
                "sort": _strip(note.fields[sortf])[:200],
                "notetype": note.note_type()["name"],
                "deck": decks.get(card.odid or card.did, "?"),
                "tags": note.tags,
                "due": card.due if card.queue == 0 else None,
                "interval": card.ivl,
                "reps": card.reps,
                "suspended": card.queue == -1,
                "flag": card.user_flag(),
            })
        return rows

    @_locked
    def suspend(self, card_ids: list[int], suspended: bool = True) -> None:
        (self._col.sched.suspend_cards if suspended else self._col.sched.unsuspend_cards)(card_ids)

    @_locked
    def flag(self, card_ids: list[int], flag: int) -> None:
        self._col.set_user_flag_for_cards(flag, card_ids)

    @_locked
    def move_cards(self, card_ids: list[int], deck) -> None:
        deck_id = deck if isinstance(deck, int) else self._col.decks.id(deck)
        self._col.set_deck(card_ids, deck_id)

    @_locked
    def card_info(self, card_id: int) -> str:
        return self._col.card_stats(card_id, include_revlog=True)

    # ---------- stats ----------

    @_locked
    def stats(self) -> dict:
        return {
            "cards": self._col.card_count(),
            "notes": self._col.note_count(),
            "studied_today": _strip(self._col.studied_today()),
            "due_today": sum(d["new"] + d["learn"] + d["review"] for d in self.decks()),
        }

    @_locked
    def overview(self, past_days: int = 126, future_days: int = 28) -> dict:
        """Data for the 'Heute' screen: reviews per past day, forecast per future day, streak, retention."""
        db, sched = self._col.db, self._col.sched
        cutoff = sched.day_cutoff  # unix seconds of the next day rollover
        today = sched.today
        past = dict(db.all(
            "select (? - id/1000 - 1) / 86400 as ago, count() from revlog where id > ? group by ago",
            cutoff, (cutoff - past_days * 86400) * 1000,
        ))
        future = dict(db.all(
            "select due - ?, count() from cards where queue in (2,3) and due between ? and ? group by due",
            today, today, today + future_days,
        ))
        streak = 0
        while past.get(streak + (0 if past.get(0) else 1)):
            streak += 1
        month_ago = (cutoff - 30 * 86400) * 1000
        passed, total, secs = db.first(
            "select sum(ease > 1), count(), sum(time) / 1000.0 from revlog where id > ? and type = 1", month_ago
        ) or (0, 0, 0)
        avg_secs = (db.scalar("select avg(time) / 1000.0 from revlog where id > ?", month_ago) or 10)
        due = sum(d["new"] + d["learn"] + d["review"] for d in self.decks())
        return {
            "due": due,
            "minutes": round(due * avg_secs / 60),
            "streak": streak,
            "retention": round(100 * passed / total) if total else None,
            "past": [past.get(i, 0) for i in range(past_days - 1, -1, -1)],  # oldest first, last = today
            "future": [future.get(i, 0) for i in range(1, future_days + 1)],
            "overdue": {d["id"]: n for d in self._flat_decks() if (n := self._overdue(d["id"]))},
        }

    def _flat_decks(self):
        def walk(nodes):
            for n in nodes:
                yield n
                yield from walk(n["children"])
        return list(walk(self.decks()))

    def _overdue(self, deck_id: int) -> int:
        ids = self._col.decks.deck_and_child_ids(deck_id)
        return self._col.db.scalar(
            f"select count() from cards where queue = 2 and due < ? and did in ({','.join(map(str, ids))})",
            self._col.sched.today,
        )

    # ---------- import / export ----------

    @_locked
    def import_file(self, path: str) -> str:
        ext = Path(path).suffix.lower()
        if ext == ".apkg":
            req = ImportAnkiPackageRequest(
                package_path=path,
                options=ImportAnkiPackageOptions(with_scheduling=True, with_deck_configs=True),
            )
            log = self._col.import_anki_package(req).log
        elif ext in (".csv", ".txt", ".tsv"):
            meta = self._col.get_csv_metadata(path, None)
            log = self._col.import_csv(ImportCsvRequest(path=path, metadata=meta)).log
        else:
            raise ValueError("supported: .apkg, .csv, .txt, .tsv")
        return f"{len(log.new)} neu, {len(log.updated)} aktualisiert, {len(log.duplicate)} Duplikate"

    @_locked
    def export_deck(self, path: str, deck_id: int | None = None, scheduling: bool = True, media: bool = True) -> int:
        return self._col.export_anki_package(
            out_path=path,
            options=ExportAnkiPackageOptions(with_scheduling=scheduling, with_deck_configs=scheduling, with_media=media, legacy=False),
            limit=DeckIdLimit(deck_id) if deck_id else None,
        )

    # ---------- native dialogs (app only) ----------

    def pick_import_file(self) -> str | None:
        import webview

        res = self._window.create_file_dialog(webview.FileDialog.OPEN, file_types=("Anki/CSV (*.apkg;*.csv;*.txt;*.tsv)",))
        return res[0] if res else None

    def pick_export_file(self, name: str) -> str | None:
        import webview

        res = self._window.create_file_dialog(webview.FileDialog.SAVE, save_filename=f"{name}.apkg")
        return (res if isinstance(res, str) else res[0]) if res else None

    def media_dir(self) -> str:
        return self._col.media.dir()

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
from anki.sound import SoundOrVideoTag, TTSTag

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


_SPEAKER = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/>'
            '<path d="M19 5a10 10 0 0 1 0 14"/></svg>')


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

    # ---------- deck options (presets) & FSRS ----------

    _OPTION_FIELDS = (
        "new_per_day", "reviews_per_day", "graduating_interval_good", "graduating_interval_easy",
        "maximum_review_interval", "leech_threshold", "leech_action", "bury_new", "bury_reviews",
        "bury_interday_learning", "desired_retention",
    )

    def _configs_for(self, deck_id: int):
        info = self._col.decks.get_deck_configs_for_update(deck_id)
        return info, {c.config.id: c for c in info.all_config}

    @_locked
    def deck_options(self, deck_id: int, preset_id: int | None = None) -> dict:
        info, by_id = self._configs_for(deck_id)
        cfg = by_id[preset_id or info.current_deck.config_id].config
        c = cfg.config
        return {
            "deck_name": info.current_deck.name,
            "preset_id": cfg.id,
            "presets": [{"id": x.config.id, "name": x.config.name, "decks": x.use_count} for x in info.all_config],
            "fsrs": info.fsrs,
            "fsrs_optimized": len(c.fsrs_params_6) > 0,
            "days_since_optimize": info.days_since_last_fsrs_optimize,
            "learn_steps": list(c.learn_steps),
            "relearn_steps": list(c.relearn_steps),
            **{f: getattr(c, f) for f in self._OPTION_FIELDS},
            "desired_retention": round(c.desired_retention, 2),
        }

    def _save_configs(self, deck_id: int, info, cfg, fsrs: bool):
        from anki.deck_config_pb2 import UpdateDeckConfigsRequest

        self._col.decks.update_deck_configs(UpdateDeckConfigsRequest(
            target_deck_id=deck_id,
            configs=[cfg],  # the last config is the one applied to the target deck
            limits=info.current_deck.limits,
            card_state_customizer=info.card_state_customizer,
            new_cards_ignore_review_limit=info.new_cards_ignore_review_limit,
            apply_all_parent_limits=info.apply_all_parent_limits,
            fsrs=fsrs,
            fsrs_reschedule=False,
            fsrs_health_check=info.fsrs_health_check,
        ))

    @_locked
    def save_deck_options(self, deck_id: int, options: dict) -> None:
        """options: same keys as deck_options(); preset_id picks which preset this deck uses."""
        info, by_id = self._configs_for(deck_id)
        cfg = by_id[options.get("preset_id", info.current_deck.config_id)].config
        c = cfg.config
        for f in self._OPTION_FIELDS:
            if f in options:
                setattr(c, f, type(getattr(c, f))(options[f]))
        for f in ("learn_steps", "relearn_steps"):
            if f in options:
                del getattr(c, f)[:]
                getattr(c, f).extend(float(x) for x in options[f])
        self._save_configs(deck_id, info, cfg, bool(options.get("fsrs", info.fsrs)))

    @_locked
    def new_preset(self, deck_id: int, name: str) -> int:
        """Clone the deck's current preset under a new name and assign it to the deck."""
        info, by_id = self._configs_for(deck_id)
        cfg = by_id[info.current_deck.config_id].config
        clone = type(cfg)()
        clone.CopyFrom(cfg)
        clone.id = 0  # 0 = create new
        clone.name = name.strip()
        self._save_configs(deck_id, info, clone, info.fsrs)
        return self._col.decks.get(deck_id)["conf"]

    @_locked
    def optimize_fsrs(self, deck_id: int) -> dict:
        """Fit FSRS parameters to this preset's review history (needs a few hundred reviews to matter)."""
        info, by_id = self._configs_for(deck_id)
        cfg = by_id[info.current_deck.config_id].config
        c = cfg.config
        search = c.param_search or f'preset:"{cfg.name}" -is:suspended'
        res = self._col._backend.compute_fsrs_params(
            search=search, current_params=list(c.fsrs_params_6), ignore_revlogs_before_ms=0,
            num_of_relearning_steps=len(c.relearn_steps), health_check=False,
        )
        changed = list(res.params) != list(c.fsrs_params_6) and len(res.params) > 0
        if changed:
            del c.fsrs_params_6[:]
            c.fsrs_params_6.extend(res.params)
            self._save_configs(deck_id, info, cfg, True)
        return {"reviews": res.fsrs_items, "changed": changed}

    # ---------- filtered decks ----------

    @_locked
    def create_filtered_deck(self, name: str, search: str, limit: int = 100, order: int = 1, reschedule: bool = True) -> int:
        """order: 0 zuletzt gesehen, 1 zufällig, 2 kleinstes Intervall, 3 größtes Intervall, 4 meiste Fehler,
        5 hinzugefügt, 6 fällig, 7 zuletzt hinzugefügt, 8 relativ überfällig."""
        did = self._col.decks.new_filtered(name.strip())
        d = self._col.decks.get(did)
        d["terms"] = [[search, int(limit), int(order)]]
        d["resched"] = bool(reschedule)
        self._col.decks.save(d)
        self._col.sched.rebuild_filtered_deck(did)
        return did

    @_locked
    def rebuild_filtered_deck(self, deck_id: int) -> int:
        return self._col.sched.rebuild_filtered_deck(deck_id).count

    @_locked
    def empty_filtered_deck(self, deck_id: int) -> None:
        self._col.sched.empty_filtered_deck(deck_id)

    # ---------- note types ----------

    @_locked
    def notetype(self, notetype_id: int) -> dict:
        m = self._col.models.get(notetype_id)
        return {
            "id": m["id"], "name": m["name"], "cloze": m["type"] == 1, "css": m["css"],
            "use_count": self._col.models.use_count(m),
            "fields": [{"ord": f["ord"], "name": f["name"]} for f in m["flds"]],
            "templates": [{"ord": t["ord"], "name": t["name"], "qfmt": t["qfmt"], "afmt": t["afmt"]} for t in m["tmpls"]],
        }

    def _apply_notetype(self, data: dict):
        """Build an updated notetype dict from UI data. Entries keep their 'ord' (None = new) so
        Anki maps renames/reorders/removals onto existing notes."""
        m = self._col.models.get(data["id"])
        old_f = {f["ord"]: f for f in m["flds"]}
        old_t = {t["ord"]: t for t in m["tmpls"]}
        flds = []
        for f in data["fields"]:
            fd = dict(old_f[f["ord"]]) if f.get("ord") is not None else self._col.models.new_field(f["name"])
            fd["name"] = f["name"].strip()
            flds.append(fd)
        renames = {old_f[f["ord"]]["name"]: f["name"].strip() for f in data["fields"]
                   if f.get("ord") is not None and old_f[f["ord"]]["name"] != f["name"].strip()}

        def rename_refs(text):  # what Anki does on save, so the preview matches: {{Old}}, {{#Old}}, {{text:Old}} ...
            for old, new in renames.items():
                text = re.sub(r"(\{\{[#/^]?(?:[^{}:]*:)*)" + re.escape(old) + r"\}\}", lambda m: m.group(1) + new + "}}", text)
            return text

        tmpls = []
        for t in data["templates"]:
            td = dict(old_t[t["ord"]]) if t.get("ord") is not None else self._col.models.new_template(t["name"])
            td.update(name=t["name"].strip(), qfmt=rename_refs(t["qfmt"]), afmt=rename_refs(t["afmt"]))
            tmpls.append(td)
        m.update(name=data["name"].strip(), css=data["css"], flds=flds, tmpls=tmpls)
        return m

    @_locked
    def save_notetype(self, data: dict) -> None:
        self._col.models.update_dict(self._apply_notetype(data))

    @_locked
    def add_notetype(self, base_id: int, name: str) -> int:
        m = self._col.models.copy(self._col.models.get(base_id), add=False)
        m["name"] = name.strip()
        self._col.models.add_dict(m)
        return self._col.models.by_name(m["name"])["id"]

    @_locked
    def delete_notetype(self, notetype_id: int) -> None:
        self._col.models.remove(notetype_id)

    @_locked
    def preview_template(self, data: dict, template_index: int) -> dict:
        """Render unsaved template edits with placeholder field contents.

        Anki's renderer resolves field names through the *stored* notetype, so references to
        renamed fields are mapped back to their stored name and unknown (new) fields become literals.
        """
        stored = self._col.models.get(data["id"])
        by_ord = {f["ord"]: f["name"] for f in stored["flds"]}
        current = {f["ord"]: f["name"].strip() for f in data["fields"] if f.get("ord") is not None}
        to_stored = {new: by_ord[o] for o, new in current.items()}
        special = {"FrontSide", "Tags", "Deck", "Subdeck", "Card", "Type", "CardFlag"}

        def fix(text):
            def ref(mo):
                prefix, name = mo.group(1), mo.group(2).strip()
                if name in to_stored:
                    return f"{prefix}{to_stored[name]}}}}}"
                if name in by_ord.values() or name in special:
                    return mo.group(0)
                return f"({name})" if prefix == "{{" else ""  # new field: show a placeholder, drop its sections
            return re.sub(r"(\{\{[#/^]?(?:[^{}:]*:)*)([^{}:#/^][^{}]*?)\}\}", ref, text)

        t = data["templates"][template_index]
        tmpl = dict(stored["tmpls"][t["ord"]]) if t.get("ord") is not None else self._col.models.new_template(t["name"])
        tmpl.update(qfmt=fix(t["qfmt"]), afmt=fix(t["afmt"]))
        m = {**stored, "css": data["css"]}
        note = self._col.new_note(stored)
        note.fields = [
            "{{c1::Beispiel}} für den Lückentext" if stored["type"] == 1 and i == 0 else f"({current.get(f['ord'], f['name'])})"
            for i, f in enumerate(stored["flds"])
        ]
        ord_ = 0 if stored["type"] == 1 else template_index
        card = note.ephemeral_card(ord_, custom_note_type=m, custom_template=tmpl, fill_empty=True)
        out = card.render_output()  # already rendered from the layout; reload would look up a stored card
        return {"question": out.question_text, "answer": out.answer_text, "css": out.css, "ord": ord_}

    # ---------- backups & AnkiWeb sync ----------

    def _backup_dir(self) -> Path:
        d = data_dir() / "backups"
        d.mkdir(exist_ok=True)
        return d

    @_locked
    def backup(self, force: bool = True) -> bool:
        """force=False only backs up if Anki's periodic interval has passed (used on app exit)."""
        return self._col.create_backup(backup_folder=str(self._backup_dir()), force=force, wait_for_completion=True)

    def backups(self) -> list[dict]:
        files = sorted(self._backup_dir().glob("*.colpkg"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [{"path": str(p), "name": p.name, "size_kb": p.stat().st_size // 1024, "mtime": p.stat().st_mtime} for p in files]

    def data_folder(self) -> str:
        return str(data_dir())

    def _replace_collection(self, colpkg: str):
        """Replace the whole collection with a .colpkg (import or backup restore). A backup is made first."""
        import shutil
        import tempfile

        from anki._backend import RustBackend

        # copy the source first: the safety backup below can get the same timestamped name as it
        src = Path(tempfile.mkdtemp()) / "import.colpkg"
        shutil.copy(colpkg, src)
        self._col.create_backup(backup_folder=str(self._backup_dir()), force=True, wait_for_completion=True)
        path = self._col.path
        media_folder, media_db = self._col.media.dir(), str(Path(path).with_suffix(".media.db2"))
        self._col.close(downgrade=False)
        try:
            RustBackend().import_collection_package(col_path=path, backup_path=str(src), media_folder=media_folder, media_db=media_db)
        finally:
            self._col = Collection(path)
            self._current = None
            shutil.rmtree(src.parent, ignore_errors=True)

    @_locked
    def restore_backup(self, path: str) -> None:
        self._replace_collection(path)

    _SYNC_FILE = "sync.json"

    def _sync_auth(self):
        import json
        from anki.sync_pb2 import SyncAuth

        f = data_dir() / self._SYNC_FILE
        if not f.exists():
            return None
        d = json.loads(f.read_text())
        return SyncAuth(hkey=d["hkey"], endpoint=d.get("endpoint") or None)

    def sync_account(self) -> str | None:
        import json

        f = data_dir() / self._SYNC_FILE
        return json.loads(f.read_text()).get("username") if f.exists() else None

    @_locked
    def sync_login(self, username: str, password: str) -> None:
        import json

        auth = self._col.sync_login(username=username, password=password, endpoint=None)
        f = data_dir() / self._SYNC_FILE
        f.write_text(json.dumps({"hkey": auth.hkey, "endpoint": auth.endpoint, "username": username}))
        f.chmod(0o600)  # the hkey is a login token

    def sync_logout(self) -> None:
        (data_dir() / self._SYNC_FILE).unlink(missing_ok=True)

    @_locked
    def sync(self) -> dict:
        """Normal sync. Returns {'full_required': True} when AnkiWeb needs a one-way full sync first."""
        from anki.sync_pb2 import SyncCollectionResponse as R

        auth = self._sync_auth()
        if not auth:
            raise ValueError("Nicht bei AnkiWeb angemeldet")
        out = self._col.sync_collection(auth, sync_media=False)
        if out.new_endpoint:
            auth.endpoint = out.new_endpoint
        if out.required in (R.FULL_SYNC, R.FULL_DOWNLOAD, R.FULL_UPLOAD):
            self._pending_full = (auth, out.server_media_usn)
            return {"full_required": True, "direction": {R.FULL_DOWNLOAD: "download", R.FULL_UPLOAD: "upload"}.get(out.required),
                    "message": out.server_message}
        self._col.sync_media(auth)
        return {"full_required": False, "message": out.server_message}

    @_locked
    def full_sync(self, upload: bool) -> None:
        auth, media_usn = getattr(self, "_pending_full", (self._sync_auth(), None))
        self._col.close_for_full_sync()
        try:
            self._col.full_upload_or_download(auth=auth, server_usn=media_usn, upload=upload)
        finally:
            self._col.reopen(after_full_sync=True)
            self._current = None
        self._col.sync_media(auth)

    # ---------- studying ----------

    def _render(self, card, side: str) -> str:
        out = card.render_output(reload=side == "q")
        text = out.question_text if side == "q" else out.answer_text
        tags = out.question_av_tags if side == "q" else out.answer_av_tags

        def audio(m):
            tag = tags[int(m.group(2))] if int(m.group(2)) < len(tags) else None
            auto = m.group(1) == side
            if isinstance(tag, SoundOrVideoTag):
                return f'<audio controls {"autoplay" if auto else ""} src="{html.escape(tag.filename)}"></audio>'
            if isinstance(tag, TTSTag):  # spoken by the system voice via speechSynthesis inside the card frame
                return (f'<button class="ba-tts" data-auto="{int(auto)}" data-lang="{html.escape(tag.lang.replace("_", "-"))}" '
                        f'data-text="{html.escape(tag.field_text)}" aria-label="Vorlesen">{_SPEAKER}</button>')
            return ""

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

    @_locked
    def statistics(self, deck_id: int | None = None, days: int = 30) -> dict:
        """Chart data from Anki's own graph engine, flattened for the UI."""
        from google.protobuf.json_format import MessageToDict

        search = f'"deck:{self._col.decks.name(deck_id)}"' if deck_id else ""
        g = MessageToDict(self._col._backend.graphs(search=search, days=days))
        period = {30: "oneMonth", 90: "threeMonths"}.get(days, "oneYear")

        today = g.get("today", {})
        answered = today.get("answerCount", 0)

        future = [0] * days
        for k, n in g.get("futureDue", {}).get("futureDue", {}).items():
            if int(k) < days:
                future[max(0, int(k))] += n  # overdue lands on today

        reviews = [{"learn": 0, "relearn": 0, "young": 0, "mature": 0, "filtered": 0} for _ in range(days)]
        for k, v in g.get("reviews", {}).get("count", {}).items():
            if -days < int(k) <= 0:
                reviews[days - 1 + int(k)].update(v)

        buckets = [(1, 1, "1 T"), (2, 2, "2 T"), (3, 3, "3 T"), (4, 7, "4–7 T"), (8, 14, "1–2 W"), (15, 30, "2–4 W"),
                   (31, 90, "1–3 M"), (91, 180, "3–6 M"), (181, 365, "6–12 M"), (366, 10**9, "> 1 J")]
        ivls = {int(k): v for k, v in g.get("intervals", {}).get("intervals", {}).items()}
        intervals = [{"label": lab, "n": sum(v for i, v in ivls.items() if lo <= i <= hi)} for lo, hi, lab in buckets]

        retention = {}
        for k, v in g.get("trueRetention", {}).items():
            passed = v.get("youngPassed", 0) + v.get("maturePassed", 0)
            total = passed + v.get("youngFailed", 0) + v.get("matureFailed", 0)
            retention[k] = {"pct": round(100 * passed / total, 1) if total else None, "total": total}

        cc = g.get("cardCounts", {}).get("includingInactive", {})
        return {
            "today": {
                "answered": answered,
                "minutes": round(today.get("answerMillis", 0) / 60000, 1),
                "correct_pct": round(100 * today.get("correctCount", 0) / answered) if answered else None,
                "learn": today.get("learnCount", 0), "review": today.get("reviewCount", 0),
                "relearn": today.get("relearnCount", 0),
            },
            "future": future,
            "reviews": reviews,
            "intervals": intervals,
            "card_counts": {k: cc.get(src, 0) for k, src in [("new", "newCards"), ("learn", "learn"), ("relearn", "relearn"),
                            ("young", "young"), ("mature", "mature"), ("suspended", "suspended"), ("buried", "buried")]},
            "hours": [{"total": h.get("total", 0), "correct": h.get("correct", 0)} for h in g.get("hours", {}).get(period, [])],
            "buttons": {k: v for k, v in g.get("buttons", {}).get(period, {}).items()},
            "retention": retention,
        }

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
        elif ext == ".colpkg":
            self._replace_collection(path)
            return "Sammlung ersetzt (vorherige als Sicherung behalten)"
        elif ext in (".csv", ".txt", ".tsv"):
            meta = self._col.get_csv_metadata(path, None)
            log = self._col.import_csv(ImportCsvRequest(path=path, metadata=meta)).log
        else:
            raise ValueError("unterstützt: .apkg, .colpkg, .csv, .txt, .tsv")
        return f"{len(log.new)} neu, {len(log.updated)} aktualisiert, {len(log.duplicate)} Duplikate"

    @_locked
    def export_deck(self, path: str, deck_id: int | None = None, scheduling: bool = True, media: bool = True) -> int:
        return self._col.export_anki_package(
            out_path=path,
            options=ExportAnkiPackageOptions(with_scheduling=scheduling, with_deck_configs=scheduling, with_media=media, legacy=False),
            limit=DeckIdLimit(deck_id) if deck_id else None,
        )

    @_locked
    def export_collection(self, path: str, media: bool = True) -> None:
        """Whole collection as .colpkg (for moving to another computer or Anki itself)."""
        self._col.export_collection_package(path, include_media=media, legacy=False)

    def mcp_command(self) -> str:
        """The command Claude should run to start the MCP server for this installation."""
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}" --mcp'
        return f'uv run --directory "{Path(__file__).resolve().parents[2]}" betteranki --mcp'

    # ---------- native dialogs (app only) ----------

    def pick_import_file(self) -> str | None:
        import webview

        res = self._window.create_file_dialog(webview.FileDialog.OPEN, file_types=("Anki/CSV (*.apkg;*.colpkg;*.csv;*.txt;*.tsv)",))
        return res[0] if res else None

    def pick_export_file(self, name: str, ext: str = "apkg") -> str | None:
        import webview

        res = self._window.create_file_dialog(webview.FileDialog.SAVE, save_filename=f"{name}.{ext}")
        return (res if isinstance(res, str) else res[0]) if res else None

    def media_dir(self) -> str:
        return self._col.media.dir()

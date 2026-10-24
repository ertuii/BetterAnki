"""Type-in answers, current card for Claude, duplicate check, image occlusion type, media from Claude."""

import base64
import os
import tempfile
from pathlib import Path

HOME = Path(tempfile.mkdtemp())
os.environ["MUISTI_DIR"] = str(HOME / "data")

from muisti.core import Core, collection_path  # noqa: E402

core = Core(collection_path())
col = core._col

# type-in answer: a copy of Basic with {{type:Back}}
basic = next(t for t in core.note_types() if t["basic"])
tid = core.add_notetype(basic["id"], "Eintippen")
nt = core.notetype(tid)
front, back = (f["name"] for f in nt["fields"])  # German stock names
nt["templates"][0]["qfmt"] = f"{{{{{front}}}}}<br>{{{{type:{back}}}}}"
nt["templates"][0]["afmt"] = f"{{{{{front}}}}}<hr id=answer>{{{{type:{back}}}}}"
core.save_notetype(nt)
deck = core.create_deck("Tippen")
nid = core.add_note(tid, deck, ["Hauptstadt?", "<b>Berlin</b>"])
card = core.next_card(deck)
assert card["type_answer"] and '<input id="typeans"' in card["question"], card["question"]
assert "[[typeans]]" in card["answer"] and "[[type:" not in card["answer"]
out = core.compare_answer(card["card_id"], "Berlim")
assert "typeGood" in out and "typeBad" in out and "<b>" not in out, out

# cloze typing: only the asked cloze is expected
cloze = next(t for t in core.note_types() if t["cloze"] and not t["io"])
cid_ = core.add_notetype(cloze["id"], "Lücke tippen")
nt = core.notetype(cid_)
text = nt["fields"][0]["name"]
nt["templates"][0]["qfmt"] = f"{{{{cloze:{text}}}}}{{{{type:cloze:{text}}}}}"
core.save_notetype(nt)
d2 = core.create_deck("Lücke")
core.add_note(cid_, d2, ["{{c1::Paris}} liegt in {{c2::Frankreich}}"])
card = core.next_card(d2)
assert core._typed[0] in ("Paris", "Frankreich"), core._typed

# a card without {{type:}} has no input
core.add_note("Basic", "Normal", ["a", "b"])
assert core.next_card(col.decks.id("Normal"))["type_answer"] is False

# current card for Claude
cur = core.current_card()
assert cur["fields"] and cur["question"] == "a" and cur["deck"] == "Normal", cur
core.leave_study()
assert core.current_card() is None

# duplicates: warning in the editor, rejected for Claude unless allowed
assert core.duplicate_of(basic["id"], "<i>a</i>") is not None  # HTML ignored
assert core.duplicate_of(basic["id"], "neu") is None
own = col.find_notes('"deck:Normal"')[0]
assert core.duplicate_of(basic["id"], "a", own) is None  # editing a note is not its own duplicate
try:
    core.add_note("Basic", "Normal", ["a", "c"], allow_duplicate=False)
    raise AssertionError("duplicate accepted")
except ValueError as e:
    assert str(own) in str(e)
core.add_note("Basic", "Normal", ["a", "c"])  # the app's editor still allows it, like Anki

# image occlusion: Anki's type is offered, notes are plain fields, rendering gives the mask data
io = next(t for t in core.note_types() if t["io"])
png = base64.b64encode(base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")).decode()
name = core.add_media("schema.png", png)
occ = "{{c1::image-occlusion:rect:left=.1:top=.2:width=.3:height=.1:oi=1}}{{c2::image-occlusion:rect:left=.5:top=.5:width=.2:height=.2:oi=1}}"
core.add_note(io["id"], "Anatomie", [occ, f'<img src="{name}">', "Herz", "", ""])
card = core.next_card(col.decks.id("Anatomie"))
assert 'class="cloze" data-ordinal="1" data-shape="rect"' in card["question"] and "anki.imageOcclusion.setup" in card["question"]
assert "cloze-highlight" in card["answer"]
assert len(col.find_cards('"deck:Anatomie"')) == 2
assert len([t for t in core.note_types() if t["io"]]) == 1  # created once

# exporting the whole collection: Anki closes it for that, the app must keep working afterwards
core.export_collection(str(Path(tempfile.mkdtemp()) / "alles.colpkg"))
assert core.decks() and core.next_card(col.decks.id("Anatomie"))

core._close()
print("ok")

import os
import tempfile
from pathlib import Path

HOME = Path(tempfile.mkdtemp())
os.environ["HOME"] = str(HOME)  # fake Anki desktop profile lives here
os.environ["BETTERANKI_DIR"] = str(HOME / "data")

from anki.collection import Collection

from betteranki.core import Core, collection_path


def _fake_anki_profile() -> Path:
    base = Core._anki_base() / "Benutzer 1"
    base.mkdir(parents=True)
    col = Collection(str(base / "collection.anki2"))
    nt = col.models.by_name("Basic") or col.models.all()[0]
    for i in range(3):
        n = col.new_note(nt)
        n.fields[0], n.fields[1] = f"anki{i}", f"<img src='bild{i}.png'>"
        col.add_note(n, col.decks.id("Aus Anki"))
        col.media.write_data(f"bild{i}.png", b"\x89PNG fake")
    col.close()
    return base / "collection.anki2"


def test_migration_and_prelearn():
    src = _fake_anki_profile()
    core = Core(collection_path())
    core.add_note("Basic", "Eigenes", ["mein", "eigenes"])

    profiles = core.anki_profiles()
    assert profiles[0]["cards"] == 3 and profiles[0]["media"] == 3 and not profiles[0]["locked"]

    assert "3 neu" in core.migrate_from_anki(str(src), "merge")
    assert len(core.search("")) == 4
    assert (Path(core.storage()["dir"]) / "collection.media" / "bild0.png").exists()

    core.migrate_from_anki(str(src), "replace")
    assert len(core.search("")) == 3 and core.backups()  # old state kept as backup
    assert Collection(str(src)).card_count() == 3  # Anki's original untouched (and openable)

    # pre-learn a future day: make one card a review due in 2 days
    cid = core._col.find_cards("")[0]
    core._col.db.execute("update cards set type=2, queue=2, ivl=5, due=? where id=?", core._col.sched.today + 2, cid)
    r = core.prelearn(2)
    assert r["count"] == 1
    card = core.next_card(r["deck_id"])
    assert card and card["card_id"] == cid and "autoplay" in card["study"]
    core.answer(cid, 3)
    core.end_prelearn(r["deck_id"])
    assert not any(d["name"].startswith("Vorlernen") for d in core.decks())
    assert core._col.get_card(cid).due > core._col.sched.today + 2  # rescheduled further out
    core._close()


if __name__ == "__main__":
    test_migration_and_prelearn()
    print("ok")

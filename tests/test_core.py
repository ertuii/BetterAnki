import tempfile
from pathlib import Path

from betteranki.core import Core


def test_roundtrip():
    tmp = Path(tempfile.mkdtemp())
    core = Core(str(tmp / "c.anki2"))
    deck = core.create_deck("Spanisch::Verben")
    nid = core.add_note("Basic", "Spanisch::Verben", {"Front": "hablar", "Back": "sprechen"}, ["verb"])

    assert core.stats()["due_today"] == 1
    card = core.next_card(deck)
    assert "hablar" in card["question"] and "sprechen" in card["answer"]
    assert len(card["buttons"]) == 4
    core.answer(card["card_id"], 3)
    ov = core.overview()
    assert ov["past"][-1] == 1 and ov["streak"] == 1, ov
    assert core.search("deck:Spanisch")[0]["reps"] == 1

    core.update_note(nid, {"Back": "reden"}, ["verb", "a1"])
    assert list(core.get_note(nid)["fields"].values())[1] == "reden"
    assert core.undo()  # undo the update

    out = str(tmp / "x.apkg")
    core.export_deck(out, deck)
    core.delete_notes([nid])
    assert core.search("") == []
    assert "1 neu" in core.import_file(out)
    core._close()


if __name__ == "__main__":
    test_roundtrip()
    print("ok")

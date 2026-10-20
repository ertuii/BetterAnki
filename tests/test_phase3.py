import json
import os
import tempfile
from pathlib import Path

HOME = Path(tempfile.mkdtemp())
os.environ["BETTERANKI_DIR"] = str(HOME / "data")
# Claude Desktop/Code configs are looked up here, never the real ones (Windows: USERPROFILE, APPDATA)
os.environ["HOME"] = os.environ["USERPROFILE"] = os.environ["APPDATA"] = str(HOME)

from betteranki import claude_connect
from betteranki.core import Core, collection_path, data_dir


def test_storage_import_claude():
    core = Core(collection_path())
    core.create_deck("Bio")
    core.add_note("Basic", "Bio", ["Zelle", "kleinste Einheit"])

    # CSV with options: own deck, columns swapped, tags from column 3
    csv = HOME / "v.csv"
    csv.write_text("sprechen;hablar;verb\nessen;comer;verb\n")
    info = core.inspect_import(str(csv))
    assert info["kind"] == "csv" and info["columns"] == 3 and len(info["preview"]) == 2
    assert "2 neu" in core.import_file(str(csv), "Spanisch", info["notetype_id"], [2, 1], 3)
    row = next(r for r in core.search('"deck:Spanisch"') if r["sort"] == "hablar")
    assert row["tags"] == ["verb"]

    # move the collection to another folder, then switch back by opening the original
    target = HOME / "Karten"
    assert "jetzt in" in core.change_storage(str(target), "move")
    assert Path(core.storage()["dir"]) == target and (target / "collection.anki2").exists()
    assert len(core.search("")) == 3
    core.change_storage(str(data_dir()), "open")
    assert core.storage()["is_default"]
    assert core.check_storage_target(str(target))["has_collection"]
    assert core.storage()["synced_folder"] is False

    # Claude Desktop: merges into an existing config and keeps other servers
    desktop = claude_connect._desktop_config()
    assert desktop.is_relative_to(HOME)
    desktop.parent.mkdir(parents=True)
    desktop.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}, "preferences": {"a": 1}}))
    claude_connect.connect("desktop")
    cfg = json.loads(desktop.read_text())
    assert set(cfg["mcpServers"]) == {"other", "betteranki"} and cfg["preferences"] == {"a": 1}
    assert claude_connect.status()["desktop"]["state"] == "on"
    claude_connect.disconnect("desktop")
    assert set(json.loads(desktop.read_text())["mcpServers"]) == {"other"}
    core._close()


if __name__ == "__main__":
    test_storage_import_claude()
    print("ok")

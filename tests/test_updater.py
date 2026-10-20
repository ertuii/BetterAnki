"""Updater: finds a newer release on a fake server, downloads and unpacks it next to the app."""

import http.server
import json
import os
import sys
import tempfile
import threading
import zipfile
from pathlib import Path

os.environ["BETTERANKI_DIR"] = tempfile.mkdtemp()  # the swap helper reports failures into the data folder
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from betteranki import updater  # noqa: E402

tmp = Path(tempfile.mkdtemp())
app_name = "BetterAnki" if sys.platform == "win32" else "BetterAnki.app"
(tmp / "Applications" / app_name).mkdir(parents=True)
with zipfile.ZipFile(tmp / updater.ASSET, "w") as z:
    z.writestr(f"{app_name}/new.txt", "v9")

releases = {"version": "9.0.0", "assets": {}}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(releases).encode() if self.path == "/latest" else (tmp / updater.ASSET).read_bytes()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}"
releases["assets"][updater.ASSET] = f"{base}/{updater.ASSET}"

assert updater._parse("v0.10.0") > updater._parse("0.9.3")
assert updater.check() is None  # running from source, no override: never updates

os.environ["BETTERANKI_UPDATE_URL"] = f"{base}/latest"
u = updater.check()
assert u and u["version"] == "9.0.0", u

releases["version"] = updater.__version__
assert updater.check() is None  # same version: nothing to do
releases["version"] = "9.0.0"

swapped = {}
updater.app_dir = lambda: tmp / "Applications" / app_name
updater._start_swap = lambda target, new, staging: swapped.update(target=target, new=new)
updater.install(u)
assert swapped["target"] == tmp / "Applications" / app_name
assert (swapped["new"] / "new.txt").read_text() == "v9"
assert swapped["new"].parent == tmp / "Applications" / ".BetterAnki-update"

os.environ["BETTERANKI_UPDATE_URL"] = "http://127.0.0.1:1/latest"  # offline
assert updater.check() is None
try:
    updater.check(manual=True)
    raise AssertionError("manual check must report the error")
except RuntimeError as e:
    assert "fehlgeschlagen" in str(e)

srv.shutdown()

if sys.platform == "win32":
    # The real swap on Windows, started the way the app starts it: from a process whose working directory is
    # the app folder (double-click in Explorer). Windows can't rename a folder some process is standing in.
    import subprocess
    import time

    import importlib

    importlib.reload(updater)  # undo the stubs above
    app = tmp / "Programs" / "BetterAnki"
    app.mkdir(parents=True)
    (app / "old.txt").write_text("v1")
    staging = app.parent / ".BetterAnki-update"
    (staging / "BetterAnki").mkdir(parents=True)
    (staging / "BetterAnki" / "new.txt").write_text("v2")
    fake_app = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(2)"])
    os.chdir(app)
    updater._start_swap(app, staging / "BetterAnki", staging, pid=fake_app.pid)
    os.chdir(tmp)
    fake_app.wait()
    for _ in range(60):
        if (app / "new.txt").exists() and not staging.exists():
            break
        time.sleep(0.5)
    assert (app / "new.txt").exists() and not (app / "old.txt").exists(), (updater.take_failure(), sorted(p.name for p in app.parent.iterdir()))
    assert updater.take_failure() is None

print("updater ok")

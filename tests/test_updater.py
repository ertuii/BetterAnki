"""Updater: finds a newer release on a fake server, downloads and unpacks it next to the app."""

import http.server
import json
import os
import sys
import tempfile
import threading
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from betteranki import updater  # noqa: E402

tmp = Path(tempfile.mkdtemp())
app_name = "BetterAnki" if sys.platform == "win32" else "BetterAnki.app"
(tmp / "Applications" / app_name).mkdir(parents=True)
with zipfile.ZipFile(tmp / updater.ASSET, "w") as z:
    z.writestr(f"{app_name}/new.txt", "v9")

releases = {"tag_name": "v9.0.0", "body": "Neu", "assets": [{"name": updater.ASSET, "browser_download_url": None}]}


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
releases["assets"][0]["browser_download_url"] = f"{base}/{updater.ASSET}"

assert updater._parse("v0.10.0") > updater._parse("0.9.3")
assert updater.check() is None  # running from source, no override: never updates

os.environ["BETTERANKI_UPDATE_URL"] = f"{base}/latest"
u = updater.check()
assert u and u["version"] == "9.0.0" and u["notes"] == "Neu", u

releases["tag_name"] = "v" + updater.__version__
assert updater.check() is None  # same version: nothing to do
releases["tag_name"] = "v9.0.0"

swapped = {}
updater.app_dir = lambda: tmp / "Applications" / app_name
updater._start_swap = lambda target, new, staging: swapped.update(target=target, new=new)
updater.install(u)
assert swapped["target"] == tmp / "Applications" / app_name
assert (swapped["new"] / "new.txt").read_text() == "v9"
assert swapped["new"].parent == tmp / "Applications" / ".BetterAnki-update"

srv.shutdown()
print("updater ok")

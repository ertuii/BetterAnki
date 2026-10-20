import sys

__version__ = "0.2.2"  # keep in sync with pyproject.toml; a release tag is v<this>


def main() -> None:
    if "--mcp" in sys.argv:
        from .mcp_server import run
    else:
        from .app import run
    run()

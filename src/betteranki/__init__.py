import sys


def main() -> None:
    if "--mcp" in sys.argv:
        from .mcp_server import run
    else:
        from .app import run
    run()

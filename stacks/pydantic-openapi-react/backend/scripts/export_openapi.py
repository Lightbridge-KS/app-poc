"""Dump the OpenAPI document without booting a server.

Importing the app and calling `app.openapi()` is the whole trick: it is fast,
needs no port, and works identically on a laptop and in CI.

    uv run python scripts/export_openapi.py [OUT_PATH]
"""

import json
import sys
from pathlib import Path

from app.main import app

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "openapi.json"


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    # Trailing newline keeps the committed artifact diff-friendly.
    out.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

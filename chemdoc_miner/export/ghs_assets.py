from __future__ import annotations

import base64
import json
from pathlib import Path

GHS_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "ghs"


def ghs_pictogram_json() -> str:
    uris: dict[str, str] = {}
    for path in sorted(GHS_ASSETS_DIR.glob("GHS*.svg")):
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        uris[path.stem.upper()] = f"data:image/svg+xml;base64,{encoded}"
    return json.dumps(uris, ensure_ascii=False)

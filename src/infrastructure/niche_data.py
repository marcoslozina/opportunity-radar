from __future__ import annotations
import json
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "niche_keywords.json"


def load_niche_keywords() -> dict[str, list[str]]:
    """Load niche keywords from JSON. Falls back to empty dict if file missing."""
    try:
        return json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}

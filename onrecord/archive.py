"""Coda, archivio, vincoli di equilibrio e numerazione della fanzine."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .models import Story

STRANDS = ["palco", "studio", "privata", "emozione"]
ITALIAN_WINDOW = 10
STRAND_WINDOW = 8


def story_key(artist: str, song: Optional[str], strand: str) -> str:
    def norm(s: Optional[str]) -> str:
        text = re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()
        return re.sub(r"^(the|i|gli|le|la|il|lo) ", "", text)
    return f"{norm(artist)}|{norm(song)}|{strand}"


def _read_items(root: Path, folder: str, meta_file: str, sort_key: str) -> List[Dict]:
    items = []
    for meta_path in sorted((Path(root) / folder).glob(f"*/{meta_file}")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["_path"] = str(meta_path.parent)
        items.append(meta)
    return sorted(items, key=lambda m: m.get(sort_key, ""))


def published_index(root: Path) -> List[Dict]:
    return _read_items(root, "archive", "published.json", "published_at")


def queue_index(root: Path) -> List[Dict]:
    return _read_items(root, "queue", "manifest.json", "created_at")


def _sequence(root: Path) -> List[Dict]:
    """Ordine in cui il pubblico vedrà i caroselli: pubblicati, poi la coda."""
    return published_index(root) + queue_index(root)


def next_constraints(root: Path) -> Dict:
    seq = _sequence(root)
    last = seq[-1] if seq else None
    recent_strands = [m["strand"] for m in seq[-STRAND_WINDOW:]]
    preferred = min(STRANDS, key=lambda s: (recent_strands.count(s), STRANDS.index(s)))
    window = seq[-ITALIAN_WINDOW:]
    need_italian = len(window) >= ITALIAN_WINDOW - 1 and not any(m.get("italian") for m in window)
    return {
        "avoid_artists": [last["artist"]] if last else [],
        "avoid_decade": last["decade"] if last else None,
        "need_italian": need_italian,
        "preferred_strand": preferred,
        "used_keys": [m["key"] for m in seq],
    }


def is_duplicate(story: Story, root: Path) -> bool:
    key = story_key(story.artist, story.song, story.strand)
    return any(m["key"] == key for m in _sequence(root))


def next_issue_number(root: Path) -> int:
    return len(published_index(root)) + len(queue_index(root)) + 1


def enqueue(story_dir: Path, root: Path) -> Path:
    dest = Path(root) / "queue" / Path(story_dir).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(story_dir), str(dest))
    return dest


def dequeue_oldest(root: Path) -> Optional[Path]:
    ready = [m for m in queue_index(root) if m.get("status") == "ready"]
    return Path(ready[0]["_path"]) if ready else None


def queue_item(root: Path, item_id: str) -> Optional[Path]:
    """Un carosello pronto della coda, scelto per id (cartella)."""
    for meta in queue_index(root):
        if meta.get("status") == "ready" and Path(meta["_path"]).name == item_id:
            return Path(meta["_path"])
    return None


def archive_item(item: Path, media_id: str, root: Path, slot: Optional[str] = None) -> Path:
    meta = json.loads((Path(item) / "manifest.json").read_text(encoding="utf-8"))
    dest = Path(root) / "archive" / Path(item).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(item), str(dest))
    meta.pop("status", None)
    meta.update({
        "media_id": media_id,
        "slot": slot,
        "published_at": datetime.now(timezone.utc).isoformat(),
    })
    (dest / "published.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest

"""Comandi: constraints, build (più avanti: publish, refresh-token)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from . import archive, instagram
from .caption import CaptionTooLongError, build_caption
from .config import load_config
from .models import Story, load_story
from .photos import Photo, resolve_photo
from .render import SlideOverflowError, render_story
from .schedule import alerts, due_slot
from .sources import unreachable_sources
from .validate import validate_story


def _consecutive_errors(story: Story, root: Path) -> List[str]:
    queued = archive.queue_index(root)
    previous = queued[-1] if queued else (archive.published_index(root) or [None])[-1]
    if not previous:
        return []
    errors = []
    if previous["artist"].strip().lower() == story.artist.strip().lower():
        errors.append(f"stesso artista del carosello precedente: {story.artist}")
    if previous["decade"] == story.decade:
        errors.append(f"stesso decennio del carosello precedente: {story.decade}")
    return errors


def _resolve_photos(story: Story, dest: Path) -> Dict[int, List[Photo]]:
    photos: Dict[int, List[Photo]] = {}
    for i, slide in enumerate(story.slides):
        found = [resolve_photo(req, dest) for req in slide.photos]
        photos[i] = [p for p in found if p is not None]
    if not photos.get(0) and story.slides[0].kind == "cover":
        story.slides[0].kind = "nophoto_cover"
    return photos


def build(story_dir: Path, root: Path, render: bool = True) -> int:
    story_dir, root = Path(story_dir), Path(root)
    story = load_story(story_dir / "story.json")
    errors = validate_story(story)
    if archive.is_duplicate(story, root):
        errors.append("storia già pubblicata o già in coda")
    errors += _consecutive_errors(story, root)
    if not errors:
        errors += unreachable_sources(story)
    if errors:
        print("Carosello scartato:\n- " + "\n- ".join(errors))
        return 1

    if not render:
        # Solo verifica: le foto si scaricano in una cartella temporanea, non nel branch della routine.
        with tempfile.TemporaryDirectory() as tmp:
            _resolve_photos(story, Path(tmp))
        print(f"Storia valida: {story.id}")
        return 0
    photos = _resolve_photos(story, story_dir / "photos")

    cfg = load_config(root)
    issue = archive.next_issue_number(root) + cfg.first_issue - 1
    flat_photos = [p for ps in photos.values() for p in ps]
    try:
        caption = build_caption(story, flat_photos, handle=cfg.handle)
        render_story(story, photos, issue=issue, out_dir=story_dir / "slides", handle=cfg.handle)
    except (CaptionTooLongError, SlideOverflowError) as exc:
        print(f"Carosello scartato:\n- {exc}")
        return 1

    (story_dir / "story.json").write_text(story.model_dump_json(indent=2), encoding="utf-8")
    (story_dir / "caption.txt").write_text(caption, encoding="utf-8")
    manifest = {
        "id": story.id, "artist": story.artist, "song": story.song, "decade": story.decade,
        "strand": story.strand, "italian": story.italian,
        "key": archive.story_key(story.artist, story.song, story.strand),
        "issue": issue, "status": "ready", "created_at": datetime.now(timezone.utc).isoformat(),
        "photos": [{"author": p.author, "license": p.license, "source_url": p.source_url} for p in flat_photos],
    }
    (story_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    dest = archive.enqueue(story_dir, root)
    print(f"In coda: {dest}")
    return 0


def _load_state(root: Path) -> Dict:
    path = root / "state.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _save_state(root: Path, state: Dict) -> None:
    (root / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


def _fail_with_alerts(messages: List[str]) -> int:
    # Il workflow fallisce e GitHub manda l'email di avviso al proprietario del repository.
    print("AVVISO 50onrecord:\n- " + "\n- ".join(messages))
    return 1


def publish(root: Path, now: Optional[datetime] = None, dry_run: bool = False) -> int:
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    cfg = load_config(root)
    state = _load_state(root)
    last = state.get("last_published_utc")
    last_dt = datetime.fromisoformat(last) if last else None
    ready = [m for m in archive.queue_index(root) if m.get("status") == "ready"]
    slot = due_slot(now, cfg, len(ready), last_dt)
    if slot is None:
        print("Nessuna pubblicazione prevista in questo momento.")
        return 0

    token_expires = datetime.fromisoformat(os.environ["IG_TOKEN_EXPIRES"])
    item = archive.dequeue_oldest(root)
    if item is None:
        state["consecutive_skips"] = state.get("consecutive_skips", 0) + 1
        _save_state(root, state)
        return _fail_with_alerts(alerts({**state, "queue_ready": 0}, now, token_expires))

    base = os.environ["ONRECORD_RAW_BASE"].rstrip("/")
    rel = item.relative_to(root).as_posix()
    urls = [f"{base}/{rel}/slides/{p.name}" for p in sorted((item / "slides").glob("*.jpg"))]
    caption = (item / "caption.txt").read_text(encoding="utf-8")
    if dry_run:
        print(f"[prova] slot {slot}\n" + "\n".join(urls) + "\n\n" + caption)
        return 0

    try:
        media_id = instagram.publish_carousel(urls, caption, os.environ["IG_USER_ID"], os.environ["IG_TOKEN"])
    except instagram.PublishError as exc:
        state["consecutive_skips"] = state.get("consecutive_skips", 0) + 1
        _save_state(root, state)
        return _fail_with_alerts([f"pubblicazione rifiutata: {exc}"]
                                 + alerts({**state, "queue_ready": len(ready)}, now, token_expires))

    archive.archive_item(item, media_id, root, slot=slot)
    state.update({"consecutive_skips": 0, "last_published_utc": now.isoformat()})
    _save_state(root, state)
    print(f"Pubblicato {item.name} come {media_id} (slot {slot})")
    remaining = alerts({**state, "queue_ready": len(ready) - 1}, now, token_expires)
    # La coda che si svuota con questo post non è ancora un problema: lo diventa al prossimo slot.
    remaining = [a for a in remaining if not a.startswith("coda vuota")]
    return _fail_with_alerts(remaining) if remaining else 0


def refresh(out_dir: Path) -> int:
    token, expires = instagram.refresh_token(os.environ["IG_TOKEN"])
    out_dir.mkdir(parents=True, exist_ok=True)
    # Mai stampare il token nei log: lo legge il workflow da file.
    (out_dir / "token.txt").write_text(token, encoding="utf-8")
    (out_dir / "expires.txt").write_text(expires.isoformat(), encoding="utf-8")
    print(f"Token rinnovato, scade il {expires.date().isoformat()}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="onrecord")
    sub = parser.add_subparsers(dest="command", required=True)
    p_build = sub.add_parser("build")
    p_build.add_argument("story_dir")
    p_build.add_argument("--root", default=".")
    p_build.add_argument("--no-render", action="store_true")
    p_cons = sub.add_parser("constraints")
    p_cons.add_argument("--root", default=".")
    p_pub = sub.add_parser("publish")
    p_pub.add_argument("--root", default=".")
    p_pub.add_argument("--dry-run", action="store_true")
    p_ref = sub.add_parser("refresh-token")
    p_ref.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    if args.command == "publish":
        return publish(Path(args.root), dry_run=args.dry_run)
    if args.command == "refresh-token":
        return refresh(Path(args.out_dir))

    if args.command == "build":
        return build(Path(args.story_dir), Path(args.root), render=not args.no_render)
    if args.command == "constraints":
        print(json.dumps(archive.next_constraints(Path(args.root)), ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())

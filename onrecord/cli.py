"""Comandi: constraints, build (più avanti: publish, refresh-token)."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from . import archive
from .caption import CaptionTooLongError, build_caption
from .config import load_config
from .models import Story, load_story
from .photos import Photo, resolve_photo
from .render import SlideOverflowError, render_story
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


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="onrecord")
    sub = parser.add_subparsers(dest="command", required=True)
    p_build = sub.add_parser("build")
    p_build.add_argument("story_dir")
    p_build.add_argument("--root", default=".")
    p_build.add_argument("--no-render", action="store_true")
    p_cons = sub.add_parser("constraints")
    p_cons.add_argument("--root", default=".")
    args = parser.parse_args(argv)

    if args.command == "build":
        return build(Path(args.story_dir), Path(args.root), render=not args.no_render)
    if args.command == "constraints":
        print(json.dumps(archive.next_constraints(Path(args.root)), ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())

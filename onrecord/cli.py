"""Comandi: constraints, build, publish, check-instagram, gate-check."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import ValidationError

from . import archive, instagram
from .caption import CaptionTooLongError, build_caption
from .config import load_config
from .gate import branch_violations
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
        found = [resolve_photo(req, dest, subject=req.subject or story.artist) for req in slide.photos]
        photos[i] = [p for p in found if p is not None]
    if not photos.get(0) and story.slides[0].kind == "cover":
        story.slides[0].kind = "nophoto_cover"
    return photos


def build(story_dir: Path, root: Path, render: bool = True) -> int:
    """0 = in coda, 1 = storia scartata (regole), 2 = errore tecnico (la storia va conservata)."""
    try:
        return _build(Path(story_dir), Path(root), render)
    except Exception as exc:  # rete, Commons, browser: non sono violazioni delle regole
        print(f"Carosello non elaborato per un errore tecnico: {type(exc).__name__}: {exc}")
        return 2


def _build(story_dir: Path, root: Path, render: bool) -> int:
    try:
        story = load_story(story_dir / "story.json")
    except (ValidationError, ValueError) as exc:  # file non conforme: va scartato, non riprovato
        print(f"Carosello scartato:\n- story.json non valido: {exc}")
        return 1
    errors = validate_story(story)
    for folder in ("queue", "archive"):
        if (root / folder / story_dir.name).exists():
            errors.append(f"la cartella {folder}/{story_dir.name} esiste già: usa un id diverso")
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
    cfg = load_config(root)
    issue = archive.next_issue_number(root) + cfg.first_issue - 1
    # Foto originali e HTML intermedio restano fuori dal repository: in coda vanno solo i JPEG finali.
    with tempfile.TemporaryDirectory() as tmp:
        photos = _resolve_photos(story, Path(tmp))
        flat_photos = [p for ps in photos.values() for p in ps]
        try:
            caption = build_caption(story, flat_photos, handle=cfg.handle)
            render_story(story, photos, issue=issue, out_dir=story_dir / "slides", handle=cfg.handle)
        except (CaptionTooLongError, SlideOverflowError) as exc:
            print(f"Carosello scartato:\n- {exc}")
            return 1
        finally:
            shutil.rmtree(story_dir / "slides" / "html", ignore_errors=True)

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


def _secret(name: str) -> str:
    """Valore di un segreto senza spazi o "a capo" copiati per sbaglio insieme al codice."""
    return os.environ[name].strip()


def _load_state(root: Path) -> Dict:
    path = root / "state.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _save_state(root: Path, state: Dict) -> None:
    (root / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


def _fail_with_alerts(messages: List[str]) -> int:
    # Il workflow fallisce e GitHub manda l'email di avviso al proprietario del repository.
    print("AVVISO 50onrecord:\n- " + "\n- ".join(messages))
    return 1


MAX_ITEM_FAILED_SLOTS = 2


def _count_skip(state: Dict, slot: str) -> None:
    """Uno slot saltato conta una volta sola, anche se nella sua finestra si riprova più volte."""
    if state.get("last_skipped_slot") != slot:
        state["consecutive_skips"] = state.get("consecutive_skips", 0) + 1
        state["last_skipped_slot"] = slot


def _record_item_failure(item: Path, slot: str) -> bool:
    """Un carosello che fallisce in due slot diversi viene messo da parte, così non blocca la coda."""
    path = item / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    failed = manifest.setdefault("failed_slots", [])
    if slot not in failed:
        failed.append(slot)
    set_aside = len(failed) >= MAX_ITEM_FAILED_SLOTS
    if set_aside:
        manifest["status"] = "failed"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return set_aside


def _mark_published(root: Path, state: Dict, item: Path, media_id: str, slot: str, now: datetime) -> None:
    archive.archive_item(item, media_id, root, slot=slot)
    state.pop("pending", None)
    state.update({"consecutive_skips": 0, "last_published_utc": now.isoformat()})
    _save_state(root, state)
    print(f"Pubblicato {item.name} come {media_id} (slot {slot})")


def _resolve_pending(root: Path, state: Dict, now: datetime) -> Optional[int]:
    """Un tentativo precedente si è interrotto dopo aver preparato il carosello: mai ripubblicare alla cieca."""
    pending = state["pending"]
    item = root / "queue" / pending["item"]
    token = _secret("IG_TOKEN")
    try:
        status = instagram.container_status(pending["container"], token)
        if status == "PUBLISHED":
            media_id = pending["container"]
        elif status == "FINISHED" and item.exists():
            media_id = instagram.publish_container(_secret("IG_USER_ID"), pending["container"], token)
        else:
            state.pop("pending")
            _save_state(root, state)
            return None
    except instagram.PublishError as exc:
        return _fail_with_alerts([f"impossibile verificare la pubblicazione precedente: {exc}"])
    if item.exists():
        _mark_published(root, state, item, media_id, pending["slot"], now)
    else:
        state.pop("pending")
        _save_state(root, state)
    return 0


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

    # Il token dell'utente di sistema non scade: senza IG_TOKEN_EXPIRES non c'è nulla da avvisare.
    expires = os.environ.get("IG_TOKEN_EXPIRES")
    token_expires = datetime.fromisoformat(expires) if expires else datetime.max.replace(tzinfo=timezone.utc)
    if state.get("pending") and not dry_run:
        resolved = _resolve_pending(root, state, now)
        if resolved is not None:
            return resolved
    item = archive.dequeue_oldest(root)
    if item is None:
        _count_skip(state, slot)
        _save_state(root, state)
        return _fail_with_alerts(alerts({**state, "queue_ready": 0}, now, token_expires))

    base = os.environ["ONRECORD_RAW_BASE"].rstrip("/")
    rel = item.relative_to(root).as_posix()
    urls = [f"{base}/{rel}/slides/{p.name}" for p in sorted((item / "slides").glob("*.jpg"))]
    caption = (item / "caption.txt").read_text(encoding="utf-8")
    if dry_run:
        print(f"[prova] slot {slot}\n" + "\n".join(urls) + "\n\n" + caption)
        return 0

    def remember_container(container_id: str) -> None:
        state["pending"] = {"item": item.name, "container": container_id, "slot": slot}
        _save_state(root, state)

    try:
        media_id = instagram.publish_carousel(urls, caption, _secret("IG_USER_ID"), _secret("IG_TOKEN"),
                                              on_container=remember_container)
    except instagram.PublishError as exc:
        _count_skip(state, slot)
        _save_state(root, state)
        set_aside = _record_item_failure(item, slot)
        notes = [f"carosello {item.name} messo da parte dopo {MAX_ITEM_FAILED_SLOTS} slot falliti"] if set_aside else []
        return _fail_with_alerts([f"pubblicazione rifiutata: {exc}"] + notes
                                 + alerts({**state, "queue_ready": len(ready)}, now, token_expires))

    _mark_published(root, state, item, media_id, slot, now)
    remaining = alerts({**state, "queue_ready": len(ready) - 1}, now, token_expires)
    # La coda che si svuota con questo post non è ancora un problema: lo diventa al prossimo slot.
    remaining = [a for a in remaining if not a.startswith("coda vuota")]
    return _fail_with_alerts(remaining) if remaining else 0


def check_instagram() -> int:
    try:
        info = instagram.check_connection(_secret("IG_USER_ID"), _secret("IG_TOKEN"))
    except instagram.PublishError as exc:
        print(f"Collegamento a Instagram non riuscito: {exc}")
        return 1
    print(f"Collegamento riuscito: @{info['username']}, quota di pubblicazione {info['quota_usage']}/{info['quota_total']}")
    return 0


def prepare_instagram(root: Path) -> int:
    """Prova senza pubblicare: Meta scarica le slide del prossimo carosello e le elabora; nulla va online."""
    root = Path(root)
    item = archive.dequeue_oldest(root)
    if item is None:
        print("Nessun carosello in coda da provare.")
        return 1
    base = os.environ["ONRECORD_RAW_BASE"].rstrip("/")
    rel = item.relative_to(root).as_posix()
    urls = [f"{base}/{rel}/slides/{p.name}" for p in sorted((item / "slides").glob("*.jpg"))]
    caption = (item / "caption.txt").read_text(encoding="utf-8")
    try:
        container = instagram.prepare_carousel(urls, caption, _secret("IG_USER_ID"), _secret("IG_TOKEN"))
    except instagram.PublishError as exc:
        print(f"Prova non riuscita per {item.name}: {exc}")
        return 1
    print(f"Prova riuscita: {item.name} è pronto su Meta ({len(urls)} slide, contenitore {container}). Non pubblicato.")
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
    p_prep = sub.add_parser("prepare-instagram", help="prova: Meta elabora il prossimo carosello senza pubblicarlo")
    p_prep.add_argument("--root", default=".")
    sub.add_parser("check-instagram", help="prova di sola lettura del collegamento a Instagram")
    sub.add_parser("gate-check", help="legge da stdin i file modificati dal branch della routine")
    args = parser.parse_args(argv)

    if args.command == "gate-check":
        violations = branch_violations(sys.stdin.read().splitlines())
        if violations:
            print("Il branch modifica file non consentiti:\n- " + "\n- ".join(violations))
            return 1
        return 0
    if args.command == "publish":
        return publish(Path(args.root), dry_run=args.dry_run)
    if args.command == "prepare-instagram":
        return prepare_instagram(Path(args.root))
    if args.command == "check-instagram":
        return check_instagram()

    if args.command == "build":
        return build(Path(args.story_dir), Path(args.root), render=not args.no_render)
    if args.command == "constraints":
        print(json.dumps(archive.next_constraints(Path(args.root)), ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())

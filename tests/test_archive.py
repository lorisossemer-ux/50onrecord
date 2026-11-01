import json
from pathlib import Path

from onrecord import archive
from onrecord.models import Story

STRANDS = ["palco", "studio", "privata", "emozione"]


def _write(root: Path, folder: str, idx: int, artist: str, decade: str = "70", strand: str = "studio",
           italian: bool = False, song: str = "Song"):
    item = root / folder / f"item-{idx:03d}"
    item.mkdir(parents=True)
    meta = {"id": item.name, "artist": artist, "song": song, "decade": decade, "strand": strand,
            "italian": italian, "key": archive.story_key(artist, song, strand)}
    if folder == "archive":
        meta["published_at"] = f"2026-12-{idx:02d}T19:30:00+00:00"
        (item / "published.json").write_text(json.dumps(meta))
    else:
        meta["created_at"] = f"2026-11-{idx:02d}T03:00:00+00:00"
        meta["status"] = "ready"
        (item / "manifest.json").write_text(json.dumps(meta))
    return item


def test_last_artist_and_decade_avoided(tmp_path):
    _write(tmp_path, "archive", 1, "Queen", decade="80")
    _write(tmp_path, "archive", 2, "The Police", decade="70")
    c = archive.next_constraints(tmp_path)
    assert "The Police" in c["avoid_artists"]
    assert c["avoid_decade"] == "70"


def test_queue_counts_after_archive(tmp_path):
    _write(tmp_path, "archive", 1, "The Police", decade="70")
    _write(tmp_path, "queue", 2, "Nirvana", decade="90")
    c = archive.next_constraints(tmp_path)
    assert c["avoid_decade"] == "90"
    assert "Nirvana" in c["avoid_artists"]


def test_need_italian_after_nine_foreign(tmp_path):
    for i in range(1, 10):
        _write(tmp_path, "archive", i, f"Artist {i}")
    assert archive.next_constraints(tmp_path)["need_italian"] is True


def test_no_need_italian_when_one_in_last_ten(tmp_path):
    for i in range(1, 10):
        _write(tmp_path, "archive", i, f"Artist {i}", italian=(i == 4))
    assert archive.next_constraints(tmp_path)["need_italian"] is False


def test_preferred_strand_is_least_used(tmp_path):
    for i, strand in enumerate(["palco", "studio", "palco", "privata", "studio", "palco", "privata", "studio"], 1):
        _write(tmp_path, "archive", i, f"Artist {i}", strand=strand)
    assert archive.next_constraints(tmp_path)["preferred_strand"] == "emozione"


def test_duplicate_detected_in_queue(tmp_path, story_dict):
    story = Story(**story_dict)
    _write(tmp_path, "queue", 1, story.artist, song=story.song, strand=story.strand)
    assert archive.is_duplicate(story, tmp_path) is True


def test_not_duplicate_when_strand_differs(tmp_path, story_dict):
    story = Story(**story_dict)
    _write(tmp_path, "archive", 1, story.artist, song=story.song, strand="palco")
    assert archive.is_duplicate(story, tmp_path) is False


def test_next_issue_number(tmp_path):
    _write(tmp_path, "archive", 1, "A")
    _write(tmp_path, "archive", 2, "B")
    _write(tmp_path, "queue", 3, "C")
    assert archive.next_issue_number(tmp_path) == 4


def test_dequeue_oldest(tmp_path):
    _write(tmp_path, "queue", 5, "Later")
    oldest = _write(tmp_path, "queue", 2, "Earlier")
    assert archive.dequeue_oldest(tmp_path) == oldest


def test_dequeue_empty(tmp_path):
    assert archive.dequeue_oldest(tmp_path) is None


def test_archive_item_moves_and_records(tmp_path):
    item = _write(tmp_path, "queue", 1, "The Police")
    dest = archive.archive_item(item, "1789", tmp_path, slot="2026-12-01T20:30")
    assert not item.exists()
    published = json.loads((dest / "published.json").read_text())
    assert published["media_id"] == "1789"
    assert published["slot"] == "2026-12-01T20:30"
    assert archive.published_index(tmp_path)[-1]["artist"] == "The Police"

import json
import shutil
from pathlib import Path

import pytest
import responses

from onrecord import cli
from onrecord.photos import API_URL
from conftest import FIXTURES

ROOT = Path(__file__).parent.parent
IMG_URL = "https://upload.wikimedia.org/wikipedia/commons/3/31/Sting_Atlanta_3.jpg"


@pytest.fixture
def repo(tmp_path):
    shutil.copy(ROOT / "config.toml", tmp_path / "config.toml")
    return tmp_path


def _incoming(repo, story):
    d = repo / "incoming" / story["id"]
    d.mkdir(parents=True)
    (d / "story.json").write_text(json.dumps(story, ensure_ascii=False), encoding="utf-8")
    return d


def _mock_commons(fixture="commons_sting.json"):
    responses.add(responses.GET, API_URL, body=(FIXTURES / fixture).read_text(), content_type="application/json")
    responses.add(responses.GET, IMG_URL, body=(ROOT / "docs/mockup/img/sting_live.jpg").read_bytes(),
                  content_type="image/jpeg")


def _published(repo, artist, decade):
    d = repo / "archive" / "old"
    d.mkdir(parents=True)
    (d / "published.json").write_text(json.dumps({
        "id": "old", "artist": artist, "song": "x", "decade": decade, "strand": "palco", "italian": False,
        "key": f"{artist.lower()}|x|palco", "published_at": "2026-12-01T19:30:00+00:00"}))


def test_build_rejects_invalid_story(repo, story_dict, capsys):
    story_dict["facts"][0]["sources"] = story_dict["facts"][0]["sources"][:1]
    d = _incoming(repo, story_dict)
    assert cli.main(["build", str(d), "--root", str(repo)]) == 1
    assert "2 fonti indipendenti" in capsys.readouterr().out
    assert not (repo / "queue").exists()


@pytest.mark.parametrize("artist,decade,message", [
    ("The Police", "80", "stesso artista"),
    ("Queen", "70", "stesso decennio"),
])
def test_build_rejects_consecutive_artist_or_decade(repo, story_dict, capsys, artist, decade, message):
    _published(repo, artist, decade)
    d = _incoming(repo, story_dict)
    assert cli.main(["build", str(d), "--root", str(repo)]) == 1
    assert message in capsys.readouterr().out


@responses.activate
def test_build_happy_path(repo, story_dict):
    _mock_commons()
    d = _incoming(repo, story_dict)
    assert cli.main(["build", str(d), "--root", str(repo)]) == 0
    item = repo / "queue" / story_dict["id"]
    manifest = json.loads((item / "manifest.json").read_text())
    assert manifest["status"] == "ready"
    assert manifest["issue"] == 1
    assert len(list((item / "slides").glob("*.png"))) == len(story_dict["slides"])
    assert "Acroterion" in (item / "caption.txt").read_text()
    assert not d.exists()


@responses.activate
def test_build_without_photos_uses_nophoto_cover(repo, story_dict):
    responses.add(responses.GET, API_URL, body=(FIXTURES / "commons_empty.json").read_text(),
                  content_type="application/json")
    d = _incoming(repo, story_dict)
    assert cli.main(["build", str(d), "--root", str(repo)]) == 0
    story = json.loads((repo / "queue" / story_dict["id"] / "story.json").read_text())
    assert story["slides"][0]["kind"] == "nophoto_cover"


@responses.activate
def test_build_no_render_validates_only(repo, story_dict):
    _mock_commons()
    d = _incoming(repo, story_dict)
    assert cli.main(["build", str(d), "--root", str(repo), "--no-render"]) == 0
    assert d.exists()
    assert not list(d.rglob("*.png"))
    assert not (d / "photos").exists()
    assert not (repo / "queue").exists()

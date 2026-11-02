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


def _mock_sources(story):
    for url in {s["url"] for f in story["facts"] for s in f["sources"]}:
        responses.add(responses.GET, url, status=200)


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
    _mock_sources(story_dict)
    d = _incoming(repo, story_dict)
    assert cli.main(["build", str(d), "--root", str(repo)]) == 0
    item = repo / "queue" / story_dict["id"]
    manifest = json.loads((item / "manifest.json").read_text())
    assert manifest["status"] == "ready"
    assert manifest["issue"] == 1
    assert len(list((item / "slides").glob("*.jpg"))) == len(story_dict["slides"])
    assert "Acroterion" in (item / "caption.txt").read_text()
    assert not d.exists()


@responses.activate
def test_build_without_photos_uses_nophoto_cover(repo, story_dict):
    _mock_sources(story_dict)
    responses.add(responses.GET, API_URL, body=(FIXTURES / "commons_empty.json").read_text(),
                  content_type="application/json")
    d = _incoming(repo, story_dict)
    assert cli.main(["build", str(d), "--root", str(repo)]) == 0
    story = json.loads((repo / "queue" / story_dict["id"] / "story.json").read_text())
    assert story["slides"][0]["kind"] == "nophoto_cover"


@responses.activate
def test_build_no_render_validates_only(repo, story_dict):
    _mock_commons()
    _mock_sources(story_dict)
    d = _incoming(repo, story_dict)
    assert cli.main(["build", str(d), "--root", str(repo), "--no-render"]) == 0
    assert d.exists()
    assert not list(d.rglob("*.jpg"))
    assert not (d / "photos").exists()
    assert not (repo / "queue").exists()


@responses.activate
def test_build_rejects_dead_source(repo, story_dict, capsys):
    _mock_commons()
    urls = sorted({s["url"] for f in story_dict["facts"] for s in f["sources"]})
    for url in urls[1:]:
        responses.add(responses.GET, url, status=200)
    responses.add(responses.GET, urls[0], status=404)
    d = _incoming(repo, story_dict)
    assert cli.main(["build", str(d), "--root", str(repo)]) == 1
    assert "fonte non raggiungibile" in capsys.readouterr().out


@responses.activate
def test_build_infrastructure_error_returns_2_and_keeps_story(repo, story_dict, capsys):
    _mock_sources(story_dict)
    responses.add(responses.GET, API_URL, status=503, body="<html>busy</html>")
    d = _incoming(repo, story_dict)
    assert cli.main(["build", str(d), "--root", str(repo)]) == 2
    assert d.exists()
    assert "errore tecnico" in capsys.readouterr().out


def test_build_rejects_existing_folder_name(repo, story_dict, capsys):
    other = repo / "archive" / story_dict["id"]
    other.mkdir(parents=True)
    (other / "published.json").write_text(json.dumps({
        "id": story_dict["id"], "artist": "Queen", "song": "y", "decade": "80", "strand": "palco",
        "italian": False, "key": "queen|y|palco", "published_at": "2026-12-01T19:30:00+00:00"}))
    d = _incoming(repo, story_dict)
    assert cli.main(["build", str(d), "--root", str(repo)]) == 1
    assert "esiste già" in capsys.readouterr().out


@responses.activate
def test_queue_item_is_lightweight(repo, story_dict):
    _mock_commons()
    _mock_sources(story_dict)
    d = _incoming(repo, story_dict)
    assert cli.main(["build", str(d), "--root", str(repo)]) == 0
    item = repo / "queue" / story_dict["id"]
    assert not (item / "photos").exists()
    assert not (item / "slides" / "html").exists()


def test_build_rejects_story_not_matching_schema(repo, story_dict, capsys):
    del story_dict["listen_track"]
    d = _incoming(repo, story_dict)
    assert cli.main(["build", str(d), "--root", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "scartato" in out.lower()
    assert "listen_track" in out


def test_same_photo_is_not_repeated_across_slides(story_dict, tmp_path, monkeypatch):
    from onrecord import cli
    from onrecord.models import Story
    from onrecord.photos import Photo

    def fake_resolve(req, dest, subject=None):
        name = {"a": "Stessa.jpg", "b": "Altra.jpg"}[req.query]
        return Photo(path=tmp_path / name, author="X", license="CC BY 2.0",
                     source_url=f"https://commons.wikimedia.org/wiki/File:{name}", sharealike=False)

    monkeypatch.setattr(cli, "resolve_photo", fake_resolve)
    for slide in story_dict["slides"]:
        slide["photos"] = []
    story_dict["slides"][0]["photos"] = [{"query": "a", "role": "main"}, {"query": "a", "role": "side"}]
    story_dict["slides"][1]["photos"] = [{"query": "a", "role": "main"}]
    story_dict["slides"][2]["photos"] = [{"query": "b", "role": "main"}]
    story_dict["slides"][3]["photos"] = [{"query": "b", "role": "main"}]
    photos = cli._resolve_photos(Story(**story_dict), tmp_path)
    assert [p.source_url.rsplit(":", 1)[-1] for p in photos[0]] == ["Stessa.jpg"]   # il doppione in copertina cade
    assert photos[1] == []                                                         # già usata nella copertina
    assert [p.source_url.rsplit(":", 1)[-1] for p in photos[2]] == ["Altra.jpg"]
    assert photos[3] == []                                                         # già usata nella slide 3

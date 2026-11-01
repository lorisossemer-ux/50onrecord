import json
from datetime import datetime, timedelta, timezone

import pytest
import responses

from onrecord import cli, instagram
from onrecord.instagram import GRAPH, PublishError, publish_carousel, refresh_token

IG = "17841400000000000"
URLS = [f"https://raw.githubusercontent.com/o/50onrecord/main/queue/x/slides/{i:02d}.jpg" for i in range(1, 7)]


def _status(container_id, code):
    responses.add(responses.GET, f"{GRAPH}/{container_id}", json={"status_code": code, "id": container_id})


def _happy_path_mocks():
    for i in range(len(URLS)):
        responses.add(responses.POST, f"{GRAPH}/{IG}/media", json={"id": f"c{i}"})
    for i in range(len(URLS)):
        _status(f"c{i}", "FINISHED")
    responses.add(responses.POST, f"{GRAPH}/{IG}/media", json={"id": "carousel"})
    _status("carousel", "FINISHED")
    responses.add(responses.POST, f"{GRAPH}/{IG}/media_publish", json={"id": "MEDIA123"})


@responses.activate
def test_publish_happy_path_order():
    _happy_path_mocks()
    media_id = publish_carousel(URLS, "didascalia", IG, "TOKEN", poll_interval=0)
    assert media_id == "MEDIA123"
    posts = [c.request for c in responses.calls if c.request.method == "POST"]
    assert "is_carousel_item=true" in posts[0].body
    assert "image_url=" in posts[0].body
    carousel = posts[len(URLS)].body
    assert "media_type=CAROUSEL" in carousel and "children=c0%2Cc1" in carousel and "caption=" in carousel
    assert "creation_id=carousel" in posts[-1].body
    assert posts[0].headers["Authorization"] == "Bearer TOKEN"


@responses.activate
def test_stuck_container_raises():
    responses.add(responses.POST, f"{GRAPH}/{IG}/media", json={"id": "c0"})
    for _ in range(5):
        _status("c0", "IN_PROGRESS")
    with pytest.raises(PublishError):
        publish_carousel(URLS[:1] * 2, "x", IG, "TOKEN", poll_interval=0, max_polls=5)
    assert not any("media_publish" in c.request.url for c in responses.calls)


@responses.activate
def test_error_status_raises():
    responses.add(responses.POST, f"{GRAPH}/{IG}/media", json={"id": "c0"})
    _status("c0", "ERROR")
    with pytest.raises(PublishError):
        publish_carousel(URLS[:2], "x", IG, "TOKEN", poll_interval=0)


@responses.activate
def test_meta_error_message_carried():
    _happy_path_mocks()
    responses.replace(responses.POST, f"{GRAPH}/{IG}/media_publish", status=400,
                      json={"error": {"message": "Media ID is not available"}})
    with pytest.raises(PublishError, match="Media ID is not available"):
        publish_carousel(URLS, "x", IG, "TOKEN", poll_interval=0)


def test_too_many_images_rejected_before_http():
    with pytest.raises(ValueError):
        publish_carousel(URLS * 2, "x", IG, "TOKEN")


@responses.activate
def test_refresh_token():
    responses.add(responses.GET, "https://graph.instagram.com/refresh_access_token",
                  json={"access_token": "NEW", "token_type": "bearer", "expires_in": 5184000})
    token, expires = refresh_token("OLD", now=datetime(2026, 12, 1, tzinfo=timezone.utc))
    assert token == "NEW"
    assert expires == datetime(2027, 1, 30, tzinfo=timezone.utc)
    assert "grant_type=ig_refresh_token" in responses.calls[0].request.url


# --- comando publish -------------------------------------------------------------

@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / "config.toml").write_text(
        'handle = "@50onrecord"\ntimezone = "Europe/Rome"\nstart_date = "2026-12-01"\n'
        'phase1_days = 56\nphase1_slots = ["12:30", "20:30"]\nphase2_slots = ["20:30"]\nfirst_issue = 1\n')
    item = tmp_path / "queue" / "item-1"
    (item / "slides").mkdir(parents=True)
    for i in range(1, 7):
        (item / "slides" / f"{i:02d}.jpg").write_bytes(b"\xff\xd8")
    (item / "caption.txt").write_text("didascalia")
    (item / "manifest.json").write_text(json.dumps({
        "id": "item-1", "artist": "The Police", "song": "x", "decade": "70", "strand": "studio", "italian": False,
        "key": "k", "status": "ready", "created_at": "2026-11-30T03:00:00+00:00", "issue": 1}))
    monkeypatch.setenv("IG_USER_ID", IG)
    monkeypatch.setenv("IG_TOKEN", "TOKEN")
    monkeypatch.setenv("IG_TOKEN_EXPIRES", "2027-01-30T00:00:00+00:00")
    monkeypatch.setenv("ONRECORD_RAW_BASE", "https://raw.githubusercontent.com/o/50onrecord/main")
    return tmp_path


EVENING = datetime(2026, 12, 2, 19, 35, tzinfo=timezone.utc)  # 20:35 a Roma


def test_publish_dry_run_makes_no_post(repo, capsys):
    with responses.RequestsMock() as rsps:
        assert cli.publish(repo, now=EVENING, dry_run=True) == 0
        assert len(rsps.calls) == 0
    out = capsys.readouterr().out
    assert "https://raw.githubusercontent.com/o/50onrecord/main/queue/item-1/slides/01.jpg" in out
    assert "didascalia" in out
    assert (repo / "queue" / "item-1").exists()


def test_publish_nothing_due(repo, capsys):
    assert cli.publish(repo, now=datetime(2026, 12, 2, 15, 0, tzinfo=timezone.utc)) == 0
    assert (repo / "queue" / "item-1").exists()


@responses.activate
def test_publish_success_archives(repo, monkeypatch):
    monkeypatch.setattr(instagram, "publish_carousel", lambda urls, caption, ig, token: "MEDIA123")
    assert cli.publish(repo, now=EVENING) == 0
    published = json.loads((repo / "archive" / "item-1" / "published.json").read_text())
    assert published["media_id"] == "MEDIA123"
    assert published["slot"] == "2026-12-02T20:30"
    state = json.loads((repo / "state.json").read_text())
    assert state["consecutive_skips"] == 0


def test_publish_failure_keeps_item_and_counts_skip(repo, monkeypatch):
    def boom(*a, **k):
        raise PublishError("rifiutato")
    monkeypatch.setattr(instagram, "publish_carousel", boom)
    (repo / "state.json").write_text(json.dumps({"consecutive_skips": 1}))
    assert cli.publish(repo, now=EVENING) == 1
    assert (repo / "queue" / "item-1").exists()
    assert json.loads((repo / "state.json").read_text())["consecutive_skips"] == 2


def test_publish_empty_queue_alerts(repo):
    import shutil
    shutil.rmtree(repo / "queue" / "item-1")
    assert cli.publish(repo, now=EVENING) == 1


def test_publish_token_expiring_alerts_after_publishing(repo, monkeypatch):
    monkeypatch.setattr(instagram, "publish_carousel", lambda *a: "MEDIA123")
    monkeypatch.setenv("IG_TOKEN_EXPIRES", (EVENING + timedelta(days=3)).isoformat())
    assert cli.publish(repo, now=EVENING) == 1
    assert (repo / "archive" / "item-1").exists()

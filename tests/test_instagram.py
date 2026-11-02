import json
from datetime import datetime, timedelta, timezone

import pytest
import responses

from onrecord import cli, instagram
from onrecord.instagram import GRAPH, PublishError, check_connection, publish_carousel

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
    monkeypatch.setattr(instagram, "recent_captions", lambda ig_user_id, token, limit=10: [])
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
    monkeypatch.setattr(instagram, "publish_carousel", lambda urls, caption, ig, token, on_container=None: "MEDIA123")
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
    monkeypatch.setattr(instagram, "publish_carousel", lambda *a, **k: "MEDIA123")
    monkeypatch.setenv("IG_TOKEN_EXPIRES", (EVENING + timedelta(days=3)).isoformat())
    assert cli.publish(repo, now=EVENING) == 1
    assert (repo / "archive" / "item-1").exists()


# --- niente doppie pubblicazioni -----------------------------------------------------

@responses.activate
def test_hook_called_with_container_before_publish():
    _happy_path_mocks()
    seen = []

    def hook(container_id):
        seen.append((container_id, any("media_publish" in c.request.url for c in responses.calls)))

    publish_carousel(URLS, "x", IG, "TOKEN", poll_interval=0, on_container=hook)
    assert seen == [("carousel", False)]


@responses.activate
def test_network_timeout_becomes_publish_error():
    import requests as rq
    responses.add(responses.POST, f"{GRAPH}/{IG}/media", body=rq.exceptions.Timeout("lento"))
    with pytest.raises(PublishError):
        publish_carousel(URLS[:2], "x", IG, "TOKEN", poll_interval=0)


def _pending(repo, status_value, monkeypatch, calls):
    (repo / "state.json").write_text(json.dumps({
        "consecutive_skips": 1,
        "pending": {"item": "item-1", "container": "CONT9", "slot": "2026-12-02T20:30"}}))
    monkeypatch.setattr(instagram, "container_status", lambda cid, token: status_value)
    monkeypatch.setattr(instagram, "publish_container", lambda ig, cid, token: calls.append(cid) or "MEDIA9")

    def must_not_publish(*a, **k):
        raise AssertionError("ripubblicato!")
    return must_not_publish


def test_pending_already_published_is_archived_not_reposted(repo, monkeypatch):
    calls = []
    monkeypatch.setattr(instagram, "publish_carousel", _pending(repo, "PUBLISHED", monkeypatch, calls))
    assert cli.publish(repo, now=EVENING + timedelta(minutes=15)) == 0
    published = json.loads((repo / "archive" / "item-1" / "published.json").read_text())
    assert published["media_id"] == "CONT9"
    state = json.loads((repo / "state.json").read_text())
    assert "pending" not in state and state["consecutive_skips"] == 0
    assert calls == []


def test_pending_finished_is_published_once(repo, monkeypatch):
    calls = []
    monkeypatch.setattr(instagram, "publish_carousel", _pending(repo, "FINISHED", monkeypatch, calls))
    assert cli.publish(repo, now=EVENING + timedelta(minutes=15)) == 0
    assert calls == ["CONT9"]
    assert json.loads((repo / "archive" / "item-1" / "published.json").read_text())["media_id"] == "MEDIA9"


def test_pending_expired_is_cleared_and_normal_flow_runs(repo, monkeypatch):
    calls = []
    _pending(repo, "EXPIRED", monkeypatch, calls)
    monkeypatch.setattr(instagram, "publish_carousel", lambda urls, caption, ig, token, on_container=None: "NEW1")
    assert cli.publish(repo, now=EVENING + timedelta(minutes=15)) == 0
    assert json.loads((repo / "archive" / "item-1" / "published.json").read_text())["media_id"] == "NEW1"


def test_container_saved_before_publish_attempt(repo, monkeypatch):
    def fails_after_container(urls, caption, ig, token, on_container=None):
        on_container("CONT7")
        raise PublishError("timeout su media_publish")
    monkeypatch.setattr(instagram, "publish_carousel", fails_after_container)
    assert cli.publish(repo, now=EVENING) == 1
    state = json.loads((repo / "state.json").read_text())
    assert state["pending"]["container"] == "CONT7"
    assert (repo / "queue" / "item-1").exists()


# --- errori contati per slot e coda mai bloccata -------------------------------------

def _fail(monkeypatch):
    def boom(*a, **k):
        raise PublishError("rifiutato")
    monkeypatch.setattr(instagram, "publish_carousel", boom)


def test_same_slot_failure_counted_once(repo, monkeypatch):
    _fail(monkeypatch)
    cli.publish(repo, now=EVENING)
    cli.publish(repo, now=EVENING + timedelta(minutes=15))
    assert json.loads((repo / "state.json").read_text())["consecutive_skips"] == 1


def test_item_failing_in_two_slots_is_set_aside(repo, monkeypatch):
    second = repo / "queue" / "item-2"
    (second / "slides").mkdir(parents=True)
    for i in range(1, 7):
        (second / "slides" / f"{i:02d}.jpg").write_bytes(b"\xff\xd8")
    (second / "caption.txt").write_text("seconda")
    (second / "manifest.json").write_text(json.dumps({
        "id": "item-2", "artist": "Queen", "song": "y", "decade": "80", "strand": "palco", "italian": False,
        "key": "k2", "status": "ready", "created_at": "2026-11-30T04:00:00+00:00", "issue": 2}))
    _fail(monkeypatch)
    cli.publish(repo, now=EVENING)
    cli.publish(repo, now=EVENING + timedelta(days=1))
    manifest = json.loads((repo / "queue" / "item-1" / "manifest.json").read_text())
    assert manifest["status"] == "failed"
    published = []
    monkeypatch.setattr(instagram, "publish_carousel",
                        lambda urls, caption, ig, token, on_container=None: published.append(caption) or "M2")
    assert cli.publish(repo, now=EVENING + timedelta(days=2)) == 0
    assert published == ["seconda"]


# --- login unificato: token di sistema senza scadenza ----------------------------------

def test_graph_host_is_facebook():
    assert GRAPH.startswith("https://graph.facebook.com/v")


@responses.activate
def test_check_connection_is_read_only_and_hides_token():
    responses.add(responses.GET, f"{GRAPH}/{IG}", json={"username": "50onrecord", "id": IG})
    responses.add(responses.GET, f"{GRAPH}/{IG}/content_publishing_limit",
                  json={"data": [{"quota_usage": 2, "config": {"quota_total": 50}}]})
    info = check_connection(IG, "TOKEN")
    assert info == {"username": "50onrecord", "quota_usage": 2, "quota_total": 50}
    assert all(c.request.method == "GET" for c in responses.calls)
    assert "TOKEN" not in str(info)


@responses.activate
def test_check_connection_wrong_account_fails():
    responses.add(responses.GET, f"{GRAPH}/{IG}", status=400, json={"error": {"message": "Invalid OAuth access token"}})
    with pytest.raises(PublishError, match="Invalid OAuth access token"):
        check_connection(IG, "BAD")


def test_publish_without_token_expiry_env(repo, monkeypatch):
    monkeypatch.delenv("IG_TOKEN_EXPIRES")
    monkeypatch.setattr(instagram, "publish_carousel", lambda *a, **k: "MEDIA123")
    assert cli.publish(repo, now=EVENING) == 0
    assert (repo / "archive" / "item-1").exists()


def test_check_instagram_command(repo, monkeypatch, capsys):
    monkeypatch.setattr(instagram, "check_connection",
                        lambda ig, token: {"username": "50onrecord", "quota_usage": 0, "quota_total": 50})
    assert cli.main(["check-instagram"]) == 0
    out = capsys.readouterr().out
    assert "50onrecord" in out and "TOKEN" not in out


def test_check_instagram_failure_is_clean(repo, monkeypatch, capsys):
    def boom(ig, token):
        raise PublishError("Invalid OAuth access token")
    monkeypatch.setattr(instagram, "check_connection", boom)
    assert cli.main(["check-instagram"]) == 1
    out = capsys.readouterr().out
    assert "Invalid OAuth access token" in out and "Traceback" not in out and "TOKEN" not in out


# --- segreti incollati con spazi o "a capo" ------------------------------------------------

@responses.activate
def test_check_connection_with_pasted_whitespace(monkeypatch, capsys):
    responses.add(responses.GET, f"{GRAPH}/{IG}", json={"username": "50onrecord", "id": IG})
    responses.add(responses.GET, f"{GRAPH}/{IG}/content_publishing_limit",
                  json={"data": [{"quota_usage": 0, "config": {"quota_total": 50}}]})
    monkeypatch.setenv("IG_USER_ID", f"  {IG}\n")
    monkeypatch.setenv("IG_TOKEN", "  TOKEN\r\n")
    assert cli.main(["check-instagram"]) == 0
    assert responses.calls[0].request.headers["Authorization"] == "Bearer TOKEN"
    assert f"/{IG}?" in responses.calls[0].request.url


def test_publish_uses_clean_secrets(repo, monkeypatch):
    seen = {}
    monkeypatch.setenv("IG_USER_ID", f"{IG}\n")
    monkeypatch.setenv("IG_TOKEN", "TOKEN \n")

    def fake(urls, caption, ig, token, on_container=None):
        seen.update(ig=ig, token=token)
        return "M1"
    monkeypatch.setattr(instagram, "publish_carousel", fake)
    assert cli.publish(repo, now=EVENING) == 0
    assert seen == {"ig": IG, "token": "TOKEN"}


@responses.activate
def test_prepare_carousel_never_publishes():
    _happy_path_mocks()
    carousel = instagram.prepare_carousel(URLS, "didascalia", IG, "TOKEN", poll_interval=0)
    assert carousel == "carousel"
    assert not any(c.request.url.endswith("/media_publish") for c in responses.calls)


@responses.activate
def test_prepare_instagram_command_uses_oldest_queued_item(tmp_path, monkeypatch, capsys):
    item = tmp_path / "queue" / "item-1"
    (item / "slides").mkdir(parents=True)
    for i in (1, 2):
        (item / "slides" / f"{i:02d}.jpg").write_bytes(b"x")
    (item / "caption.txt").write_text("didascalia", encoding="utf-8")
    (item / "manifest.json").write_text(json.dumps({"id": "item-1", "status": "ready", "created_at": "2026-11-02T00:00:00+00:00"}))
    monkeypatch.setenv("IG_USER_ID", IG)
    monkeypatch.setenv("IG_TOKEN", "TOKEN")
    monkeypatch.setenv("ONRECORD_RAW_BASE", "https://raw.githubusercontent.com/o/50onrecord/main")
    for i in range(2):
        responses.add(responses.POST, f"{GRAPH}/{IG}/media", json={"id": f"c{i}"})
        _status(f"c{i}", "FINISHED")
    responses.add(responses.POST, f"{GRAPH}/{IG}/media", json={"id": "carousel"})
    _status("carousel", "FINISHED")
    assert cli.main(["prepare-instagram", "--root", str(tmp_path)]) == 0
    assert "pronto" in capsys.readouterr().out
    assert not any(c.request.url.endswith("/media_publish") for c in responses.calls)


# --- pubblicazione immediata (fuori slot) e scelta del carosello ---------------------

AFTERNOON = datetime(2026, 12, 2, 15, 0, tzinfo=timezone.utc)  # 16:00 a Roma: nessuno slot


def _add_item(repo, name, created_at):
    item = repo / "queue" / name
    (item / "slides").mkdir(parents=True)
    for i in range(1, 7):
        (item / "slides" / f"{i:02d}.jpg").write_bytes(b"\xff\xd8")
    (item / "caption.txt").write_text(f"didascalia {name}")
    (item / "manifest.json").write_text(json.dumps({
        "id": name, "artist": "Queen", "song": "y", "decade": "80", "strand": "studio", "italian": False,
        "key": name, "status": "ready", "created_at": created_at, "issue": 2}))


def test_publish_immediately_ignores_the_slot(repo, monkeypatch):
    monkeypatch.setattr(instagram, "publish_carousel", lambda urls, caption, ig, token, on_container=None: "NOW1")
    assert cli.publish(repo, now=AFTERNOON, immediate=True) == 0
    published = json.loads((repo / "archive" / "item-1" / "published.json").read_text())
    assert published["media_id"] == "NOW1"
    assert published["slot"] == "manuale-2026-12-02T16:00"


def test_publish_immediately_does_not_block_the_next_slot(repo, monkeypatch):
    _add_item(repo, "item-2", "2026-12-01T03:00:00+00:00")
    monkeypatch.setattr(instagram, "publish_carousel", lambda urls, caption, ig, token, on_container=None: "M")
    assert cli.publish(repo, now=AFTERNOON, immediate=True) == 0
    assert cli.publish(repo, now=EVENING) == 0  # lo slot delle 20:30 pubblica comunque il successivo
    assert (repo / "archive" / "item-2").exists()


def test_publish_a_chosen_item_instead_of_the_oldest(repo, monkeypatch):
    _add_item(repo, "item-2", "2026-12-02T03:00:00+00:00")
    captions = []
    monkeypatch.setattr(instagram, "publish_carousel",
                        lambda urls, caption, ig, token, on_container=None: captions.append(caption) or "M2")
    assert cli.publish(repo, now=AFTERNOON, immediate=True, item="item-2") == 0
    assert captions == ["didascalia item-2"]
    assert (repo / "archive" / "item-2").exists() and (repo / "queue" / "item-1").exists()


def test_publish_unknown_item_fails_without_posting(repo, capsys):
    with responses.RequestsMock() as rsps:
        assert cli.publish(repo, now=AFTERNOON, immediate=True, item="non-esiste") == 1
        assert len(rsps.calls) == 0
    assert "non-esiste" in capsys.readouterr().out
    assert (repo / "queue" / "item-1").exists()


# --- protezione dai duplicati: controllo delle ultime didascalie ------------------------

@responses.activate
def test_recent_captions_reads_the_latest_posts():
    responses.add(responses.GET, f"{GRAPH}/{IG}/media", json={"data": [{"caption": "uno"}, {"id": "2"}, {"caption": "tre"}]})
    assert instagram.recent_captions(IG, "TOKEN", limit=3) == ["uno", "tre"]
    assert "fields=caption" in responses.calls[0].request.url and "limit=3" in responses.calls[0].request.url


def test_caption_already_online_is_archived_without_posting_again(repo, monkeypatch):
    # Meta a volte pubblica ma risponde con un errore: il sistema non deve ripubblicare lo stesso carosello.
    monkeypatch.setattr(instagram, "recent_captions", lambda ig_user_id, token, limit=10: ["altro", " didascalia  "])
    posted = []
    monkeypatch.setattr(instagram, "publish_carousel",
                        lambda urls, caption, ig, token, on_container=None: posted.append(caption) or "NEW")
    assert cli.publish(repo, now=EVENING) == 0
    assert posted == []
    assert (repo / "archive" / "item-1").exists() and not (repo / "queue" / "item-1").exists()


def test_publish_stops_when_recent_posts_cannot_be_checked(repo, monkeypatch):
    def fails(ig_user_id, token, limit=10):
        raise PublishError("Meta ha rifiutato la richiesta: Application request limit reached")
    monkeypatch.setattr(instagram, "recent_captions", fails)
    posted = []
    monkeypatch.setattr(instagram, "publish_carousel",
                        lambda urls, caption, ig, token, on_container=None: posted.append(caption) or "NEW")
    assert cli.publish(repo, now=EVENING) == 1
    assert posted == [] and (repo / "queue" / "item-1").exists()


def test_error_after_meta_published_is_recovered_in_the_same_run(repo, monkeypatch):
    # Meta pubblica ma risponde "limite di richieste": al secondo controllo il post è online, niente run fallito.
    calls = {"n": 0}

    def captions(ig_user_id, token, limit=10):
        calls["n"] += 1
        return [] if calls["n"] == 1 else ["didascalia"]

    def publish_then_error(urls, caption, ig, token, on_container=None):
        raise PublishError("Meta ha rifiutato la richiesta: Application request limit reached")

    monkeypatch.setattr(instagram, "recent_captions", captions)
    monkeypatch.setattr(instagram, "publish_carousel", publish_then_error)
    assert cli.publish(repo, now=EVENING) == 0
    assert (repo / "archive" / "item-1").exists() and not (repo / "queue" / "item-1").exists()
    state = json.loads((repo / "state.json").read_text())
    assert "pending" not in state and state["consecutive_skips"] == 0


def test_error_without_a_published_post_still_fails(repo, monkeypatch):
    def publish_error(urls, caption, ig, token, on_container=None):
        raise PublishError("Meta ha rifiutato la richiesta: Application request limit reached")

    monkeypatch.setattr(instagram, "publish_carousel", publish_error)
    assert cli.publish(repo, now=EVENING) == 1
    assert (repo / "queue" / "item-1").exists()

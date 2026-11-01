import pytest
import responses

from onrecord.models import PhotoRequest
from onrecord.photos import API_URL, license_allowed, resolve_photo
from conftest import FIXTURES

IMG_URL = "https://upload.wikimedia.org/wikipedia/commons/3/31/Sting_Atlanta_3.jpg"


@pytest.mark.parametrize("name,ok", [
    ("Public domain", True), ("CC0", True), ("CC BY 2.0", True), ("CC BY-SA 4.0", True),
    ("CC BY-NC 2.0", False), ("CC BY-ND 4.0", False), ("CC BY-NC-SA 3.0", False),
    ("Fair use", False), ("", False),
])
def test_license_allowed(name, ok):
    assert license_allowed(name) is ok


def _mock_api(fixture):
    responses.add(responses.GET, API_URL, body=(FIXTURES / fixture).read_text(), content_type="application/json")


@responses.activate
def test_resolve_uses_original_resolution(tmp_path):
    _mock_api("commons_sting.json")
    responses.add(responses.GET, IMG_URL, body=b"\xff\xd8jpegdata", content_type="image/jpeg")
    photo = resolve_photo(PhotoRequest(query="Sting Police 1979", role="main"), tmp_path, subject="Sting")
    assert photo is not None
    assert photo.path.read_bytes() == b"\xff\xd8jpegdata"
    assert responses.calls[1].request.url.startswith(IMG_URL)
    assert "thumb" not in responses.calls[1].request.url
    assert photo.license == "CC BY-SA 4.0"
    assert photo.sharealike is True
    assert photo.source_url == "https://commons.wikimedia.org/wiki/File:Sting_Atlanta_3.jpg"


@responses.activate
def test_author_html_stripped(tmp_path):
    _mock_api("commons_sting.json")
    responses.add(responses.GET, IMG_URL, body=b"x")
    assert resolve_photo(PhotoRequest(query="Sting", role="main"), tmp_path, subject="Sting").author == "Acroterion"


@responses.activate
def test_resolve_rejects_nc(tmp_path):
    _mock_api("commons_nc.json")
    assert resolve_photo(PhotoRequest(query="Sting", role="main"), tmp_path, subject="Sting") is None
    assert len(responses.calls) == 1


@responses.activate
def test_resolve_none_when_no_results(tmp_path):
    _mock_api("commons_empty.json")
    assert resolve_photo(PhotoRequest(query="Nobody", role="main"), tmp_path, subject="Nobody") is None


@responses.activate
def test_resolve_by_commons_file_uses_titles(tmp_path):
    _mock_api("commons_sting.json")
    responses.add(responses.GET, IMG_URL, body=b"x")
    resolve_photo(PhotoRequest(query="", commons_file="Sting Atlanta 3.jpg", role="main"), tmp_path, subject="Sting")
    assert "titles=File%3ASting+Atlanta+3.jpg" in responses.calls[0].request.url


@responses.activate
def test_user_agent_is_descriptive(tmp_path):
    _mock_api("commons_empty.json")
    resolve_photo(PhotoRequest(query="x", role="main"), tmp_path, subject="x")
    assert "50onrecord" in responses.calls[0].request.headers["User-Agent"]


@responses.activate
def test_ai_generated_category_rejected(tmp_path):
    _mock_api("commons_ai.json")
    assert resolve_photo(PhotoRequest(query="Sting", role="main"), tmp_path, subject="Sting") is None
    assert len(responses.calls) == 1


@responses.activate
def test_wrong_subject_rejected(tmp_path):
    _mock_api("commons_sting.json")
    assert resolve_photo(PhotoRequest(query="Madonna 1985", role="main"), tmp_path, subject="Madonna") is None


@responses.activate
def test_subject_matched_in_categories(tmp_path):
    _mock_api("commons_sting.json")
    responses.add(responses.GET, IMG_URL, body=b"x")
    photo = resolve_photo(PhotoRequest(query="Police live", role="main"), tmp_path, subject="The Police")
    assert photo is not None


def test_categories_requested(tmp_path):
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, API_URL, body=(FIXTURES / "commons_empty.json").read_text())
        resolve_photo(PhotoRequest(query="x", role="main"), tmp_path, subject="x")
        assert "categories" in rsps.calls[0].request.url


@responses.activate
def test_photo_without_author_rejected(tmp_path):
    import json as _json
    data = _json.loads((FIXTURES / "commons_sting.json").read_text())
    for page in data["query"]["pages"].values():
        page["imageinfo"][0]["extmetadata"].pop("Artist", None)
    responses.add(responses.GET, API_URL, json=data)
    assert resolve_photo(PhotoRequest(query="Sting", role="main"), tmp_path, subject="Sting") is None

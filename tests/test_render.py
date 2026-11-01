import struct
from pathlib import Path

import pytest

from onrecord.models import Story
from onrecord.photos import Photo
from onrecord.render import SlideOverflowError, render_story

MOCK_IMG = Path(__file__).parent.parent / "docs" / "mockup" / "img"


def _photo(name):
    return Photo(path=MOCK_IMG / name, author="Acroterion", license="CC BY-SA 4.0",
                 source_url="https://commons.wikimedia.org/wiki/File:Sting_Atlanta_1.jpg", sharealike=True)


def _photos_for(story):
    pool = ["sting_bass.jpg", "copeland.jpg", "summers.jpg", "sting_live.jpg", "hero.jpg"]
    return {i: [_photo(pool[(i + j) % len(pool)]) for j in range(len(s.photos))] for i, s in enumerate(story.slides)}


def _jpeg_size(path):
    data = Path(path).read_bytes()
    assert data[:2] == b"\xff\xd8", "non è un JPEG"
    i = 2
    while i < len(data):
        marker, length = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            height, width = struct.unpack(">HH", data[i + 5:i + 9])
            return width, height
        i += 2 + length
    raise AssertionError("dimensioni JPEG non trovate")


def test_renders_expected_count_and_size(tmp_path, story_dict):
    story = Story(**story_dict)
    paths = render_story(story, _photos_for(story), issue=1, out_dir=tmp_path)
    assert len(paths) == len(story.slides)
    for p in paths:
        assert p.suffix == ".jpg"
        assert _jpeg_size(p) == (1080, 1350)


def test_footer_issue_number(tmp_path, story_dict):
    story = Story(**story_dict)
    render_story(story, _photos_for(story), issue=7, out_dir=tmp_path)
    assert "fanzine n.7" in (tmp_path / "html" / "01.html").read_text(encoding="utf-8")
    assert "fanzine n.8" in (tmp_path / "html" / f"{len(story.slides):02d}.html").read_text(encoding="utf-8")


def test_overflow_detected(tmp_path, story_dict):
    story_dict["slides"][0]["heading_cuts"] = ["X" * 60]
    story = Story(**story_dict)
    with pytest.raises(SlideOverflowError) as exc:
        render_story(story, _photos_for(story), issue=1, out_dir=tmp_path)
    assert exc.value.slide_index == 0


def test_body_overflow_detected(tmp_path, story_dict):
    story_dict["slides"][1]["body"] = "parola " * 400
    story = Story(**story_dict)
    with pytest.raises(SlideOverflowError) as exc:
        render_story(story, _photos_for(story), issue=1, out_dir=tmp_path)
    assert exc.value.slide_index == 1


def test_long_word_with_accents_fits(tmp_path, story_dict):
    story_dict["slides"][1]["heading_cuts"] = ["DÜSSELDORF", "1979"]
    story_dict["slides"][1]["body"] += " Un suono psichedelicamente nuovo."
    story = Story(**story_dict)
    render_story(story, _photos_for(story), issue=1, out_dir=tmp_path)


@pytest.mark.parametrize("decade,year", [("60", 1967), ("80", 1985), ("90", 1991), ("00", 2004)])
def test_every_decade_palette_renders(tmp_path, story_dict, decade, year):
    story_dict["decade"], story_dict["year"] = decade, year
    story = Story(**story_dict)
    render_story(story, _photos_for(story), issue=1, out_dir=tmp_path)
    assert f"decade-{decade}" in (tmp_path / "html" / "01.html").read_text(encoding="utf-8")


def test_nophoto_variant(tmp_path, story_dict):
    story_dict["slides"][0]["kind"] = "nophoto_cover"
    story = Story(**story_dict)
    no_photos = {i: [] for i in range(len(story.slides))}
    paths = render_story(story, no_photos, issue=1, out_dir=tmp_path)
    assert len(paths) == len(story.slides)
    assert "<img" not in (tmp_path / "html" / "01.html").read_text(encoding="utf-8")


def test_credits_with_many_authors_fit(tmp_path, story_dict):
    story = Story(**story_dict)
    photos = _photos_for(story)
    names = ["Acroterion", "Rob Bogaerts for Anefo", "Jean-Luc Ourlin", "Kingkongphoto & www.celebrity-photos.com"]
    licenses = ["CC BY-SA 4.0", "CC BY-SA 3.0 nl", "CC BY 2.0", "CC BY-SA 2.0"]
    for i, ps in photos.items():
        for j, p in enumerate(ps):
            p.author, p.license = names[(i + j) % 4], licenses[(i + j) % 4]
    render_story(story, photos, issue=1, out_dir=tmp_path)

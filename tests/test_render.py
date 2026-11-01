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


def _png_size(path):
    with open(path, "rb") as f:
        header = f.read(24)
    return struct.unpack(">II", header[16:24])


def test_renders_expected_count_and_size(tmp_path, story_dict):
    story = Story(**story_dict)
    paths = render_story(story, _photos_for(story), issue=1, out_dir=tmp_path)
    assert len(paths) == len(story.slides)
    for p in paths:
        assert _png_size(p) == (1080, 1350)


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

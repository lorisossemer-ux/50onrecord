from pathlib import Path

import pytest

from onrecord.caption import CaptionTooLongError, build_caption
from onrecord.models import Story
from onrecord.photos import Photo


def _photo(license="CC BY-SA 4.0"):
    return Photo(path=Path("x.jpg"), author="Acroterion", license=license,
                 source_url="https://commons.wikimedia.org/wiki/File:Sting_Atlanta_1.jpg",
                 sharealike="SA" in license)


def test_caption_contents(story_dict):
    story = Story(**story_dict)
    text = build_caption(story, [_photo()], handle="@50onrecord")
    assert story.caption_body in text
    assert story.question in text
    assert "Salvalo e mandalo a chi ama The Police" in text
    assert "Foto (Wikimedia Commons): Acroterion (CC BY-SA 4.0)" in text
    assert "Fonti: " in text
    for fact in story.facts:
        for source in fact.sources:
            assert source.publisher in text
    assert "Per altre storie dietro le canzoni, segui @50onrecord" in text
    assert text.rstrip().endswith(" ".join(story.hashtags))


def test_caption_has_no_links(story_dict):
    # Su Instagram i link nelle didascalie non sono cliccabili: non servono.
    text = build_caption(Story(**story_dict), [_photo()], handle="@50onrecord")
    assert "http" not in text


def test_sources_listed_once_by_publisher(story_dict):
    text = build_caption(Story(**story_dict), [_photo()], handle="@50onrecord")
    sources_line = next(l for l in text.splitlines() if l.startswith("Fonti: "))
    names = [n.strip() for n in sources_line[len("Fonti: "):].split(",")]
    assert len(names) == len(set(names))


def test_photo_credits_on_one_line_without_duplicates(story_dict):
    photos = [_photo(), _photo(), Photo(path=Path("y.jpg"), author="Benky", license="CC BY 2.0",
                                        source_url="https://commons.wikimedia.org/wiki/File:Y.jpg", sharealike=False)]
    text = build_caption(Story(**story_dict), photos, handle="@x")
    credit_lines = [l for l in text.splitlines() if l.startswith("Foto")]
    assert credit_lines == ["Foto (Wikimedia Commons): Acroterion (CC BY-SA 4.0), Benky (CC BY 2.0)"]


def test_doubled_author_name_is_collapsed(story_dict):
    photo = Photo(path=Path("z.jpg"), author="Unknown authorUnknown author", license="Public domain",
                  source_url="https://commons.wikimedia.org/wiki/File:Z.jpg", sharealike=False)
    text = build_caption(Story(**story_dict), [photo], handle="@x")
    assert "Unknown authorUnknown author" not in text
    assert "Unknown author (Public domain)" in text


def test_sharealike_notice(story_dict):
    story = Story(**story_dict)
    assert "Slide rilasciate con licenza CC BY-SA 4.0" in build_caption(story, [_photo()], handle="@x")
    assert "Slide rilasciate" not in build_caption(story, [_photo("CC BY 2.0")], handle="@x")


def test_caption_length_limit(story_dict):
    story_dict["caption_body"] = "parola " * 400
    with pytest.raises(CaptionTooLongError):
        build_caption(Story(**story_dict), [_photo()], handle="@x")


def test_caption_starts_with_listen_line_without_links(story_dict):
    story = Story(**story_dict)
    text = build_caption(story, [_photo()], handle="@50onrecord")
    assert text.splitlines()[0] == "\U0001F3A7 Ascolta: The Police \u2013 Message in a Bottle"
    assert "spotify" not in text.lower() and "youtube" not in text.lower()

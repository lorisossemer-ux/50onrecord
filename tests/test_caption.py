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
    assert "Foto: Acroterion · CC BY-SA 4.0 · https://commons.wikimedia.org/wiki/File:Sting_Atlanta_1.jpg" in text
    assert "Fonti:" in text
    for fact in story.facts:
        for source in fact.sources:
            assert str(source.url) in text
    assert "Per altre storie dietro le canzoni, segui @50onrecord" in text
    assert text.rstrip().endswith(" ".join(story.hashtags))


def test_sources_listed_once(story_dict):
    text = build_caption(Story(**story_dict), [_photo()], handle="@50onrecord")
    assert text.count("https://www.songfacts.com/facts/the-police/message-in-a-bottle") == 1


def test_sharealike_notice(story_dict):
    story = Story(**story_dict)
    assert "Slide rilasciate con licenza CC BY-SA 4.0" in build_caption(story, [_photo()], handle="@x")
    assert "Slide rilasciate" not in build_caption(story, [_photo("CC BY 2.0")], handle="@x")


def test_caption_length_limit(story_dict):
    story_dict["caption_body"] = "parola " * 400
    with pytest.raises(CaptionTooLongError):
        build_caption(Story(**story_dict), [_photo()], handle="@x")


def test_caption_starts_with_listen_line_and_search_links(story_dict):
    story = Story(**story_dict)
    text = build_caption(story, [_photo()], handle="@50onrecord")
    assert text.splitlines()[0] == "\U0001F3A7 Ascolta: The Police \u2013 Message in a Bottle"
    assert "https://open.spotify.com/search/The%20Police%20%E2%80%93%20Message%20in%20a%20Bottle" in text
    assert "https://www.youtube.com/results?search_query=The+Police+%E2%80%93+Message+in+a+Bottle" in text

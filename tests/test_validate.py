import pytest

from onrecord.domains import canonical_domain
from onrecord.models import Story
from onrecord.validate import validate_story


@pytest.mark.parametrize("url", [
    "https://en.wikipedia.org/wiki/Message_in_a_Bottle_(The_Police_song)",
    "https://it.wikipedia.org/wiki/Message_in_a_Bottle",
    "https://www.wikiwand.com/en/articles/Message_in_a_Bottle_(The_Police_song)",
    "https://bafybeiemxf.ipfs.4everland.io/wiki/Message_in_a_Bottle_(song).html",
    "https://wiki.krisyotam.com/content/wikipedia_en_all_nopic_2026-03/Message_in_a_Bottle",
])
def test_mirror_domains_collapse(url):
    assert canonical_domain(url) == "wikipedia"


def test_regular_domains():
    assert canonical_domain("https://www.songfacts.com/facts/x") == "songfacts.com"
    assert canonical_domain("https://news.bbc.co.uk/a") == "bbc.co.uk"


def test_valid_fixture_has_no_errors(story_dict):
    assert validate_story(Story(**story_dict)) == []


def test_fact_needs_two_independent_domains(story_dict):
    story_dict["facts"][0]["sources"] = [
        {"url": "https://en.wikipedia.org/wiki/A", "title": "A", "publisher": "Wikipedia"},
        {"url": "https://it.wikipedia.org/wiki/A", "title": "A", "publisher": "Wikipedia"},
    ]
    errors = validate_story(Story(**story_dict))
    assert any("2 fonti indipendenti" in e for e in errors)


@pytest.mark.parametrize("phrase", ["da verificare", "Si dice", "pare che", "sembra che", "forse", "secondo alcuni"])
def test_forbidden_phrases(story_dict, phrase):
    story_dict["slides"][1]["body"] = f"Era il 1979, {phrase} Sting scriveva."
    errors = validate_story(Story(**story_dict))
    assert any(phrase.lower() in e.lower() for e in errors)


def test_forbidden_phrase_in_caption(story_dict):
    story_dict["caption_body"] += " Fonte da verificare."
    assert validate_story(Story(**story_dict))


def test_forbidden_word_not_matched_inside_other_words(story_dict):
    story_dict["slides"][1]["body"] = story_dict["slides"][1]["body"] + " Una forsennata corsa."
    assert validate_story(Story(**story_dict)) == []


def test_lyrics_quote_limit(story_dict):
    story_dict["slides"][3]["body"] = "Canta “uno due tre quattro cinque sei” sulla spiaggia."
    assert any("citazione" in e for e in validate_story(Story(**story_dict)))
    story_dict["slides"][3]["body"] = "Canta \"uno due tre quattro cinque\" sulla spiaggia."
    assert validate_story(Story(**story_dict)) == []


def test_hashtag_limit(story_dict):
    story_dict["hashtags"].append("#sesto")
    assert any("hashtag" in e for e in validate_story(Story(**story_dict)))


def test_every_slide_number_traceable(story_dict):
    story_dict["slides"][4]["body"] = "Ci resta tre settimane e vende 2000000 copie."
    errors = validate_story(Story(**story_dict))
    assert any("numero non coperto da un fatto" in e for e in errors)

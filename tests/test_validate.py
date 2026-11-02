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


# --- correzioni dalla revisione finale --------------------------------------------

def test_minimum_three_facts(story_dict):
    story_dict["facts"] = story_dict["facts"][:2]
    assert any("almeno 3 fatti" in e for e in validate_story(Story(**story_dict)))


def test_numbers_in_caption_and_question_must_be_covered(story_dict):
    story_dict["caption_body"] += " Vendette 7 milioni di copie nel 1983."
    errors = validate_story(Story(**story_dict))
    assert any("7" in e and "numero non coperto" in e for e in errors)
    assert any("1983" in e for e in errors)


@pytest.mark.parametrize("text", [
    "Si diceva che Sting fosse stanco.",
    "Pare abbia scritto tutto in una notte.",
    "Sembrerebbe una leggenda.",
    "Sembrava che fosse finita.",
    "pare che fosse vero.",
    "si\ndice che fosse vero.",
    "Probabilmente era il 1979.",
    "Si racconta che fosse notte.",
])
def test_hedging_variants_rejected(story_dict, text):
    story_dict["slides"][1]["body"] = text
    assert any("espressione vietata" in e for e in validate_story(Story(**story_dict)))


@pytest.mark.parametrize("url", [
    "https://wikimili.com/en/Message_in_a_Bottle",
    "https://wiki2.org/en/Message_in_a_Bottle",
    "https://dbpedia.org/page/Message_in_a_Bottle",
    "https://infogalactic.com/info/Message_in_a_Bottle",
    "https://alchetron.com/Message-in-a-Bottle",
    "https://everybodywiki.com/Message_in_a_Bottle",
    "https://www.wikidata.org/wiki/Q1",
])
def test_more_wikipedia_mirrors(url):
    assert canonical_domain(url) == "wikipedia"


@pytest.mark.parametrize("url,expected", [
    ("https://web.archive.org/web/20200101000000/https://www.songfacts.com/facts/x", "songfacts.com"),
    ("https://archive.ph/2020.01.01/https://www.songfacts.com/facts/x", "songfacts.com"),
    ("https://www-songfacts-com.translate.goog/facts/x?_x_tr_sl=en", "songfacts.com"),
])
def test_archive_wrappers_unwrapped(url, expected):
    assert canonical_domain(url) == expected


def test_single_curly_quotes_limited(story_dict):
    story_dict["slides"][3]["body"] = "Canta ‘uno due tre quattro cinque sei’ sulla spiaggia, l’isola."
    assert any("citazione" in e for e in validate_story(Story(**story_dict)))


def test_italian_apostrophes_are_not_quotes(story_dict):
    story_dict["slides"][3]["body"] = "Sull’isola, un’idea che diventa un’ossessione per tutta l’estate."
    assert validate_story(Story(**story_dict)) == []


def test_listen_track_must_name_the_artist(story_dict):
    story_dict["listen_track"] = "Roxanne"
    assert any("brano da ascoltare" in e for e in validate_story(Story(**story_dict)))


def test_listen_track_article_is_ignored(story_dict):
    story_dict["listen_track"] = "Police - Roxanne"
    assert validate_story(Story(**story_dict)) == []


def test_listen_track_hedging_rejected(story_dict):
    story_dict["listen_track"] = "The Police - forse Roxanne"
    assert any("espressione vietata" in e for e in validate_story(Story(**story_dict)))


def _with_quote(story_dict, quote):
    story_dict["lyric_quote"] = quote
    story_dict["facts"][0]["claim"] += f' Il ritornello dice "{quote}".'
    return Story(**story_dict)


def test_lyric_quote_is_optional(story_dict):
    assert "lyric_quote" not in story_dict
    assert validate_story(Story(**story_dict)) == []


def test_short_lyric_quote_covered_by_a_fact_is_valid(story_dict):
    assert validate_story(_with_quote(story_dict, "Message in a bottle")) == []


def test_lyric_quote_longer_than_five_words_rejected(story_dict):
    errors = validate_story(_with_quote(story_dict, "Sending out an SOS to the world"))
    assert any("frase del brano" in e and "max 5" in e for e in errors)


def test_lyric_quote_must_appear_in_a_fact(story_dict):
    story_dict["lyric_quote"] = "Sending out an SOS"
    errors = validate_story(Story(**story_dict))
    assert any("frase del brano" in e and "fatto" in e for e in errors)

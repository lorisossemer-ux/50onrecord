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


def test_slides_without_photos_use_text_layout(tmp_path, story_dict):
    story = Story(**story_dict)
    no_photos = {i: [] for i in range(len(story.slides))}
    story.slides[0].kind = "nophoto_cover"
    render_story(story, no_photos, issue=1, out_dir=tmp_path)
    assert "max-height:760px" in (tmp_path / "html" / "02.html").read_text(encoding="utf-8")
    assert "top:160px" in (tmp_path / "html" / "05.html").read_text(encoding="utf-8")


def test_long_marker_fits_without_photo(tmp_path, story_dict):
    story_dict["slides"][1]["marker"] = "quelle note diventeranno il riff più famoso"
    story_dict["slides"][1]["photos"] = []
    story = Story(**story_dict)
    photos = _photos_for(story)
    photos[1] = []
    render_story(story, photos, issue=1, out_dir=tmp_path)


def test_nophoto_cover_long_artist_detected(tmp_path, story_dict):
    story_dict["slides"][0]["kind"] = "nophoto_cover"
    story_dict["artist"] = "The Extraordinarily Long Named Psychedelic Orchestra Of Somewhere Far Away"
    story = Story(**story_dict)
    with pytest.raises(SlideOverflowError) as exc:
        render_story(story, {i: [] for i in range(len(story.slides))}, issue=1, out_dir=tmp_path)
    assert exc.value.slide_index == 0
    assert "artista" in exc.value.elements


def test_trio_without_photos_moves_text_up(tmp_path, story_dict):
    story = Story(**story_dict)
    photos = _photos_for(story)
    photos[2] = []
    render_story(story, photos, issue=1, out_dir=tmp_path)
    assert "top:300px" in (tmp_path / "html" / "03.html").read_text(encoding="utf-8")


def test_final_slide_shows_listen_track(tmp_path, story_dict):
    story = Story(**story_dict)
    render_story(story, _photos_for(story), issue=1, out_dir=tmp_path)
    html = (tmp_path / "html" / f"{len(story.slides):02d}.html").read_text(encoding="utf-8")
    assert "ascolta: The Police \u2013 Message in a Bottle" in html


def test_long_listen_track_detected(tmp_path, story_dict):
    story_dict["listen_track"] = "The Police \u2013 " + "W" * 70
    story = Story(**story_dict)
    with pytest.raises(SlideOverflowError) as exc:
        render_story(story, _photos_for(story), issue=1, out_dir=tmp_path)
    assert "ascolta" in exc.value.elements


def test_two_line_listen_track_fits(tmp_path, story_dict):
    story_dict["listen_track"] = "The Rolling Stones \u2013 (I Can't Get No) Satisfaction e le sue molte versioni dal vivo"
    story = Story(**story_dict)
    render_story(story, _photos_for(story), issue=1, out_dir=tmp_path)


def test_relative_output_dir_renders(tmp_path, story_dict, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story = Story(**story_dict)
    paths = render_story(story, _photos_for(story), issue=1, out_dir=Path("incoming/x/slides"))
    assert len(paths) == len(story.slides)
    assert all(p.exists() for p in paths)


def _note_font_sizes(html):
    import os
    from playwright.sync_api import sync_playwright
    from onrecord.render import _GROW_NOTES_JS, _OVERFLOW_JS
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=os.environ.get("ONRECORD_BROWSER_CHANNEL") or None)
        try:
            tab = browser.new_page(viewport={"width": 1080, "height": 1350})
            tab.set_content(html)
            tab.evaluate(_GROW_NOTES_JS, 60)
            sizes = tab.evaluate("[...document.querySelectorAll('.note')].map(e => parseFloat(e.style.fontSize))")
            bad = tab.evaluate(_OVERFLOW_JS, 10)
            return sizes, bad
        finally:
            browser.close()


def test_notes_grow_to_fill_their_box_without_overflowing():
    html = ("<style>.note{position:absolute;width:900px;font-family:serif;line-height:1.45;overflow:hidden}</style>"
            '<div class="note fit" style="top:0;max-height:500px;font-size:40px">Testo breve.</div>'
            '<div class="note fit" style="top:600px;max-height:330px;font-size:40px">' + "parola " * 30 + "</div>")
    (short, long_), bad = _note_font_sizes(html)
    assert 40 < short <= 60    # il testo corto si ingrandisce, ma non oltre il tetto
    assert 40 <= long_ < short  # il testo lungo cresce meno (o per nulla)
    assert bad == []           # nulla esce dal proprio riquadro


def test_note_that_overflows_at_base_size_is_not_shrunk_or_hidden():
    html = ("<style>.note{position:absolute;width:900px;font-family:serif;line-height:1.45;overflow:hidden}</style>"
            '<div class="note fit" style="top:0;max-height:100px;font-size:40px">' + "parola " * 60 + "</div>")
    (size,), bad = _note_font_sizes(html)
    assert size == 40          # non toccato: resta segnalato come overflow
    assert bad


def test_final_slide_shows_lyric_quote(tmp_path, story_dict):
    story_dict["lyric_quote"] = "Message in a bottle"
    story = Story(**story_dict)
    render_story(story, _photos_for(story), issue=1, out_dir=tmp_path)
    final = (tmp_path / "html" / f"{len(story.slides):02d}.html").read_text(encoding="utf-8")
    assert "Message in a bottle" in final


def test_final_slide_without_lyric_quote_has_no_quote_box(tmp_path, story_dict):
    story = Story(**story_dict)
    render_story(story, _photos_for(story), issue=1, out_dir=tmp_path)
    final = (tmp_path / "html" / f"{len(story.slides):02d}.html").read_text(encoding="utf-8")
    assert 'data-name="frase del brano"' not in final

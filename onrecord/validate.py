"""Regole deterministiche su fatti e testi (spec §5–§6). Restituisce errori leggibili."""
from __future__ import annotations

import re
from typing import Iterable, List

from .domains import canonical_domain
from .models import Story

MIN_INDEPENDENT_SOURCES = 2
MAX_QUOTED_WORDS = 5
MAX_HASHTAGS = 5
FORBIDDEN_PHRASES = ["da verificare", "si dice", "pare che", "sembra che", "forse", "secondo alcuni"]

_QUOTE_RE = re.compile(r"[“\"«]([^”\"»]+)[”\"»]")
_NUMBER_RE = re.compile(r"\d+")


def _story_texts(story: Story) -> Iterable[str]:
    for slide in story.slides:
        yield from slide.heading_cuts
        for text in (slide.body, slide.marker, slide.source_note):
            if text:
                yield text
    yield story.caption_body
    yield story.question


def _slide_texts_for_numbers(story: Story) -> Iterable[str]:
    # source_note cita la fonte (es. "My Songs (2019)") e non è un'affermazione.
    for slide in story.slides:
        yield from slide.heading_cuts
        for text in (slide.body, slide.marker):
            if text:
                yield text


def validate_story(story: Story) -> List[str]:
    errors: List[str] = []

    for i, fact in enumerate(story.facts, start=1):
        domains = {canonical_domain(str(s.url)) for s in fact.sources}
        if len(domains) < MIN_INDEPENDENT_SOURCES:
            errors.append(f"fatto {i}: servono almeno 2 fonti indipendenti (trovate: {sorted(domains)})")

    texts = list(_story_texts(story))
    for phrase in FORBIDDEN_PHRASES:
        pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
        if any(pattern.search(t) for t in texts):
            errors.append(f"espressione vietata: \"{phrase}\"")

    for text in texts:
        for quoted in _QUOTE_RE.findall(text):
            if len(quoted.split()) > MAX_QUOTED_WORDS:
                errors.append(f"citazione troppo lunga (max {MAX_QUOTED_WORDS} parole): \"{quoted}\"")

    if len(story.hashtags) > MAX_HASHTAGS:
        errors.append(f"troppi hashtag: {len(story.hashtags)} (max {MAX_HASHTAGS})")

    known_numbers = set()
    for fact in story.facts:
        known_numbers.update(_NUMBER_RE.findall(fact.claim))
    for text in _slide_texts_for_numbers(story):
        for number in _NUMBER_RE.findall(text):
            if number not in known_numbers:
                errors.append(f"numero non coperto da un fatto: {number} in \"{text}\"")

    return errors

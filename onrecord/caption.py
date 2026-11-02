"""Didascalia del carosello (spec §5): racconto, invito, fonti, crediti foto, chiusura, hashtag."""
from __future__ import annotations

from typing import List

from .models import Story
from .photos import Photo

MAX_CAPTION_CHARS = 2200  # limite Instagram
SHAREALIKE_NOTICE = "Slide rilasciate con licenza CC BY-SA 4.0."


class CaptionTooLongError(ValueError):
    pass


def _clean_author(author: str) -> str:
    """Commons a volte restituisce il nome due volte di seguito ("Unknown authorUnknown author")."""
    author = author.strip()
    half = len(author) // 2
    if len(author) % 2 == 0 and author[:half] == author[half:]:
        return author[:half]
    return author


def build_caption(story: Story, photos: List[Photo], handle: str) -> str:
    # Su Instagram i link nelle didascalie non sono cliccabili: niente indirizzi, solo nomi.
    parts = [f"\U0001F3A7 Ascolta: {story.listen_track.strip()}", story.caption_body.strip(),
             story.question.strip(), f"Salvalo e mandalo a chi ama {story.artist}."]

    publishers = []
    for fact in story.facts:
        for source in fact.sources:
            if source.publisher not in publishers:
                publishers.append(source.publisher)
    parts.append("Fonti: " + ", ".join(publishers))

    credits = []
    for p in photos:
        credit = f"{_clean_author(p.author)} ({p.license})"
        if credit not in credits:
            credits.append(credit)
    if credits:
        block = "Foto (Wikimedia Commons): " + ", ".join(credits)
        if any(p.sharealike for p in photos):
            block += "\n" + SHAREALIKE_NOTICE
        parts.append(block)

    parts.append(f"Per altre storie dietro le canzoni, segui {handle}")
    if story.hashtags:
        parts.append(" ".join(story.hashtags))

    text = "\n\n".join(parts)
    if len(text) > MAX_CAPTION_CHARS:
        raise CaptionTooLongError(f"didascalia di {len(text)} caratteri (max {MAX_CAPTION_CHARS})")
    return text

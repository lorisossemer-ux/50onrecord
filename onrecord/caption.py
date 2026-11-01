"""Didascalia del carosello (spec §5): racconto, invito, fonti, crediti foto, chiusura, hashtag."""
from __future__ import annotations

from typing import List
from urllib.parse import quote, quote_plus

from .models import Story
from .photos import Photo

MAX_CAPTION_CHARS = 2200  # limite Instagram
SHAREALIKE_NOTICE = "Slide rilasciate con licenza CC BY-SA 4.0."


class CaptionTooLongError(ValueError):
    pass


def build_caption(story: Story, photos: List[Photo], handle: str) -> str:
    track = story.listen_track.strip()
    listen = (f"\U0001F3A7 Ascolta: {track}\n"
              f"Spotify: https://open.spotify.com/search/{quote(track)}\n"
              f"YouTube: https://www.youtube.com/results?search_query={quote_plus(track)}")
    parts = [listen, story.caption_body.strip(), story.question.strip(),
             f"Salvalo e mandalo a chi ama {story.artist}."]

    seen = []
    for fact in story.facts:
        for source in fact.sources:
            if str(source.url) not in [str(s.url) for s in seen]:
                seen.append(source)
    parts.append("Fonti:\n" + "\n".join(f"- {s.title} ({s.publisher}): {s.url}" for s in seen))

    credits = []
    for p in photos:
        line = f"Foto: {p.author} · {p.license} · {p.source_url}"
        if line not in credits:
            credits.append(line)
    if credits:
        block = "\n".join(credits)
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

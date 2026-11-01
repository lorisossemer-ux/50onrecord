"""Modelli dei dati di una storia (il file story.json scritto dalla routine)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, model_validator

SlideKind = Literal["cover", "note", "trio", "emotion", "result", "final", "nophoto_cover"]
Decade = Literal["60", "70", "80", "90", "00"]
Strand = Literal["palco", "studio", "privata", "emozione"]

MIN_SLIDES = 6
MAX_SLIDES = 10


class Source(BaseModel):
    url: HttpUrl
    title: str
    publisher: str


class Fact(BaseModel):
    claim: str
    sources: List[Source]


class PhotoRequest(BaseModel):
    query: str
    commons_file: Optional[str] = None
    role: Literal["main", "side", "trio"]


class Slide(BaseModel):
    kind: SlideKind
    heading_cuts: List[str] = Field(default_factory=list)
    body: Optional[str] = None
    marker: Optional[str] = None
    photos: List[PhotoRequest] = Field(default_factory=list)
    source_note: Optional[str] = None


def decade_of(year: int) -> str:
    """1979 -> "70"; 2000-2010 -> "00"."""
    if year >= 2000:
        return "00"
    return str(year)[2] + "0"


class Story(BaseModel):
    id: str
    artist: str
    song: Optional[str] = None
    year: int = Field(ge=1960, le=2010)
    decade: Decade
    strand: Strand
    italian: bool
    facts: List[Fact]
    slides: List[Slide] = Field(min_length=MIN_SLIDES, max_length=MAX_SLIDES)
    caption_body: str
    question: str
    hashtags: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_structure(self) -> "Story":
        if self.decade != decade_of(self.year):
            raise ValueError(f"decennio {self.decade} incoerente con l'anno {self.year}")
        if self.slides[0].kind not in ("cover", "nophoto_cover"):
            raise ValueError("la prima slide deve essere una copertina")
        if self.slides[-1].kind != "final":
            raise ValueError("l'ultima slide deve essere di tipo final")
        return self


def load_story(path: Path) -> Story:
    return Story(**json.loads(Path(path).read_text(encoding="utf-8")))

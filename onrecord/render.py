"""Impaginazione fanzine: modelli Jinja2 trasformati in PNG 1080×1350 con Playwright (spec §4)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from .models import Story
from .photos import Photo

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
WIDTH, HEIGHT = 1080, 1350
FRAME_TOLERANCE = 10
MAX_CREDIT_CHARS = 55
JPEG_QUALITY = 92

# Ogni elemento .fit deve stare nel suo riquadro e dentro la slide. 12px di tolleranza
# assorbono le metriche dei caratteri (ascendenti del pennarello); una riga in più è ≥ 30px.
_OVERFLOW_JS = """
(tol) => {
  const bad = [];
  document.querySelectorAll('.fit').forEach(el => {
    const name = el.dataset.name || el.className;
    if (el.scrollHeight > el.clientHeight + 12 || el.scrollWidth > el.clientWidth + 12) bad.push(name);
    const r = el.getBoundingClientRect();
    if (r.left < -tol || r.top < -tol || r.right > 1080 + tol || r.bottom > 1350 + tol) bad.push(name + ' (fuori slide)');
  });
  return bad;
}
"""


# I testi nei riquadri bianchi si ingrandiscono finché stanno nel riquadro (tetto: NOTE_MAX_FONT_PX),
# per essere leggibili anche sul telefono. Un testo che già non sta alla misura di base non viene toccato
# e resta segnalato dal controllo di overflow.
NOTE_MAX_FONT_PX = 60
_GROW_NOTES_JS = """
(cap) => {
  document.querySelectorAll('.note.fit').forEach(el => {
    const fits = () => el.scrollHeight <= el.clientHeight + 12 && el.scrollWidth <= el.clientWidth + 12;
    let size = parseFloat(getComputedStyle(el).fontSize);
    if (!fits()) return;
    while (size + 2 <= cap) {
      el.style.fontSize = (size + 2) + 'px';
      if (!fits()) { el.style.fontSize = size + 'px'; return; }
      size += 2;
    }
    el.style.fontSize = size + 'px';
  });
}
"""


class SlideOverflowError(Exception):
    def __init__(self, slide_index: int, elements: List[str]):
        self.slide_index = slide_index
        self.elements = elements
        super().__init__(f"slide {slide_index + 1}: testo che esce dal riquadro: {', '.join(elements)}")


class _PhotoView:
    def __init__(self, photo: Photo):
        self.uri = Path(photo.path).resolve().as_uri()


def credits_line(photos: Dict[int, List[Photo]]) -> str:
    """Credito sintetico sulla slide; autori, licenze e link completi stanno in didascalia (spec §7)."""
    authors: List[str] = []
    for slide_photos in photos.values():
        for p in slide_photos:
            if p.author not in authors:
                authors.append(p.author)
    if not authors:
        return "50ONRECORD"
    line = f"foto: {authors[0]}" + (" e altri" if len(authors) > 1 else "") + " · licenze in didascalia"
    if len(line) > MAX_CREDIT_CHARS:
        line = "foto: Wikimedia Commons · crediti in didascalia"
    return line


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html"]))


def render_story(story: Story, photos: Dict[int, List[Photo]], issue: int, out_dir: Path,
                 handle: str = "@50onrecord") -> List[Path]:
    out_dir = Path(out_dir).resolve()  # as_uri() vuole percorsi assoluti
    html_dir = out_dir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    env = _env()
    credits = credits_line(photos)
    pages = []
    for i, slide in enumerate(story.slides):
        html = env.get_template(f"{slide.kind}.html").render(
            story=story, slide=slide, index=i, total=len(story.slides), issue=issue, handle=handle,
            photos=[_PhotoView(p) for p in photos.get(i, [])],  # indici mancanti = Undefined nei modelli
            credits=credits, assets=TEMPLATES.as_uri(),
        )
        page = html_dir / f"{i + 1:02d}.html"
        page.write_text(html, encoding="utf-8")
        pages.append(page)

    outputs = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=os.environ.get("ONRECORD_BROWSER_CHANNEL") or None,
                                     args=["--allow-file-access-from-files"])
        try:
            tab = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
            for i, page in enumerate(pages):
                tab.goto(page.as_uri())
                tab.evaluate("document.fonts.ready")
                tab.evaluate(_GROW_NOTES_JS, NOTE_MAX_FONT_PX)
                bad = tab.evaluate(_OVERFLOW_JS, FRAME_TOLERANCE)
                if bad:
                    raise SlideOverflowError(i, bad)
                # Instagram accetta solo JPEG per la pubblicazione via API.
                jpg = out_dir / f"{i + 1:02d}.jpg"
                tab.screenshot(path=str(jpg), type="jpeg", quality=JPEG_QUALITY)
                outputs.append(jpg)
        finally:
            browser.close()
    return outputs

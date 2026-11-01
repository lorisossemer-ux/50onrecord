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
MAX_CREDIT_AUTHORS = 2
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


class SlideOverflowError(Exception):
    def __init__(self, slide_index: int, elements: List[str]):
        self.slide_index = slide_index
        self.elements = elements
        super().__init__(f"slide {slide_index + 1}: testo che esce dal riquadro: {', '.join(elements)}")


class _PhotoView:
    def __init__(self, photo: Photo):
        self.uri = Path(photo.path).resolve().as_uri()


def credits_line(photos: Dict[int, List[Photo]]) -> str:
    authors: List[str] = []
    licenses: List[str] = []
    for slide_photos in photos.values():
        for p in slide_photos:
            if p.author not in authors:
                authors.append(p.author)
            if p.license not in licenses:
                licenses.append(p.license)
    if not authors:
        return "50ONRECORD"
    shown = ", ".join(authors[:MAX_CREDIT_AUTHORS]) + (" e altri" if len(authors) > MAX_CREDIT_AUTHORS else "")
    return f"foto: {shown} · {', '.join(licenses)}"


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html"]))


def render_story(story: Story, photos: Dict[int, List[Photo]], issue: int, out_dir: Path,
                 handle: str = "@50onrecord") -> List[Path]:
    out_dir = Path(out_dir)
    html_dir = out_dir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    env = _env()
    credits = credits_line(photos)
    pages = []
    for i, slide in enumerate(story.slides):
        html = env.get_template(f"{slide.kind}.html").render(
            story=story, slide=slide, index=i, total=len(story.slides), issue=issue, handle=handle,
            photos=[_PhotoView(p) for p in photos.get(i, [])] + [None, None, None],
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

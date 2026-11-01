"""Verifica che le fonti citate esistano davvero: un link inventato o morto fa scartare la storia."""
from __future__ import annotations

from typing import List

import requests

from .models import Story

USER_AGENT = "Mozilla/5.0 (compatible; 50onrecord/0.1; +https://github.com/lorisossemer-ux/50onrecord)"
TIMEOUT = 20
# Pagina assente: la fonte non esiste. 401/403/429 vengono spesso dai blocchi anti-bot: non bastano a scartare.
MISSING_STATUS = {404, 410}


def unreachable_sources(story: Story) -> List[str]:
    errors = []
    urls = sorted({str(s.url) for fact in story.facts for s in fact.sources})
    for url in urls:
        try:
            status = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT,
                                  allow_redirects=True, stream=True).status_code
        except requests.exceptions.RequestException as exc:
            errors.append(f"fonte non raggiungibile: {url} ({type(exc).__name__})")
            continue
        if status in MISSING_STATUS or status >= 500:
            errors.append(f"fonte non raggiungibile: {url} (HTTP {status})")
    return errors

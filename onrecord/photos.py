"""Foto da Wikimedia Commons con licenza verificata (spec §7)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

from .models import PhotoRequest

API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "50onrecord/0.1 (https://github.com/lorisossemer-ux/50onrecord)"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")
TIMEOUT = 30


@dataclass
class Photo:
    path: Path
    author: str
    license: str
    source_url: str
    sharealike: bool


def license_allowed(short_name: str) -> bool:
    name = (short_name or "").strip().upper()
    if not name or re.search(r"\b(NC|ND)\b", name):
        return False
    return name in ("CC0", "PUBLIC DOMAIN") or name.startswith(("PD", "CC BY", "CC0"))


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").strip()


def _query_params(req: PhotoRequest) -> dict:
    params = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiextmetadatafilter": "LicenseShortName|Artist|LicenseUrl",
    }
    if req.commons_file:
        title = req.commons_file if req.commons_file.startswith("File:") else f"File:{req.commons_file}"
        params["titles"] = title
    else:
        params.update({"generator": "search", "gsrnamespace": 6, "gsrsearch": req.query, "gsrlimit": 10})
    return params


def resolve_photo(req: PhotoRequest, dest: Path) -> Optional[Photo]:
    """Prima foto con licenza ammessa, scaricata alla risoluzione originale; None se non c'è."""
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    data = session.get(API_URL, params=_query_params(req), timeout=TIMEOUT).json()
    pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        url = (info.get("url") or "").split("?")[0]
        meta = info.get("extmetadata", {})
        license_name = meta.get("LicenseShortName", {}).get("value", "")
        if not url.lower().endswith(IMAGE_EXTENSIONS) or not license_allowed(license_name):
            continue
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / url.rsplit("/", 1)[-1]
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        target.write_bytes(response.content)
        return Photo(
            path=target,
            author=_strip_html(meta.get("Artist", {}).get("value", "")) or "autore sconosciuto",
            license=license_name,
            source_url=info.get("descriptionurl", ""),
            sharealike="SA" in license_name.upper(),
        )
    return None

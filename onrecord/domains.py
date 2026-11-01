"""Normalizzazione dei domini delle fonti: i mirror di Wikipedia contano come Wikipedia."""
from __future__ import annotations

import re
from urllib.parse import urlparse

_SECOND_LEVEL = {"co", "com", "org", "net", "ac", "gov", "edu"}
_WIKIPEDIA_MARKERS = ("wikipedia", "wikiwand", "wikimili", "wiki2.org", "dbpedia", "infogalactic",
                      "alchetron", "everybodywiki", "wikidata")
_EMBEDDED_URL = re.compile(r"https?://.+")


def _unwrap(url: str) -> str:
    """web.archive.org/web/<ts>/<url>, archive.ph/<id>/<url> e proxy translate.goog -> sito originale."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in ("web.archive.org", "archive.ph", "archive.today", "archive.is"):
        inner = _EMBEDDED_URL.search(parsed.path[1:] + ("?" + parsed.query if parsed.query else ""))
        if inner:
            return _unwrap(inner.group(0))
    if host.endswith(".translate.goog"):
        original = host[: -len(".translate.goog")].replace("--", "\0").replace("-", ".").replace("\0", "-")
        return f"https://{original}{parsed.path}"
    return url


def canonical_domain(url: str) -> str:
    parsed = urlparse(_unwrap(str(url)))
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    # Mirror e copie di Wikipedia: wikiwand, gateway IPFS con /wiki/, archivi "wikipedia_*".
    haystack = host + parsed.path.lower()
    if any(m in haystack for m in _WIKIPEDIA_MARKERS) or (".ipfs." in host and "/wiki/" in parsed.path):
        return "wikipedia"
    labels = host.split(".")
    if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in _SECOND_LEVEL:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])

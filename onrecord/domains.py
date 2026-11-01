"""Normalizzazione dei domini delle fonti: i mirror di Wikipedia contano come Wikipedia."""
from __future__ import annotations

from urllib.parse import urlparse

_SECOND_LEVEL = {"co", "com", "org", "net", "ac", "gov", "edu"}
_WIKIPEDIA_MARKERS = ("wikipedia", "wikiwand")


def canonical_domain(url: str) -> str:
    parsed = urlparse(str(url))
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

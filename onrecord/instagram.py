"""Pubblicazione di caroselli con l'API di Instagram (Instagram Login, graph.instagram.com)."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional, Tuple

import requests

GRAPH = "https://graph.instagram.com/v26.0"
REFRESH_URL = "https://graph.instagram.com/refresh_access_token"
MAX_CAROUSEL_ITEMS = 10  # limite dichiarato nella spec; l'API ne accetta fino a 20
TIMEOUT = 60


class PublishError(Exception):
    pass


def _call(method: str, url: str, token: str, **data) -> dict:
    try:
        response = requests.request(method, url, headers={"Authorization": f"Bearer {token}"},
                                    data=data or None, timeout=TIMEOUT)
        payload = response.json() if response.content else {}
    except (requests.exceptions.RequestException, ValueError) as exc:
        raise PublishError(f"Meta non ha risposto correttamente: {type(exc).__name__}: {exc}") from exc
    if response.status_code >= 400 or "error" in payload:
        message = payload.get("error", {}).get("message", response.text)
        raise PublishError(f"Meta ha rifiutato la richiesta: {message}")
    return payload


def _wait_finished(container_id: str, token: str, poll_interval: float, max_polls: int) -> None:
    for _ in range(max_polls):
        status = _call("GET", f"{GRAPH}/{container_id}?fields=status_code", token).get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise PublishError(f"contenitore {container_id} in stato {status}")
        time.sleep(poll_interval)
    raise PublishError(f"contenitore {container_id} non pronto dopo {max_polls} controlli")


def container_status(container_id: str, token: str) -> str:
    return _call("GET", f"{GRAPH}/{container_id}?fields=status_code", token).get("status_code", "")


def publish_container(ig_user_id: str, container_id: str, token: str) -> str:
    return _call("POST", f"{GRAPH}/{ig_user_id}/media_publish", token, creation_id=container_id)["id"]


def publish_carousel(image_urls: List[str], caption: str, ig_user_id: str, token: str,
                     poll_interval: float = 30, max_polls: int = 10,
                     on_container: Optional[Callable[[str], None]] = None) -> str:
    """Restituisce l'id del post pubblicato. La documentazione Meta consiglia controlli entro 5 minuti.

    on_container riceve l'id del carosello pronto PRIMA di media_publish: se la risposta di Meta si perde,
    al giro successivo si controlla quel contenitore invece di ripubblicare.
    """
    if not 2 <= len(image_urls) <= MAX_CAROUSEL_ITEMS:
        raise ValueError(f"un carosello richiede da 2 a {MAX_CAROUSEL_ITEMS} immagini, ricevute {len(image_urls)}")
    children = [
        _call("POST", f"{GRAPH}/{ig_user_id}/media", token, image_url=url, is_carousel_item="true")["id"]
        for url in image_urls
    ]
    for child in children:
        _wait_finished(child, token, poll_interval, max_polls)
    carousel = _call("POST", f"{GRAPH}/{ig_user_id}/media", token,
                     media_type="CAROUSEL", children=",".join(children), caption=caption)["id"]
    _wait_finished(carousel, token, poll_interval, max_polls)
    if on_container:
        on_container(carousel)
    return publish_container(ig_user_id, carousel, token)


def refresh_token(token: str, now: Optional[datetime] = None) -> Tuple[str, datetime]:
    response = requests.get(REFRESH_URL, params={"grant_type": "ig_refresh_token", "access_token": token},
                            timeout=TIMEOUT)
    payload = response.json()
    if response.status_code >= 400 or "access_token" not in payload:
        raise PublishError(f"rinnovo del token non riuscito: {payload.get('error', payload)}")
    now = now or datetime.now(timezone.utc)
    return payload["access_token"], now + timedelta(seconds=int(payload["expires_in"]))

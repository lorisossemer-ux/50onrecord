"""Pubblicazione di caroselli con l'API di Instagram (login unificato, token dell'utente di sistema)."""
from __future__ import annotations

import time
from typing import Callable, List, Optional

import requests

# Le app Meta recenti usano il login unificato: stessi percorsi, host graph.facebook.com.
GRAPH = "https://graph.facebook.com/v26.0"
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


def recent_captions(ig_user_id: str, token: str, limit: int = 10) -> List[str]:
    """Didascalie degli ultimi post del profilo: serve a non ripubblicare un carosello già online."""
    payload = _call("GET", f"{GRAPH}/{ig_user_id}/media?fields=caption&limit={limit}", token)
    return [post["caption"] for post in payload.get("data", []) if post.get("caption")]


def list_media(ig_user_id: str, token: str, limit: int = 50) -> List[dict]:
    """Elenco dei post del profilo (sola lettura): tipo, data, link e didascalia. Serve a tenere il registro delle uscite."""
    fields = "id,caption,media_type,media_product_type,timestamp,permalink"
    payload = _call("GET", f"{GRAPH}/{ig_user_id}/media?fields={fields}&limit={limit}", token)
    return [{"id": post.get("id", ""), "timestamp": post.get("timestamp", ""), "media_type": post.get("media_type", ""),
             "product_type": post.get("media_product_type", ""), "permalink": post.get("permalink", ""),
             "caption": post.get("caption") or ""} for post in payload.get("data", [])]


def publish_container(ig_user_id: str, container_id: str, token: str) -> str:
    return _call("POST", f"{GRAPH}/{ig_user_id}/media_publish", token, creation_id=container_id)["id"]


def prepare_carousel(image_urls: List[str], caption: str, ig_user_id: str, token: str,
                     poll_interval: float = 30, max_polls: int = 10) -> str:
    """Crea e fa elaborare il carosello a Meta senza pubblicarlo: restituisce l'id del contenitore pronto."""
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
    return carousel


def publish_carousel(image_urls: List[str], caption: str, ig_user_id: str, token: str,
                     poll_interval: float = 30, max_polls: int = 10,
                     on_container: Optional[Callable[[str], None]] = None) -> str:
    """Restituisce l'id del post pubblicato. La documentazione Meta consiglia controlli entro 5 minuti.

    on_container riceve l'id del carosello pronto PRIMA di media_publish: se la risposta di Meta si perde,
    al giro successivo si controlla quel contenitore invece di ripubblicare.
    """
    carousel = prepare_carousel(image_urls, caption, ig_user_id, token, poll_interval, max_polls)
    if on_container:
        on_container(carousel)
    return publish_container(ig_user_id, carousel, token)


def check_connection(ig_user_id: str, token: str) -> dict:
    """Prova di sola lettura: nome dell'account e quota di pubblicazione. Non pubblica nulla."""
    profile = _call("GET", f"{GRAPH}/{ig_user_id}?fields=username", token)
    limit = _call("GET", f"{GRAPH}/{ig_user_id}/content_publishing_limit", token).get("data", [{}])[0]
    return {
        "username": profile.get("username", ""),
        "quota_usage": limit.get("quota_usage", 0),
        "quota_total": limit.get("config", {}).get("quota_total", 0),
    }

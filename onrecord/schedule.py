"""Orari di pubblicazione (spec §8) e regole degli avvisi (spec §9)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Collection, Dict, List, Optional
from zoneinfo import ZoneInfo

from .config import Config

MIN_QUEUE_FOR_ALL_SLOTS = 2
MAX_CONSECUTIVE_SKIPS = 2
TOKEN_WARNING = timedelta(days=7)


def _slots_for(local: datetime, cfg: Config) -> List[str]:
    day = local.date()
    if day < cfg.start_date:
        return []
    if day < cfg.start_date + timedelta(days=cfg.phase1_days):
        return cfg.phase1_slots
    return cfg.phase2_slots


def due_slot(now_utc: datetime, cfg: Config, queue_ready: int, published_slots: Collection[str] = ()) -> Optional[str]:
    """Il primo slot di oggi già iniziato e non ancora coperto, con l'etichetta "AAAA-MM-GGTHH:MM".

    Il cron di GitHub può ritardare di ore o saltare run: uno slot resta recuperabile fino a fine giornata, e
    ogni run ne copre uno solo, così anche con un grosso ritardo escono tutti, uno per controllo.
    Con poca coda si tengono gli ultimi slot: lo slot in posizione i (su n) richiede almeno n - i caroselli
    pronti, l'ultimo è sempre dovuto (a coda vuota scatta l'avviso, spec §10)."""
    tz = ZoneInfo(cfg.timezone)
    local = now_utc.astimezone(tz)
    slots = _slots_for(local, cfg)
    published = set(published_slots)
    for index, slot in enumerate(slots):
        hour, minute = (int(x) for x in slot.split(":"))
        if local < datetime(local.year, local.month, local.day, hour, minute, tzinfo=tz):
            break
        label = f"{local.date().isoformat()}T{slot}"
        if label in published:
            continue
        if index < len(slots) - 1 and queue_ready < len(slots) - index:
            continue
        return label
    return None


def alerts(state: Dict, now_utc: datetime, token_expires_utc: datetime) -> List[str]:
    found = []
    if state.get("consecutive_skips", 0) >= MAX_CONSECUTIVE_SKIPS:
        found.append(f"{state['consecutive_skips']} pubblicazioni saltate di fila")
    if state.get("queue_ready", 0) == 0:
        found.append("coda vuota: nessun carosello pronto")
    if token_expires_utc - now_utc <= TOKEN_WARNING:
        found.append(f"token in scadenza (Instagram) il {token_expires_utc.date().isoformat()}")
    return found

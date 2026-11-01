"""Orari di pubblicazione (spec §8) e regole degli avvisi (spec §9)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from .config import Config

SLOT_WINDOW = timedelta(minutes=60)  # il workflow gira ogni 15 minuti; il cron di GitHub può ritardare
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


def due_slot(now_utc: datetime, cfg: Config, queue_ready: int,
             last_published_utc: Optional[datetime]) -> Optional[str]:
    tz = ZoneInfo(cfg.timezone)
    local = now_utc.astimezone(tz)
    slots = _slots_for(local, cfg)
    for slot in slots:
        hour, minute = (int(x) for x in slot.split(":"))
        start = datetime(local.year, local.month, local.day, hour, minute, tzinfo=tz)
        if not (start <= local < start + SLOT_WINDOW):
            continue
        # Con poca coda si tiene solo l'ultimo slot della giornata (spec §10).
        if slot != slots[-1] and queue_ready < MIN_QUEUE_FOR_ALL_SLOTS:
            return None
        if last_published_utc is not None and last_published_utc >= start:
            return None
        return f"{local.date().isoformat()}T{slot}"
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

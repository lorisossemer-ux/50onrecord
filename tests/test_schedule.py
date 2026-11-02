from datetime import date, datetime, timedelta, timezone

import pytest

from onrecord.config import Config
from onrecord.schedule import alerts, due_slot

EVENING_SLOTS = ["19:40", "20:10", "20:40"]


def _cfg(start=date(2026, 6, 1), slots=None, phase2=None):
    return Config(handle="@50onrecord", timezone="Europe/Rome", start_date=start, phase1_days=56,
                  phase1_slots=slots or ["12:30", "20:30"], phase2_slots=phase2 or ["20:30"], first_issue=1)


def _utc(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def _due(now, queue=5, published=(), **cfg):
    return due_slot(_utc(now), _cfg(**cfg), queue, published)


@pytest.mark.parametrize("now,expected", [
    ("2026-07-02T10:35", "2026-07-02T12:30"),   # 12:35 ora legale (CEST)
    ("2026-07-02T11:35", "2026-07-02T12:30"),   # 13:35: il cron di GitHub ha ritardato, lo slot si recupera
    ("2026-07-02T18:30", "2026-07-02T12:30"),   # 20:30: il primo slot è ancora scoperto e ha la precedenza
    ("2026-07-02T21:59", "2026-07-02T12:30"),   # 23:59: recuperabile fino a fine giornata
    ("2026-07-02T22:00", None),                 # 00:00 del giorno dopo: il 12:30 non è ancora iniziato
])
def test_slots_are_recoverable_until_midnight(now, expected):
    assert _due(now) == expected


def test_each_slot_is_published_once_and_in_order():
    now = "2026-07-02T18:35"  # 20:35: entrambi gli slot sono iniziati
    assert _due(now) == "2026-07-02T12:30"
    assert _due(now, published=["2026-07-02T12:30"]) == "2026-07-02T20:30"
    assert _due(now, published=["2026-07-02T12:30", "2026-07-02T20:30"]) is None


def test_winter_time_slot():
    cfg = dict(start=date(2026, 11, 1))
    assert _due("2026-11-02T11:35", **cfg) == "2026-11-02T12:30"
    assert _due("2026-11-02T10:35", **cfg) is None


def test_dst_change_day_publishes_once():
    cfg = dict(start=date(2027, 3, 1))
    assert _due("2027-03-28T10:31", **cfg) == "2027-03-28T12:30"
    assert _due("2027-03-28T11:31", published=["2027-03-28T12:30"], **cfg) is None


def test_phase2_only_evening():
    cfg = _cfg(start=date(2026, 6, 1))
    day57 = date(2026, 6, 1) + timedelta(days=56)
    noon = datetime(day57.year, day57.month, day57.day, 10, 35, tzinfo=timezone.utc)
    evening = datetime(day57.year, day57.month, day57.day, 18, 35, tzinfo=timezone.utc)
    assert due_slot(noon, cfg, 5, []) is None
    assert due_slot(evening, cfg, 5, []) == f"{day57.isoformat()}T20:30"


def test_low_queue_skips_noon_slot():
    assert _due("2026-07-02T10:35", queue=1) is None
    assert _due("2026-07-02T18:35", queue=1) == "2026-07-02T20:30"


def test_nothing_before_start_date():
    assert _due("2026-05-31T18:35") is None


# --- tre slot serali --------------------------------------------------------------------

def test_three_evening_slots_open_one_by_one():
    cfg = dict(slots=EVENING_SLOTS)
    assert _due("2026-07-02T17:30", **cfg) is None                                    # 19:30: prima dello slot
    assert _due("2026-07-02T17:41", **cfg) == "2026-07-02T19:40"                      # 19:41
    assert _due("2026-07-02T18:11", published=["2026-07-02T19:40"], **cfg) == "2026-07-02T20:10"
    assert _due("2026-07-02T18:41", published=["2026-07-02T19:40", "2026-07-02T20:10"], **cfg) == "2026-07-02T20:40"


def test_late_cron_still_publishes_all_three_evening_slots_one_per_run():
    cfg = dict(slots=EVENING_SLOTS)
    now = "2026-07-02T19:30"  # 21:30: il cron di GitHub è arrivato in ritardo
    published = []
    for expected in ("19:40", "20:10", "20:40"):
        label = _due(now, published=published, **cfg)
        assert label == f"2026-07-02T{expected}"
        published.append(label)
    assert _due(now, published=published, **cfg) is None


@pytest.mark.parametrize("queue,expected", [
    (3, "2026-07-02T19:40"),   # coda piena: si parte dal primo slot
    (2, "2026-07-02T20:10"),   # con 2 pronti si tiene il secondo e il terzo
    (1, "2026-07-02T20:40"),   # con 1 pronto solo l'ultimo
])
def test_short_queue_keeps_the_last_slots(queue, expected):
    assert _due("2026-07-02T19:30", queue=queue, slots=EVENING_SLOTS) == expected


def test_alerts():
    now = _utc("2026-07-02T10:00")
    ok_token = now + timedelta(days=30)
    assert alerts({"consecutive_skips": 0, "queue_ready": 3}, now, ok_token) == []
    assert any("2 pubblicazioni saltate" in a for a in alerts({"consecutive_skips": 2, "queue_ready": 3}, now, ok_token))
    assert any("coda vuota" in a for a in alerts({"consecutive_skips": 0, "queue_ready": 0}, now, ok_token))
    assert any("token in scadenza" in a for a in alerts({"consecutive_skips": 0, "queue_ready": 3}, now, now + timedelta(days=6)))

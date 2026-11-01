from datetime import date, datetime, timedelta, timezone

import pytest

from onrecord.config import Config
from onrecord.schedule import alerts, due_slot


def _cfg(start=date(2026, 6, 1)):
    return Config(handle="@50onrecord", timezone="Europe/Rome", start_date=start, phase1_days=56,
                  phase1_slots=["12:30", "20:30"], phase2_slots=["20:30"], first_issue=1)


def _utc(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


@pytest.mark.parametrize("now,expected", [
    ("2026-07-02T10:35", "2026-07-02T12:30"),   # 12:35 ora legale (CEST)
    ("2026-07-02T11:35", None),                 # 13:35: fuori finestra
    ("2026-07-02T18:59", "2026-07-02T20:30"),   # 20:59 ultimo minuto della finestra
    ("2026-07-02T19:00", None),                 # 21:00: finestra chiusa
])
def test_phase1_slots_in_summer_time(now, expected):
    assert due_slot(_utc(now), _cfg(), queue_ready=5, last_published_utc=None) == expected


def test_winter_time_slot():
    cfg = _cfg(start=date(2026, 11, 1))
    assert due_slot(_utc("2026-11-02T11:35"), cfg, 5, None) == "2026-11-02T12:30"
    assert due_slot(_utc("2026-11-02T10:35"), cfg, 5, None) is None


def test_dst_change_day_publishes_once():
    cfg = _cfg(start=date(2027, 3, 1))
    assert due_slot(_utc("2027-03-28T10:31"), cfg, 5, None) == "2027-03-28T12:30"
    assert due_slot(_utc("2027-03-28T11:31"), cfg, 5, None) is None


def test_already_published_slot_not_due_again():
    published = _utc("2026-07-02T10:31")
    assert due_slot(_utc("2026-07-02T10:45"), _cfg(), 5, published) is None


def test_phase2_only_evening():
    cfg = _cfg(start=date(2026, 6, 1))
    day57 = date(2026, 6, 1) + timedelta(days=56)
    noon = datetime(day57.year, day57.month, day57.day, 10, 35, tzinfo=timezone.utc)
    evening = datetime(day57.year, day57.month, day57.day, 18, 35, tzinfo=timezone.utc)
    assert due_slot(noon, cfg, 5, None) is None
    assert due_slot(evening, cfg, 5, None) == f"{day57.isoformat()}T20:30"


def test_low_queue_skips_noon_slot():
    assert due_slot(_utc("2026-07-02T10:35"), _cfg(), queue_ready=1, last_published_utc=None) is None
    assert due_slot(_utc("2026-07-02T18:35"), _cfg(), queue_ready=1, last_published_utc=None) == "2026-07-02T20:30"


def test_nothing_before_start_date():
    assert due_slot(_utc("2026-05-31T18:35"), _cfg(), 5, None) is None


def test_alerts():
    now = _utc("2026-07-02T10:00")
    ok_token = now + timedelta(days=30)
    assert alerts({"consecutive_skips": 0, "queue_ready": 3}, now, ok_token) == []
    assert any("2 pubblicazioni saltate" in a for a in alerts({"consecutive_skips": 2, "queue_ready": 3}, now, ok_token))
    assert any("coda vuota" in a for a in alerts({"consecutive_skips": 0, "queue_ready": 0}, now, ok_token))
    assert any("token in scadenza" in a for a in alerts({"consecutive_skips": 0, "queue_ready": 3}, now, now + timedelta(days=6)))

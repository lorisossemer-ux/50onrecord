"""Lettura di config.toml."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class Config:
    handle: str
    timezone: str
    start_date: date
    phase1_days: int
    phase1_slots: List[str]
    phase2_slots: List[str]
    first_issue: int


def load_config(root: Path) -> Config:
    data = tomllib.loads((Path(root) / "config.toml").read_text(encoding="utf-8"))
    return Config(
        handle=data["handle"],
        timezone=data["timezone"],
        start_date=date.fromisoformat(data["start_date"]),
        phase1_days=int(data["phase1_days"]),
        phase1_slots=list(data["phase1_slots"]),
        phase2_slots=list(data["phase2_slots"]),
        first_issue=int(data.get("first_issue", 1)),
    )

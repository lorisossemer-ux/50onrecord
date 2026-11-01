"""La routine può consegnare solo incoming/<id>/story.json: codice, regole e workflow restano quelli di main."""
from __future__ import annotations

import re
from typing import Iterable, List

_ALLOWED = re.compile(r"^incoming/[a-z0-9][a-z0-9-]*/story\.json$")


def branch_violations(changed_paths: Iterable[str]) -> List[str]:
    return [p for p in (p.strip() for p in changed_paths) if p and not _ALLOWED.match(p)]

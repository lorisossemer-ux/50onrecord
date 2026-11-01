import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def story_dict():
    return json.loads((FIXTURES / "police_message.json").read_text(encoding="utf-8"))

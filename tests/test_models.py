import pytest
from pydantic import ValidationError

from onrecord.models import Story, load_story
from conftest import FIXTURES


def test_story_roundtrip():
    story = load_story(FIXTURES / "police_message.json")
    assert story.slides[0].kind == "cover"
    assert story.decade == "70"


@pytest.mark.parametrize("year", [1958, 2011])
def test_year_outside_range_rejected(story_dict, year):
    story_dict["year"] = year
    with pytest.raises(ValidationError):
        Story(**story_dict)


def test_decade_must_match_year(story_dict):
    story_dict["decade"] = "80"
    with pytest.raises(ValidationError):
        Story(**story_dict)


def test_year_2010_belongs_to_decade_00(story_dict):
    story_dict["year"] = 2010
    story_dict["decade"] = "00"
    assert Story(**story_dict).decade == "00"


@pytest.mark.parametrize("count,ok", [(5, False), (6, True), (8, True), (11, False)])
def test_slide_count_bounds(story_dict, count, ok):
    middle = story_dict["slides"][1]
    story_dict["slides"] = [story_dict["slides"][0]] + [middle] * (count - 2) + [story_dict["slides"][-1]]
    if ok:
        assert len(Story(**story_dict).slides) == count
    else:
        with pytest.raises(ValidationError):
            Story(**story_dict)


def test_first_and_last_slide_kinds(story_dict):
    story_dict["slides"][0]["kind"] = "note"
    with pytest.raises(ValidationError):
        Story(**story_dict)


def test_unknown_fields_rejected(story_dict):
    story_dict["slides"][1]["source_notes"] = "refuso"
    with pytest.raises(ValidationError):
        Story(**story_dict)

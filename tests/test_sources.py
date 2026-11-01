import requests
import responses

from onrecord.models import Story
from onrecord.sources import unreachable_sources


def _all_urls(story):
    return sorted({str(s.url) for f in story.facts for s in f.sources})


@responses.activate
def test_reachable_sources_pass(story_dict):
    story = Story(**story_dict)
    for url in _all_urls(story):
        responses.add(responses.GET, url, status=200)
    assert unreachable_sources(story) == []


@responses.activate
def test_missing_page_rejected(story_dict):
    story = Story(**story_dict)
    urls = _all_urls(story)
    for url in urls[1:]:
        responses.add(responses.GET, url, status=200)
    responses.add(responses.GET, urls[0], status=404)
    errors = unreachable_sources(story)
    assert len(errors) == 1 and urls[0] in errors[0]


@responses.activate
def test_unknown_host_rejected(story_dict):
    story = Story(**story_dict)
    urls = _all_urls(story)
    for url in urls[1:]:
        responses.add(responses.GET, url, status=200)
    responses.add(responses.GET, urls[0], body=requests.exceptions.ConnectionError("dns"))
    assert len(unreachable_sources(story)) == 1


@responses.activate
def test_bot_blocking_sites_are_not_rejected(story_dict):
    story = Story(**story_dict)
    for url in _all_urls(story):
        responses.add(responses.GET, url, status=403)
    assert unreachable_sources(story) == []

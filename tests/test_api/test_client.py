"""Tests for googler_api client (unit + integration).

Unit tests use mocking. Integration tests require network access
and are marked with @pytest.mark.integration.
"""

import json
import os

import pytest

from googler_api import GoogleSearchClient, SearchResponse, SearchResult
from googler_api.exceptions import ConnectionError, SearchError

# --- Unit Tests (no network) ---


class TestClientInit:
    def test_default_init(self):
        client = GoogleSearchClient()
        assert repr(client) == "<GoogleSearchClient [disconnected] tld=None>"

    def test_init_with_tld(self):
        client = GoogleSearchClient(tld="in")
        assert client._tld == "in"

    def test_init_with_all_options(self):
        client = GoogleSearchClient(
            tld="de",
            lang="de",
            geoloc="de",
            proxy="localhost:8118",
            timeout=30,
            ipv4_only=True,
            notweak=True,
        )
        assert client._tld == "de"
        assert client._lang == "de"
        assert client._timeout == 30

    def test_context_manager_protocol(self):
        """Verify __enter__/__exit__ are defined."""
        client = GoogleSearchClient()
        assert hasattr(client, "__enter__")
        assert hasattr(client, "__exit__")

    def test_next_page_without_search_raises(self):
        client = GoogleSearchClient()
        with pytest.raises(SearchError, match="No previous search"):
            client.next_page()

    def test_prev_page_without_search_raises(self):
        client = GoogleSearchClient()
        with pytest.raises(SearchError, match="No previous search"):
            client.prev_page()


# --- Integration Tests (require network) ---

PRESET_OPTIONS = os.getenv("GOOGLER_PRESET_OPTIONS", "").split()
# Detect if we need proxy or IPv4
_needs_proxy = any("--proxy" in opt for opt in PRESET_OPTIONS)
_needs_ipv4 = "--ipv4" in PRESET_OPTIONS or "-4" in PRESET_OPTIONS


def _client_kwargs():
    """Build client kwargs from GOOGLER_PRESET_OPTIONS env var."""
    kwargs = {}
    if _needs_ipv4:
        kwargs["ipv4_only"] = True
    for i, opt in enumerate(PRESET_OPTIONS):
        if opt == "--proxy" and i + 1 < len(PRESET_OPTIONS):
            kwargs["proxy"] = PRESET_OPTIONS[i + 1]
    return kwargs


@pytest.mark.integration
class TestClientIntegration:
    """Integration tests requiring network access.

    Run with: pytest -m integration
    Skip with: pytest -m "not integration"
    """

    def test_basic_search(self):
        with GoogleSearchClient(**_client_kwargs()) as client:
            response = client.search("python programming", num=5)
            assert isinstance(response, SearchResponse)
            assert len(response) > 0
            for r in response:
                assert isinstance(r, SearchResult)
                assert r.title
                assert r.url

    def test_search_returns_abstracts(self):
        with GoogleSearchClient(**_client_kwargs()) as client:
            response = client.search("hello world", num=3)
            # At least some results should have abstracts
            has_abstract = any(r.abstract for r in response)
            assert has_abstract

    def test_search_json_output(self):
        with GoogleSearchClient(**_client_kwargs()) as client:
            json_str = client.search_json("python tutorial", num=3)
            parsed = json.loads(json_str)
            assert isinstance(parsed, list)
            assert len(parsed) > 0
            assert "title" in parsed[0]
            assert "url" in parsed[0]

    def test_search_with_lang(self):
        with GoogleSearchClient(lang="en", **_client_kwargs()) as client:
            response = client.search("google", num=3)
            assert len(response) > 0

    def test_search_with_tld(self):
        with GoogleSearchClient(tld="in", **_client_kwargs()) as client:
            response = client.search("cricket", num=3)
            assert len(response) > 0

    def test_search_exact(self):
        with GoogleSearchClient(**_client_kwargs()) as client:
            response = client.search("gogole", num=3, exact=True)
            assert isinstance(response, SearchResponse)

    def test_site_search(self):
        with GoogleSearchClient(**_client_kwargs()) as client:
            response = client.search(
                "python",
                num=5,
                sites=["docs.python.org"],
            )
            assert len(response) > 0
            for r in response:
                assert "python.org" in r.url or "python" in r.url.lower()

    def test_pagination(self):
        with GoogleSearchClient(**_client_kwargs()) as client:
            page1 = client.search("python tutorial", num=5)
            assert len(page1) > 0

            page2 = client.next_page()
            assert len(page2) > 0
            assert page2.page == 1

            # Results should differ between pages
            page1_urls = {r.url for r in page1}
            page2_urls = {r.url for r in page2}
            assert page1_urls != page2_urls

    def test_video_search(self):
        with GoogleSearchClient(lang="en", **_client_kwargs()) as client:
            response = client.search_videos("python tutorial", num=5)
            assert len(response) > 0

    def test_response_metadata(self):
        with GoogleSearchClient(**_client_kwargs()) as client:
            response = client.search("python", num=5)
            assert response.query == "python"
            assert "google" in response.url.lower()
            assert response.page == 0

    def test_to_dict_matches_json(self):
        """Verify to_dict output structure matches googler --json format."""
        with GoogleSearchClient(**_client_kwargs()) as client:
            response = client.search("test query", num=3)
            for r in response:
                d = r.to_dict()
                assert "title" in d
                assert "url" in d
                assert "abstract" in d

    def test_search_time_filter(self):
        with GoogleSearchClient(**_client_kwargs()) as client:
            response = client.search("python", num=3, duration="y1")
            assert isinstance(response, SearchResponse)

    def test_context_manager_cleanup(self):
        """Verify connection is cleaned up after context exit."""
        client = GoogleSearchClient(**_client_kwargs())
        with client:
            client.search("test", num=1)
            assert client._conn is not None
        assert client._conn is None

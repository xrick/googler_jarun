"""Unit tests for googler_api data models (no network required)."""

import json

import pytest

from googler_api.models import (
    SearchResponse,
    SearchResult,
    SitelinkResult,
    _result_to_search_result,
)


class TestSearchResult:
    def test_basic_creation(self):
        r = SearchResult(title="Test", url="https://example.com", abstract="A test")
        assert r.title == "Test"
        assert r.url == "https://example.com"
        assert r.abstract == "A test"
        assert r.metadata is None
        assert r.sitelinks == []
        assert r.matches == []

    def test_frozen(self):
        r = SearchResult(title="T", url="https://x.com", abstract="A")
        with pytest.raises(AttributeError):
            r.title = "modified"

    def test_to_dict_minimal(self):
        r = SearchResult(title="T", url="https://x.com", abstract="A")
        d = r.to_dict()
        assert d == {"title": "T", "url": "https://x.com", "abstract": "A"}

    def test_to_dict_with_metadata(self):
        r = SearchResult(
            title="News",
            url="https://news.com/1",
            abstract="Breaking",
            metadata="CNN - 2 hours ago",
        )
        d = r.to_dict()
        assert d["metadata"] == "CNN - 2 hours ago"

    def test_to_dict_with_sitelinks(self):
        sl = SitelinkResult(title="Sub", url="https://x.com/sub", abstract="Subpage")
        r = SearchResult(
            title="T",
            url="https://x.com",
            abstract="A",
            sitelinks=[sl],
        )
        d = r.to_dict()
        assert len(d["sitelinks"]) == 1
        assert d["sitelinks"][0]["title"] == "Sub"

    def test_to_dict_with_matches(self):
        r = SearchResult(
            title="T",
            url="https://x.com",
            abstract="A",
            matches=[{"phrase": "test", "offset": 5}],
        )
        d = r.to_dict()
        assert d["matches"] == [{"phrase": "test", "offset": 5}]

    def test_domain_property(self):
        r = SearchResult(title="T", url="https://www.example.com/path", abstract="A")
        assert r.domain == "www.example.com"

    def test_domain_complex_url(self):
        r = SearchResult(
            title="T",
            url="https://docs.python.org/3/library/json.html",
            abstract="A",
        )
        assert r.domain == "docs.python.org"


class TestSitelinkResult:
    def test_creation(self):
        sl = SitelinkResult(title="Sub", url="https://x.com/sub", abstract="Info")
        assert sl.title == "Sub"
        assert sl.url == "https://x.com/sub"
        assert sl.abstract == "Info"

    def test_frozen(self):
        sl = SitelinkResult(title="Sub", url="https://x.com", abstract="A")
        with pytest.raises(AttributeError):
            sl.title = "modified"


class TestSearchResponse:
    def _make_results(self, n=3):
        return [
            SearchResult(
                title=f"Result {i}",
                url=f"https://example.com/{i}",
                abstract=f"Abstract {i}",
            )
            for i in range(n)
        ]

    def test_basic_creation(self):
        results = self._make_results()
        resp = SearchResponse(
            results=results, query="test", url="https://google.com/search?q=test"
        )
        assert len(resp) == 3
        assert resp.query == "test"
        assert resp.autocorrected is False
        assert resp.page == 0

    def test_iteration(self):
        results = self._make_results(2)
        resp = SearchResponse(results=results, query="test", url="https://google.com")
        titles = [r.title for r in resp]
        assert titles == ["Result 0", "Result 1"]

    def test_indexing(self):
        results = self._make_results(3)
        resp = SearchResponse(results=results, query="test", url="https://google.com")
        assert resp[0].title == "Result 0"
        assert resp[2].title == "Result 2"

    def test_bool_nonempty(self):
        resp = SearchResponse(results=self._make_results(1), query="q", url="u")
        assert bool(resp) is True

    def test_bool_empty(self):
        resp = SearchResponse(results=[], query="q", url="u")
        assert bool(resp) is False

    def test_to_dicts(self):
        results = self._make_results(2)
        resp = SearchResponse(results=results, query="q", url="u")
        dicts = resp.to_dicts()
        assert len(dicts) == 2
        assert dicts[0]["title"] == "Result 0"

    def test_to_json(self):
        results = self._make_results(1)
        resp = SearchResponse(results=results, query="q", url="u")
        j = resp.to_json()
        parsed = json.loads(j)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "Result 0"

    def test_autocorrect_metadata(self):
        resp = SearchResponse(
            results=[],
            query="pythn",
            url="u",
            autocorrected=True,
            showing_results_for="python",
        )
        assert resp.autocorrected is True
        assert resp.showing_results_for == "python"


class TestResultConversion:
    """Test _result_to_search_result with mock objects."""

    def test_basic_conversion(self):
        class MockResult:
            title = "Mock Title"
            url = "https://mock.com"
            abstract = "Mock abstract"
            metadata = None
            sitelinks = []
            matches = []

        sr = _result_to_search_result(MockResult())
        assert sr.title == "Mock Title"
        assert sr.url == "https://mock.com"
        assert sr.abstract == "Mock abstract"
        assert isinstance(sr, SearchResult)

    def test_conversion_with_metadata(self):
        class MockResult:
            title = "News"
            url = "https://news.com"
            abstract = "Breaking"
            metadata = "CNN - 2h ago"
            sitelinks = []
            matches = []

        sr = _result_to_search_result(MockResult())
        assert sr.metadata == "CNN - 2h ago"

    def test_conversion_with_sitelinks(self):
        class MockSitelink:
            title = "Sub"
            url = "https://x.com/sub"
            abstract = "Sub abstract"

        class MockResult:
            title = "T"
            url = "https://x.com"
            abstract = "A"
            metadata = None
            sitelinks = [MockSitelink()]
            matches = []

        sr = _result_to_search_result(MockResult())
        assert len(sr.sitelinks) == 1
        assert sr.sitelinks[0].title == "Sub"

    def test_conversion_with_matches(self):
        class MockResult:
            title = "T"
            url = "https://x.com"
            abstract = "A"
            metadata = None
            sitelinks = []
            matches = [{"phrase": "python", "offset": 0}]

        sr = _result_to_search_result(MockResult())
        assert len(sr.matches) == 1
        assert sr.matches[0]["phrase"] == "python"

    def test_conversion_missing_optional_attrs(self):
        """Result objects without optional attrs should still convert."""

        class MinimalResult:
            title = "T"
            url = "https://x.com"
            abstract = "A"

        sr = _result_to_search_result(MinimalResult())
        assert sr.title == "T"
        assert sr.metadata is None
        assert sr.sitelinks == []
        assert sr.matches == []

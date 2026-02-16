"""Data models for googler API responses."""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SitelinkResult:
    """A sitelink within a search result."""

    title: str
    url: str
    abstract: str


@dataclass(frozen=True)
class SearchResult:
    """A single search result.

    Attributes
    ----------
    title : str
        The result title.
    url : str
        The result URL.
    abstract : str
        The result snippet/abstract.
    metadata : str or None
        Extra metadata (e.g. publisher + time for news results).
    sitelinks : list of SitelinkResult
        Sub-links within this result.
    matches : list of dict
        Keyword match positions: [{"phrase": str, "offset": int}, ...].
    """

    title: str
    url: str
    abstract: str
    metadata: Optional[str] = None
    sitelinks: List[SitelinkResult] = field(default_factory=list)
    matches: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict.

        Output format matches googler's ``--json`` output.
        """
        obj = {
            "title": self.title,
            "url": self.url,
            "abstract": self.abstract,
        }
        if self.metadata:
            obj["metadata"] = self.metadata
        if self.sitelinks:
            obj["sitelinks"] = [
                {"title": s.title, "url": s.url, "abstract": s.abstract}
                for s in self.sitelinks
            ]
        if self.matches:
            obj["matches"] = self.matches
        return obj

    @property
    def domain(self) -> str:
        """Extract the domain from the URL."""
        from urllib.parse import urlparse

        return urlparse(self.url).netloc


@dataclass
class SearchResponse:
    """Complete search response with metadata.

    Supports iteration and indexing over results directly.

    Attributes
    ----------
    results : list of SearchResult
        The search results.
    query : str
        The query that was searched.
    url : str
        The full Google URL that was fetched.
    autocorrected : bool
        Whether Google auto-corrected the query.
    showing_results_for : str or None
        The corrected query string, if auto-corrected.
    filtered : bool
        Whether Google filtered similar results.
    page : int
        The current page number (0-indexed).
    """

    results: List[SearchResult]
    query: str
    url: str
    autocorrected: bool = False
    showing_results_for: Optional[str] = None
    filtered: bool = False
    page: int = 0

    def to_json(self, indent: int = 2) -> str:
        """Serialize results to JSON string.

        Output format matches googler's ``--json`` output.
        """
        return json.dumps(
            self.to_dicts(),
            indent=indent,
            sort_keys=True,
            ensure_ascii=False,
        )

    def to_dicts(self) -> List[dict]:
        """Convert results to list of dicts."""
        return [r.to_dict() for r in self.results]

    def __len__(self) -> int:
        return len(self.results)

    def __iter__(self):
        return iter(self.results)

    def __getitem__(self, index):
        return self.results[index]

    def __bool__(self) -> bool:
        return len(self.results) > 0


def _result_to_search_result(result) -> SearchResult:
    """Convert a googler internal Result to a SearchResult.

    Parameters
    ----------
    result : googler.Result
        An internal Result object from the googler parser.

    Returns
    -------
    SearchResult
    """
    sitelinks = []
    if hasattr(result, "sitelinks") and result.sitelinks:
        for sl in result.sitelinks:
            sitelinks.append(
                SitelinkResult(
                    title=getattr(sl, "title", ""),
                    url=getattr(sl, "url", ""),
                    abstract=getattr(sl, "abstract", ""),
                )
            )

    matches = []
    if hasattr(result, "matches") and result.matches:
        matches = list(result.matches)

    return SearchResult(
        title=result.title or "",
        url=result.url or "",
        abstract=result.abstract or "",
        metadata=getattr(result, "metadata", None),
        sitelinks=sitelinks,
        matches=matches,
    )

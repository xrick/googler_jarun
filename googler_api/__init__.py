"""googler_api - Python API for Google Search via googler.

Provides programmatic access to Google web, news, and video search
using googler's battle-tested internals. Zero external dependencies.

Quick start::

    from googler_api import search
    results = search("python programming")
    for r in results:
        print(r.title, r.url)

Full client::

    from googler_api import GoogleSearchClient
    with GoogleSearchClient(lang='en') as client:
        response = client.search('python', num=5)
        for result in response:
            print(result.title)
"""

__version__ = "0.1.0-alpha"

from googler_api.client import GoogleSearchClient
from googler_api.exceptions import (
    ConnectionError,
    GooglerAPIError,
    ParseError,
    RateLimitError,
    SearchError,
)
from googler_api.models import SearchResponse, SearchResult, SitelinkResult

__all__ = [
    # Convenience functions
    "search",
    "search_news",
    "search_videos",
    # Client class
    "GoogleSearchClient",
    # Data models
    "SearchResult",
    "SitelinkResult",
    "SearchResponse",
    # Exceptions
    "GooglerAPIError",
    "ConnectionError",
    "SearchError",
    "ParseError",
    "RateLimitError",
]


def search(
    query: str,
    *,
    num: int = 10,
    lang: str = None,
    tld: str = None,
    geoloc: str = None,
    start: int = 0,
    exact: bool = False,
    duration: str = None,
    date_from: str = None,
    date_to: str = None,
    sites: list = None,
    exclude: list = None,
    unfilter: bool = False,
    proxy: str = None,
    timeout: int = 45,
    ipv4_only: bool = False,
    notweak: bool = False,
) -> list:
    """Perform a Google web search and return results.

    This is a convenience function that creates a temporary client,
    executes the search, and returns the results list.

    Parameters
    ----------
    query : str
        Search keywords.
    num : int
        Number of results. Default 10.
    lang : str, optional
        Display language (e.g., 'en', 'de').
    tld : str, optional
        Country TLD (e.g., 'in', 'co.uk').
    geoloc : str, optional
        Country code for geolocation search.
    start : int
        Starting result offset. Default 0.
    exact : bool
        Disable auto-spelling correction. Default False.
    duration : str, optional
        Time limit (e.g., 'h5', 'd5', 'w5', 'm5', 'y5').
    date_from : str, optional
        Start date in MM/DD/YYYY format.
    date_to : str, optional
        End date in MM/DD/YYYY format.
    sites : list of str, optional
        Restrict to these domains.
    exclude : list of str, optional
        Exclude these domains.
    unfilter : bool
        Show similar/filtered results. Default False.
    proxy : str, optional
        HTTPS proxy spec.
    timeout : int
        Connection timeout seconds. Default 45.
    ipv4_only : bool
        Force IPv4. Default False.
    notweak : bool
        Disable TCP optimizations. Default False.

    Returns
    -------
    list of SearchResult
        Search results.

    Examples
    --------
    >>> from googler_api import search
    >>> results = search("python dataclasses", num=3, lang="en")
    >>> for r in results:
    ...     print(r.title)
    """
    with GoogleSearchClient(
        tld=tld,
        lang=lang,
        geoloc=geoloc,
        proxy=proxy,
        timeout=timeout,
        ipv4_only=ipv4_only,
        notweak=notweak,
    ) as client:
        response = client.search(
            query,
            num=num,
            start=start,
            exact=exact,
            duration=duration,
            date_from=date_from,
            date_to=date_to,
            sites=sites,
            exclude=exclude,
            unfilter=unfilter,
        )
        return response.results


def search_news(query: str, **kwargs) -> list:
    """Perform a Google News search.

    Parameters
    ----------
    query : str
        Search keywords.
    **kwargs
        Additional parameters passed to ``search()``.

    Returns
    -------
    list of SearchResult
    """
    with GoogleSearchClient(
        tld=kwargs.pop("tld", None),
        lang=kwargs.pop("lang", None),
        geoloc=kwargs.pop("geoloc", None),
        proxy=kwargs.pop("proxy", None),
        timeout=kwargs.pop("timeout", 45),
        ipv4_only=kwargs.pop("ipv4_only", False),
        notweak=kwargs.pop("notweak", False),
    ) as client:
        response = client.search_news(query, **kwargs)
        return response.results


def search_videos(query: str, **kwargs) -> list:
    """Perform a Google Videos search.

    Parameters
    ----------
    query : str
        Search keywords.
    **kwargs
        Additional parameters passed to ``search()``.

    Returns
    -------
    list of SearchResult
    """
    with GoogleSearchClient(
        tld=kwargs.pop("tld", None),
        lang=kwargs.pop("lang", None),
        geoloc=kwargs.pop("geoloc", None),
        proxy=kwargs.pop("proxy", None),
        timeout=kwargs.pop("timeout", 45),
        ipv4_only=kwargs.pop("ipv4_only", False),
        notweak=kwargs.pop("notweak", False),
    ) as client:
        response = client.search_videos(query, **kwargs)
        return response.results

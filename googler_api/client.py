"""Main API client for Google searches via googler."""

from typing import List, Optional

from googler_api._compat import GoogleConnectionError, GoogleParser
from googler_api.connection import ManagedConnection
from googler_api.exceptions import ConnectionError, ParseError, SearchError
from googler_api.models import SearchResponse, _result_to_search_result
from googler_api.url_builder import build_url


class GoogleSearchClient:
    """Client for performing Google searches programmatically.

    Uses googler's internals to fetch and parse Google search results.
    Supports web, news, and video searches with pagination.

    Parameters
    ----------
    tld : str, optional
        Country-specific TLD (e.g., 'in' for India, 'co.uk' for UK).
    lang : str, optional
        Display language (e.g., 'en', 'de', 'ja').
    geoloc : str, optional
        Country code for geolocation-based search.
    proxy : str, optional
        HTTP proxy (e.g., 'localhost:8118').
    timeout : int
        Connection timeout in seconds. Default 45.
    ipv4_only : bool
        Only connect over IPv4. Default False.
    ipv6_only : bool
        Only connect over IPv6. Default False.
    notweak : bool
        Disable TCP optimizations and TLS 1.2 enforcement. Default False.

    Examples
    --------
    Using as context manager (recommended)::

        with GoogleSearchClient(lang='en') as client:
            response = client.search('python programming', num=5)
            for result in response:
                print(result.title, result.url)

    Manual lifecycle::

        client = GoogleSearchClient()
        client.connect()
        try:
            response = client.search('test query')
        finally:
            client.close()
    """

    def __init__(
        self,
        *,
        tld: Optional[str] = None,
        lang: Optional[str] = None,
        geoloc: Optional[str] = None,
        proxy: Optional[str] = None,
        timeout: int = 45,
        ipv4_only: bool = False,
        ipv6_only: bool = False,
        notweak: bool = False,
    ):
        self._tld = tld
        self._lang = lang
        self._geoloc = geoloc
        self._proxy = proxy
        self._timeout = timeout
        self._ipv4_only = ipv4_only
        self._ipv6_only = ipv6_only
        self._notweak = notweak

        self._conn: Optional[ManagedConnection] = None
        self._google_url = None
        self._current_page = 0
        self._last_query = None
        self._last_kwargs = {}

    def connect(self):
        """Establish connection to Google.

        Called automatically when using the client as a context manager
        or when performing the first search.
        """
        if self._conn is not None and self._conn.is_connected:
            return

        # Determine hostname from TLD
        hostname = "www.google.com"
        if self._tld:
            hostname = f"www.google.{self._tld}"

        self._conn = ManagedConnection(
            hostname,
            proxy=self._proxy,
            timeout=self._timeout,
            ipv4_only=self._ipv4_only,
            ipv6_only=self._ipv6_only,
            notweak=self._notweak,
        )
        self._conn.connect()

    def close(self):
        """Close the connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def search(
        self,
        query: str,
        *,
        num: int = 10,
        start: int = 0,
        exact: bool = False,
        duration: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sites: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        unfilter: bool = False,
        news: bool = False,
        videos: bool = False,
    ) -> SearchResponse:
        """Execute a Google search.

        Parameters
        ----------
        query : str
            Search keywords.
        num : int
            Number of results to fetch. Default 10.
        start : int
            Starting result offset. Default 0.
        exact : bool
            Disable automatic spelling correction. Default False.
        duration : str, optional
            Time limit filter (e.g., 'h5', 'd5', 'w5', 'm5', 'y5').
        date_from : str, optional
            Start date in MM/DD/YYYY format.
        date_to : str, optional
            End date in MM/DD/YYYY format.
        sites : list of str, optional
            Restrict search to these domains.
        exclude : list of str, optional
            Exclude these domains from results.
        unfilter : bool
            Show similar results that Google normally filters. Default False.
        news : bool
            Search Google News. Default False.
        videos : bool
            Search Google Videos. Default False.

        Returns
        -------
        SearchResponse
            The search response containing results and metadata.

        Raises
        ------
        ConnectionError
            If the connection to Google fails.
        SearchError
            If the search request fails.
        ParseError
            If the response HTML cannot be parsed.
        """
        self.connect()

        # Store for pagination
        self._last_query = query
        self._last_kwargs = dict(
            num=num,
            exact=exact,
            duration=duration,
            date_from=date_from,
            date_to=date_to,
            sites=sites,
            exclude=exclude,
            unfilter=unfilter,
            news=news,
            videos=videos,
        )
        self._current_page = start // num if num > 0 else 0

        # Build URL
        self._google_url = build_url(
            query,
            num=num,
            start=start,
            lang=self._lang,
            geoloc=self._geoloc,
            tld=self._tld,
            exact=exact,
            duration=duration,
            date_from=date_from,
            date_to=date_to,
            sites=sites,
            exclude=exclude,
            unfilter=unfilter,
            news=news,
            videos=videos,
        )

        # Handle hostname change if TLD changed the URL's host
        url_host = self._google_url.hostname
        if self._conn.host != url_host:
            self._conn.reconnect(url_host)

        return self._fetch_and_parse()

    def search_news(self, query: str, **kwargs) -> SearchResponse:
        """Execute a Google News search.

        Parameters
        ----------
        query : str
            Search keywords.
        **kwargs
            Additional parameters passed to ``search()``.

        Returns
        -------
        SearchResponse
        """
        return self.search(query, news=True, **kwargs)

    def search_videos(self, query: str, **kwargs) -> SearchResponse:
        """Execute a Google Videos search.

        Parameters
        ----------
        query : str
            Search keywords.
        **kwargs
            Additional parameters passed to ``search()``.

        Returns
        -------
        SearchResponse
        """
        return self.search(query, videos=True, **kwargs)

    def next_page(self) -> SearchResponse:
        """Fetch the next page of results.

        Requires a previous ``search()`` call.

        Returns
        -------
        SearchResponse

        Raises
        ------
        SearchError
            If no previous search was performed.
        """
        if self._google_url is None:
            raise SearchError(
                "No previous search to paginate from. Call search() first."
            )

        self._google_url.next_page()
        self._current_page += 1
        return self._fetch_and_parse()

    def prev_page(self) -> SearchResponse:
        """Fetch the previous page of results.

        Returns
        -------
        SearchResponse

        Raises
        ------
        SearchError
            If already at the first page or no previous search.
        """
        if self._google_url is None:
            raise SearchError(
                "No previous search to paginate from. Call search() first."
            )

        try:
            self._google_url.prev_page()
        except ValueError as e:
            raise SearchError("Already at the first page.") from e

        self._current_page -= 1
        return self._fetch_and_parse()

    def search_json(self, query: str, **kwargs) -> str:
        """Execute a search and return results as a JSON string.

        Output format matches googler's ``--json`` output.

        Parameters
        ----------
        query : str
            Search keywords.
        **kwargs
            Additional parameters passed to ``search()``.

        Returns
        -------
        str
            JSON string of results.
        """
        response = self.search(query, **kwargs)
        return response.to_json()

    def _fetch_and_parse(self) -> SearchResponse:
        """Fetch the current URL and parse results.

        Returns
        -------
        SearchResponse
        """
        # Fetch page
        try:
            html = self._conn.fetch_page(self._google_url.relative())
        except ConnectionError:
            raise
        except Exception as e:
            raise SearchError(f"Search request failed: {e}") from e

        # Parse results
        try:
            parser = GoogleParser(
                html,
                news=self._google_url.news,
                videos=self._google_url.videos,
            )
        except Exception as e:
            raise ParseError(f"Failed to parse search results: {e}") from e

        # Convert internal Result objects to SearchResult dataclasses
        results = [_result_to_search_result(r) for r in parser.results]

        return SearchResponse(
            results=results,
            query=self._last_query or "",
            url=self._google_url.full(),
            autocorrected=parser.autocorrected,
            showing_results_for=parser.showing_results_for,
            filtered=parser.filtered,
            page=self._current_page,
        )

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def __repr__(self):
        status = (
            "connected" if (self._conn and self._conn.is_connected) else "disconnected"
        )
        return f"<GoogleSearchClient [{status}] tld={self._tld}>"

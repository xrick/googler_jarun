# Googler Python API Design Plan

## Date: 2026-02-14
## Status: Draft
## Type: API Specification & Implementation Plan

---

## 1. Architecture Analysis Summary

### 1.1 Current Codebase Structure

The `googler` project is a **single-file Python 3 executable** (~3,900 lines) with zero external dependencies. All code resides in the `googler` file (no `.py` extension). The architecture consists of five logical layers:

```
Layer 5: CLI Interface
  GooglerArgumentParser, parse_args(), main()

Layer 4: Interactive Shell
  GooglerCmd (REPL, browser integration, clipboard, display)

Layer 3: Result Parsing
  GoogleParser, Result, Sitelink (HTML -> structured data)

Layer 2: Google API / Network
  GoogleUrl, GoogleConnection, HardenedHTTPSConnection, GoogleConnectionError

Layer 1: HTML Parsing Engine (DOM)
  Node, ElementNode, TextNode, DOMBuilder, SelectorGroup, Selector, AttributeSelector
  (~1,260 lines of custom DOM/CSS parser replacing BeautifulSoup)
```

### 1.2 Key Classes & Their Roles

| Class | Lines | Role | API-Extractable? |
|-------|-------|------|------------------|
| `GoogleUrl` | 1673-2064 | URL construction, query params, pagination | Yes (core) |
| `GoogleConnection` | 2069-2320 | HTTPS client, TLS, proxy, fetch | Yes (core) |
| `GoogleParser` | 2322-2552 | HTML parsing -> Result objects | Yes (core) |
| `Result` | 2576-2748 | Search result data container | Yes (core) |
| `Sitelink` | 2553-2575 | Sub-result link container | Yes (core) |
| `GooglerCmd` | 2785-3258 | CLI REPL, display, browser integration | Partial (fetch logic only) |
| `HardenedHTTPSConnection` | 1581-1671 | TLS 1.2 enforced HTTPS | Yes (internal) |
| `GooglerArgumentParser` | 3260-3500 | CLI argument parsing | No (CLI only) |
| DOM classes | 175-1570 | Custom HTML/CSS parser | Yes (internal) |

### 1.3 Data Flow (Current)

```
User CLI args -> parse_args() -> argparse.Namespace
  -> GooglerCmd.__init__(opts)
    -> GoogleUrl(opts)           # Build search URL
    -> GoogleConnection(host)    # Establish HTTPS connection
  -> GooglerCmd.fetch()
    -> GoogleConnection.fetch_page(url)  # HTTP GET
    -> GoogleParser(html)                # Parse HTML response
    -> List[Result]                      # Structured results
  -> GooglerCmd.display_results()        # Print or JSON dump
```

### 1.4 Coupling Issues for API Extraction

1. **Global state**: `debugger` global variable, `logger` module-level, `COLORMAP` constants
2. **Class variables on Result**: `Result.colors` and `Result.urlexpand` set in `main()`
3. **GoogleUrl.__init__** assumes `opts.html_file` exists (crashes without it)
4. **GooglerCmd** mixes fetch logic with display/browser/clipboard logic
5. **atexit registration**: `GoogleConnection` registers cleanup via atexit in `GooglerCmd`
6. **No `__all__`**: No deliberate public API surface defined

---

## 2. API Design

### 2.1 Design Philosophy

- **Wrapper, not fork**: Build a Python package that imports from the existing `googler` file
- **Preserve single-file**: Don't modify the original `googler` executable
- **Zero new dependencies**: API wrapper uses only stdlib + googler internals
- **Pythonic interface**: Dataclasses, context managers, iterators, type hints
- **Progressive disclosure**: Simple `search()` function for basic use, full class access for power users

### 2.2 Package Structure

```
googler/                          # Existing project root
  googler                         # Original executable (unchanged)
  googler_api/                    # New package directory
    __init__.py                   # Public API surface
    client.py                     # GoogleSearchClient (main API class)
    models.py                     # SearchResult, SearchConfig, SearchResponse dataclasses
    connection.py                 # Connection wrapper with context manager
    url_builder.py                # URL builder wrapper
    exceptions.py                 # Custom exceptions
    _compat.py                    # Import bridge to googler internals
  tests/
    test_googler.py               # Existing tests (unchanged)
    test_api/                     # New API tests
      __init__.py
      test_client.py
      test_models.py
      test_connection.py
      test_integration.py
  pyproject.toml                  # New: package configuration
```

### 2.3 Core API Surface

#### 2.3.1 High-Level API (Simple Usage)

```python
from googler_api import search, search_news, search_videos

# Basic search - returns List[SearchResult]
results = search("python programming")

# With options
results = search(
    "python tutorial",
    num=5,
    lang="en",
    tld="com",
    start=0,
    exact=True,
)

# News search
results = search_news("AI breakthrough", lang="en")

# Video search
results = search_videos("PyCon 2025", num=10)

# Site-specific search
results = search(
    "machine learning",
    sites=["arxiv.org", "scholar.google.com"],
)

# Time-filtered search
results = search("python 3.12", duration="m6")  # last 6 months

# Date range search
results = search("election", date_from="01/01/2024", date_to="12/31/2024")
```

#### 2.3.2 Client API (Full Control)

```python
from googler_api import GoogleSearchClient

# Context manager for connection lifecycle
with GoogleSearchClient(
    tld="com",
    lang="en",
    proxy="localhost:8118",
    timeout=30,
    ipv4_only=True,
    notweak=False,
) as client:
    # Search with pagination
    response = client.search("python programming", num=10)
    print(response.results)        # List[SearchResult]
    print(response.total_estimated) # Estimated total results (if available)
    print(response.autocorrected)   # Was query auto-corrected?
    print(response.showing_results_for)  # Actual query if corrected
    
    # Pagination
    next_response = client.next_page()
    prev_response = client.prev_page()
    
    # Direct page access
    page3 = client.search("python", num=10, start=20)
    
    # News search
    news = client.search_news("AI", num=5)
    
    # Video search
    videos = client.search_videos("tutorial", num=5)
    
    # Site search
    site_results = client.search(
        "bug report",
        sites=["github.com"],
        exclude=["stackoverflow.com"],
    )
    
    # Get raw JSON (matches existing --json output)
    json_data = client.search_json("python")
```

#### 2.3.3 Data Models

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass(frozen=True)
class SearchResult:
    """A single search result."""
    title: str
    url: str
    abstract: str
    metadata: Optional[str] = None          # News: publisher + time
    sitelinks: List['SitelinkResult'] = field(default_factory=list)
    matches: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict (matches googler --json format)."""
        ...
    
    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        ...


@dataclass(frozen=True)
class SitelinkResult:
    """A sitelink within a search result."""
    title: str
    url: str
    abstract: str


@dataclass
class SearchConfig:
    """Configuration for search parameters."""
    num: int = 10
    start: int = 0
    lang: Optional[str] = None
    geoloc: Optional[str] = None
    tld: Optional[str] = None
    exact: bool = False
    duration: Optional[str] = None       # e.g., "h5", "d5", "w5", "m5", "y5"
    date_from: Optional[str] = None      # e.g., "01/01/2024"
    date_to: Optional[str] = None        # e.g., "12/31/2024"
    sites: Optional[List[str]] = None
    exclude: Optional[List[str]] = None
    unfilter: bool = False


@dataclass
class ConnectionConfig:
    """Configuration for network connection."""
    proxy: Optional[str] = None
    timeout: int = 45
    ipv4_only: bool = False
    ipv6_only: bool = False
    notweak: bool = False


@dataclass
class SearchResponse:
    """Complete search response with metadata."""
    results: List[SearchResult]
    query: str
    url: str                              # The Google URL that was fetched
    autocorrected: bool = False
    showing_results_for: Optional[str] = None
    filtered: bool = False
    page: int = 0
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        ...
    
    def to_dicts(self) -> List[dict]:
        """Convert results to list of dicts (matches googler --json format)."""
        ...
    
    def __len__(self) -> int:
        return len(self.results)
    
    def __iter__(self):
        return iter(self.results)
    
    def __getitem__(self, index):
        return self.results[index]
```

#### 2.3.4 Exceptions

```python
class GooglerAPIError(Exception):
    """Base exception for googler API."""
    pass

class ConnectionError(GooglerAPIError):
    """Network connection failed."""
    pass

class SearchError(GooglerAPIError):
    """Search request failed."""
    pass

class ParseError(GooglerAPIError):
    """Failed to parse Google's response."""
    pass

class RateLimitError(GooglerAPIError):
    """Google is rate-limiting requests."""
    pass
```

### 2.4 Internal Architecture

#### 2.4.1 Import Bridge (`_compat.py`)

The critical challenge: importing from a file with no `.py` extension.

```python
"""Bridge to import googler internals without modifying the original file."""
import importlib.util
import pathlib

def _import_googler():
    """Import the googler executable as a Python module."""
    googler_path = pathlib.Path(__file__).parent.parent / 'googler'
    spec = importlib.util.spec_from_file_location('_googler', googler_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_googler = _import_googler()

# Re-export internals we need
GoogleUrl = _googler.GoogleUrl
GoogleConnection = _googler.GoogleConnection
GoogleConnectionError = _googler.GoogleConnectionError
GoogleParser = _googler.GoogleParser
Result = _googler.Result
Sitelink = _googler.Sitelink
```

#### 2.4.2 Client Implementation (`client.py`)

```python
class GoogleSearchClient:
    """Main API client for Google searches via googler."""
    
    def __init__(self, *, tld=None, lang=None, geoloc=None,
                 proxy=None, timeout=45, ipv4_only=False, 
                 ipv6_only=False, notweak=False):
        # Build a mock opts namespace that GoogleUrl expects
        self._search_config = SearchConfig(tld=tld, lang=lang, geoloc=geoloc)
        self._conn_config = ConnectionConfig(
            proxy=proxy, timeout=timeout,
            ipv4_only=ipv4_only, ipv6_only=ipv6_only,
            notweak=notweak,
        )
        self._google_url = None
        self._conn = None
    
    def __enter__(self):
        self._connect()
        return self
    
    def __exit__(self, *exc):
        self.close()
    
    def _connect(self):
        """Establish connection to Google."""
        # Build GoogleUrl with a synthetic opts namespace
        # Build GoogleConnection with connection config
        ...
    
    def search(self, query, *, num=10, start=0, **kwargs) -> SearchResponse:
        """Execute a web search."""
        ...
    
    def search_news(self, query, **kwargs) -> SearchResponse:
        """Execute a news search."""
        return self.search(query, news=True, **kwargs)
    
    def search_videos(self, query, **kwargs) -> SearchResponse:
        """Execute a video search."""
        return self.search(query, videos=True, **kwargs)
    
    def next_page(self) -> SearchResponse:
        """Fetch the next page of results."""
        ...
    
    def prev_page(self) -> SearchResponse:
        """Fetch the previous page of results."""
        ...
    
    def search_json(self, query, **kwargs) -> str:
        """Execute search and return raw JSON string."""
        ...
    
    def close(self):
        """Close the connection."""
        ...
```

#### 2.4.3 Adapting GoogleUrl for API Use

The main challenge with `GoogleUrl.__init__` is that it accesses `opts.html_file` directly. The API wrapper needs to provide a synthetic namespace:

```python
def _build_opts_namespace(query, config: SearchConfig, news=False, videos=False):
    """Build an argparse.Namespace-like object for GoogleUrl."""
    from types import SimpleNamespace
    return SimpleNamespace(
        keywords=query.split() if isinstance(query, str) else query,
        num=config.num,
        start=config.start,
        lang=config.lang,
        geoloc=config.geoloc,
        tld=config.tld,
        exact=config.exact,
        duration=config.duration,
        sites=config.sites,
        exclude=config.exclude,
        unfilter=config.unfilter,
        news=news,
        videos=videos,
        html_file=None,  # Required to prevent AttributeError
        **({'from': config.date_from} if config.date_from else {}),
        **({'to': config.date_to} if config.date_to else {}),
    )
```

### 2.5 Module-Level Convenience Functions

```python
# googler_api/__init__.py

from googler_api.client import GoogleSearchClient
from googler_api.models import SearchResult, SearchResponse, SearchConfig
from googler_api.exceptions import (
    GooglerAPIError, ConnectionError, SearchError, ParseError, RateLimitError
)

__all__ = [
    'search', 'search_news', 'search_videos',
    'GoogleSearchClient',
    'SearchResult', 'SearchResponse', 'SearchConfig',
    'GooglerAPIError', 'ConnectionError', 'SearchError', 'ParseError', 'RateLimitError',
]

def search(query, *, num=10, lang=None, tld=None, start=0,
           exact=False, duration=None, date_from=None, date_to=None,
           sites=None, exclude=None, proxy=None, timeout=45,
           ipv4_only=False, notweak=False, **kwargs) -> list:
    """
    Perform a Google web search and return results.
    
    This is a convenience function that creates a temporary client,
    executes the search, and returns the results list.
    
    Parameters
    ----------
    query : str
        Search keywords.
    num : int, optional
        Number of results to return. Default 10.
    lang : str, optional
        Display language (e.g., 'en', 'de', 'ja').
    tld : str, optional
        Country TLD for Google domain (e.g., 'in', 'co.uk').
    start : int, optional
        Start at the Nth result. Default 0.
    exact : bool, optional
        Disable automatic spelling correction. Default False.
    duration : str, optional
        Time limit (e.g., 'h5', 'd5', 'w5', 'm5', 'y5').
    date_from : str, optional
        Start date in MM/DD/YYYY format.
    date_to : str, optional
        End date in MM/DD/YYYY format.
    sites : list of str, optional
        Restrict search to these sites.
    exclude : list of str, optional
        Exclude these sites from results.
    proxy : str, optional
        HTTPS proxy (e.g., 'localhost:8118').
    timeout : int, optional
        Connection timeout in seconds. Default 45.
    ipv4_only : bool, optional
        Only connect over IPv4. Default False.
    notweak : bool, optional
        Disable TCP optimizations. Default False.
    
    Returns
    -------
    list of SearchResult
        Search results.
    """
    with GoogleSearchClient(
        tld=tld, lang=lang, proxy=proxy,
        timeout=timeout, ipv4_only=ipv4_only,
        notweak=notweak,
    ) as client:
        response = client.search(
            query, num=num, start=start, exact=exact,
            duration=duration, date_from=date_from, date_to=date_to,
            sites=sites, exclude=exclude, **kwargs,
        )
        return response.results


def search_news(query, **kwargs) -> list:
    """Perform a Google News search. See search() for parameters."""
    kwargs['news'] = True
    return search(query, **kwargs)


def search_videos(query, **kwargs) -> list:
    """Perform a Google Video search. See search() for parameters."""
    kwargs['videos'] = True
    return search(query, **kwargs)
```

---

## 3. Implementation Plan

### Phase 1: Foundation (Core Infrastructure)

| Step | Task | Files | Depends On |
|------|------|-------|------------|
| 1.1 | Create package structure | `googler_api/__init__.py`, dirs | - |
| 1.2 | Implement import bridge | `googler_api/_compat.py` | 1.1 |
| 1.3 | Define data models | `googler_api/models.py` | 1.1 |
| 1.4 | Define exceptions | `googler_api/exceptions.py` | 1.1 |
| 1.5 | Write unit tests for models | `tests/test_api/test_models.py` | 1.3, 1.4 |

**Validation Gate**: Import bridge successfully loads googler internals; models instantiate correctly.

### Phase 2: Core Client (Search Functionality)

| Step | Task | Files | Depends On |
|------|------|-------|------------|
| 2.1 | Implement URL builder wrapper | `googler_api/url_builder.py` | Phase 1 |
| 2.2 | Implement connection wrapper | `googler_api/connection.py` | Phase 1 |
| 2.3 | Implement GoogleSearchClient | `googler_api/client.py` | 2.1, 2.2 |
| 2.4 | Implement convenience functions | `googler_api/__init__.py` | 2.3 |
| 2.5 | Write integration tests | `tests/test_api/test_client.py` | 2.3 |

**Validation Gate**: `search("test query")` returns valid `SearchResult` objects.

### Phase 3: Advanced Features

| Step | Task | Files | Depends On |
|------|------|-------|------------|
| 3.1 | Pagination support | `client.py` (extend) | Phase 2 |
| 3.2 | News & video search | `client.py` (extend) | Phase 2 |
| 3.3 | Site filtering | `client.py` (extend) | Phase 2 |
| 3.4 | Date range filtering | `client.py` (extend) | Phase 2 |
| 3.5 | JSON output compatibility | `models.py`, `client.py` | Phase 2 |
| 3.6 | Write comprehensive tests | `tests/test_api/test_integration.py` | 3.1-3.5 |

**Validation Gate**: All search modes work; JSON output matches existing `--json` format.

### Phase 4: Packaging & Documentation

| Step | Task | Files | Depends On |
|------|------|-------|------------|
| 4.1 | Create pyproject.toml | `pyproject.toml` | Phase 3 |
| 4.2 | Update .gitignore | `.gitignore` | 4.1 |
| 4.3 | Write API README | `googler_api/README.md` | Phase 3 |
| 4.4 | Add type stubs if needed | `googler_api/py.typed` | Phase 3 |

---

## 4. Technical Decisions & Trade-offs

### 4.1 Wrapper vs. Fork

**Decision**: Wrapper pattern (import via `importlib.util`)

**Rationale**:
- Preserves the single-file `googler` executable untouched
- Upstream changes automatically flow to the API
- No code duplication
- No risk of breaking CLI behavior

**Trade-off**: Depends on internal class APIs which could change. Mitigated by the _compat bridge layer which centralizes all imports.

### 4.2 Dataclasses vs. Reusing Result

**Decision**: New `SearchResult` dataclass wrapping `Result`

**Rationale**:
- `Result` has class-level mutable state (`colors`, `urlexpand`) -- not API-safe
- `Result.print()` writes directly to stdout -- not API-appropriate
- Frozen dataclasses provide immutability and hashability
- Clean separation between CLI display and programmatic access

**Trade-off**: Minor duplication of field definitions. Mitigated by using `Result.jsonizable_object()` as the conversion bridge.

### 4.3 Connection Lifecycle

**Decision**: Context manager pattern with optional manual management

**Rationale**:
- `GoogleConnection` holds TCP/TLS state that must be cleaned up
- Context manager is idiomatic Python for resource management
- Convenience functions hide lifecycle completely for simple use cases

### 4.4 Thread Safety

**Decision**: Not thread-safe (single connection per client)

**Rationale**:
- Matches original googler behavior (single connection)
- Adding thread safety would require connection pooling (over-engineering)
- Users who need concurrency can create multiple clients

### 4.5 GoogleUrl opts.html_file Workaround

**Decision**: Provide `html_file=None` in synthetic namespace

**Rationale**:
- `GoogleUrl.__init__` line 1744 accesses `opts.html_file` unconditionally
- Setting it to `None` with falsy check passes the guard: `if opts.html_file and not opts.keywords`
- No modification to original code needed

---

## 5. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Google changes HTML format | Parser breaks | High (happens periodically) | Inherit googler's parser updates automatically via wrapper pattern |
| googler internal API changes | Import bridge breaks | Medium | Centralized `_compat.py` makes updates single-point |
| Rate limiting by Google | Searches fail | Medium | Expose error as `RateLimitError`; document usage best practices |
| Import side effects | Module-level code runs on import | Low | `importlib.util` gives control over module loading |
| Python version compatibility | API may use newer features | Low | Target same Python 3.8+ as googler; use only stdlib |

---

## 6. Testing Strategy

### 6.1 Unit Tests (Offline, No Network)
- Model creation and serialization
- Import bridge functionality
- URL builder parameter construction
- Config validation
- Exception hierarchy

### 6.2 Integration Tests (Network Required)
- Basic web search returns results
- News search returns metadata
- Video search returns YouTube results
- Site-specific filtering works
- Pagination (next/prev page)
- Date range filtering
- JSON output compatibility with existing `googler --json`
- Context manager properly cleans up connections

### 6.3 Compatibility Tests
- Output from `search_json()` matches `subprocess.run(["googler", "--json", ...])`
- All existing `test_googler.py` tests continue to pass (no regressions)

---

## 7. Usage Examples (End-to-End)

### Basic Search
```python
from googler_api import search

results = search("python dataclasses tutorial")
for r in results:
    print(f"{r.title}\n  {r.url}\n  {r.abstract}\n")
```

### News Monitoring Script
```python
from googler_api import GoogleSearchClient

with GoogleSearchClient(lang="en") as client:
    response = client.search_news("artificial intelligence")
    for result in response:
        print(f"[{result.metadata}] {result.title}")
        print(f"  {result.url}\n")
```

### Paginated Search
```python
from googler_api import GoogleSearchClient

with GoogleSearchClient() as client:
    response = client.search("machine learning papers", num=10)
    all_results = list(response.results)
    
    # Get pages 2 and 3
    for _ in range(2):
        response = client.next_page()
        all_results.extend(response.results)
    
    print(f"Collected {len(all_results)} results across 3 pages")
```

### JSON Export
```python
import json
from googler_api import GoogleSearchClient

with GoogleSearchClient() as client:
    response = client.search("python 3.12 features", num=5)
    
    # Compatible with existing googler --json format
    with open("results.json", "w") as f:
        f.write(response.to_json())
```

### Site-Specific Research
```python
from googler_api import search

# Search only academic sources
results = search(
    "transformer architecture attention",
    sites=["arxiv.org", "papers.nips.cc", "openreview.net"],
    num=20,
)

for r in results:
    print(f"{r.domain}: {r.title}")
```

---

## 8. File-by-File Implementation Specification

### `googler_api/__init__.py`
- Public API exports (`__all__`)
- Module-level `search()`, `search_news()`, `search_videos()` convenience functions
- Version string

### `googler_api/_compat.py`
- `importlib.util` based import of `googler` file
- Re-export of: `GoogleUrl`, `GoogleConnection`, `GoogleConnectionError`, `GoogleParser`, `Result`, `Sitelink`
- Error handling if googler file not found

### `googler_api/models.py`
- `SearchResult` (frozen dataclass)
- `SitelinkResult` (frozen dataclass)
- `SearchConfig` (dataclass)
- `ConnectionConfig` (dataclass)
- `SearchResponse` (dataclass with `__iter__`, `__len__`, `__getitem__`)
- Conversion functions: `_result_to_search_result(result: Result) -> SearchResult`

### `googler_api/url_builder.py`
- `URLBuilder` class wrapping `GoogleUrl`
- `_build_opts_namespace()` helper to create synthetic argparse namespace
- Clean interface: `build(query, config) -> GoogleUrl`

### `googler_api/connection.py`
- `ManagedConnection` class wrapping `GoogleConnection`
- Context manager protocol (`__enter__`/`__exit__`)
- Connection state management
- Retry logic (delegate to underlying `GoogleConnection.fetch_page`)

### `googler_api/client.py`
- `GoogleSearchClient` main class
- All search methods: `search()`, `search_news()`, `search_videos()`
- Pagination: `next_page()`, `prev_page()`
- JSON output: `search_json()`
- Context manager protocol

### `googler_api/exceptions.py`
- Exception hierarchy: `GooglerAPIError` -> `ConnectionError`, `SearchError`, `ParseError`, `RateLimitError`
- Exception wrapping for internal googler exceptions

### `pyproject.toml`
- Package metadata, Python version requirement (>=3.8)
- Optional test dependencies (pytest)
- No external runtime dependencies

---

## Appendix: googler Internal Class Reference

### GoogleUrl Key Parameters (from `update()` method)
- `duration`: str - Time filter (h5, d5, w5, m5, y5)
- `exact`: bool - Disable auto-spelling
- `keywords`: str/list - Search terms
- `lang`: str - Display language
- `geoloc`: str - Country code for geolocation
- `news`: bool - News search mode
- `videos`: bool - Video search mode
- `num`: int - Results per page
- `sites`: list - Site restriction
- `exclude`: list - Site exclusion
- `start`: int - Starting result offset
- `tld`: str - Top-level domain
- `unfilter`: bool - Show similar results
- `from`/`to`: str - Date range (MM/DD/YYYY)

### GoogleConnection Constructor
- `host`: str - Google hostname
- `port`: int - Port (default None)
- `address_family`: int - socket.AF_INET/AF_INET6 (default 0)
- `timeout`: int - Connection timeout (default 45)
- `proxy`: str - HTTP proxy spec
- `notweak`: bool - Disable TCP optimizations

### Result.jsonizable_object() Output Format
```json
{
    "title": "string",
    "url": "string",
    "abstract": "string",
    "metadata": "string or absent",
    "sitelinks": [{"title": "...", "url": "...", "abstract": "..."}],
    "matches": [{"phrase": "string", "offset": int}]
}
```

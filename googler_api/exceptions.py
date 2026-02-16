"""Exceptions for the googler API."""


class GooglerAPIError(Exception):
    """Base exception for all googler API errors."""

    pass


class ConnectionError(GooglerAPIError):
    """Network connection to Google failed."""

    pass


class SearchError(GooglerAPIError):
    """Search request failed."""

    pass


class ParseError(GooglerAPIError):
    """Failed to parse Google's HTML response."""

    pass


class RateLimitError(GooglerAPIError):
    """Google is rate-limiting requests (HTTP 429 or CAPTCHA)."""

    pass

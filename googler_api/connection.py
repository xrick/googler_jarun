"""Connection wrapper with context manager support."""

import socket
from typing import Optional

from googler_api._compat import GoogleConnection, GoogleConnectionError
from googler_api.exceptions import ConnectionError


class ManagedConnection:
    """Wrapper around GoogleConnection with context manager protocol.

    Parameters
    ----------
    host : str
        Google hostname to connect to.
    proxy : str, optional
        HTTP proxy specification.
    timeout : int
        Connection timeout in seconds. Default 45.
    ipv4_only : bool
        Force IPv4 connections.
    ipv6_only : bool
        Force IPv6 connections.
    notweak : bool
        Disable TCP optimizations and TLS 1.2 enforcement.
    """

    def __init__(
        self,
        host: str,
        *,
        proxy: Optional[str] = None,
        timeout: int = 45,
        ipv4_only: bool = False,
        ipv6_only: bool = False,
        notweak: bool = False,
    ):
        self._host = host
        self._proxy = proxy
        self._timeout = timeout
        self._notweak = notweak
        self._conn: Optional[GoogleConnection] = None

        if ipv4_only:
            self._address_family = socket.AF_INET
        elif ipv6_only:
            self._address_family = socket.AF_INET6
        else:
            self._address_family = 0

    def connect(self):
        """Establish connection to the host.

        Raises
        ------
        ConnectionError
            If connection fails.
        """
        if self._conn is not None:
            return

        try:
            self._conn = GoogleConnection(
                self._host,
                address_family=self._address_family,
                timeout=self._timeout,
                proxy=self._proxy,
                notweak=self._notweak,
            )
        except GoogleConnectionError as e:
            raise ConnectionError(str(e)) from e

    def fetch_page(self, url: str) -> str:
        """Fetch a URL relative to the connected host.

        Parameters
        ----------
        url : str
            Relative URL path (e.g., '/search?q=python').

        Returns
        -------
        str
            The response body (HTML).

        Raises
        ------
        ConnectionError
            If the fetch fails.
        """
        if self._conn is None:
            self.connect()

        try:
            return self._conn.fetch_page(url)
        except GoogleConnectionError as e:
            raise ConnectionError(str(e)) from e

    def reconnect(self, host: Optional[str] = None):
        """Close current connection and establish a new one.

        Parameters
        ----------
        host : str, optional
            New host to connect to. Reuses current host if None.
        """
        try:
            if self._conn is not None:
                self._conn.new_connection(host, timeout=self._timeout)
                if host:
                    self._host = host
        except GoogleConnectionError as e:
            raise ConnectionError(str(e)) from e

    def close(self):
        """Close the connection if active."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def host(self) -> str:
        """The current host."""
        return self._host

    @property
    def is_connected(self) -> bool:
        """Whether a connection is currently active."""
        return self._conn is not None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()
        return False

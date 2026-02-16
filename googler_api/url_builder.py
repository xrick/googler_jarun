"""URL builder wrapper around googler's GoogleUrl."""

import socket
from types import SimpleNamespace
from typing import List, Optional

from googler_api._compat import GoogleUrl


def _build_opts_namespace(
    keywords,
    *,
    num: int = 10,
    start: int = 0,
    lang: Optional[str] = None,
    geoloc: Optional[str] = None,
    tld: Optional[str] = None,
    exact: bool = False,
    duration: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sites: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    unfilter: bool = False,
    news: bool = False,
    videos: bool = False,
) -> SimpleNamespace:
    """Build a synthetic argparse.Namespace for GoogleUrl.

    GoogleUrl.__init__ expects an opts object with specific attributes.
    This function creates a compatible namespace from keyword arguments.
    """
    if isinstance(keywords, str):
        keywords = keywords.split()

    opts = SimpleNamespace(
        keywords=keywords,
        num=num,
        start=start,
        lang=lang,
        geoloc=geoloc,
        tld=tld,
        exact=exact,
        duration=duration,
        sites=sites,
        exclude=exclude,
        unfilter=unfilter,
        news=news,
        videos=videos,
        html_file=None,  # Required: GoogleUrl checks this attribute
    )

    # GoogleUrl.update() looks for 'from' and 'to' via opts dict
    if date_from is not None:
        setattr(opts, "from", date_from)
    if date_to is not None:
        setattr(opts, "to", date_to)

    return opts


def build_url(keywords, **kwargs) -> GoogleUrl:
    """Build a GoogleUrl from keyword arguments.

    Parameters
    ----------
    keywords : str or list of str
        Search keywords.
    **kwargs
        See ``_build_opts_namespace`` for supported parameters.

    Returns
    -------
    GoogleUrl
        A configured GoogleUrl instance ready for fetching.
    """
    opts = _build_opts_namespace(keywords, **kwargs)
    return GoogleUrl(opts)

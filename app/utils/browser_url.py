"""Scheme allowlist for browser navigation URLs."""

from __future__ import annotations

from urllib.parse import urlparse


def assert_browser_http_url(url: str) -> str:
    """Require http(s) with a host before Playwright navigate / new tab.

    Rejects ``file:``, ``javascript:``, and other non-http schemes that would
    let an agent-controlled URL escape the intended web navigation surface.
    """
    if not url or not str(url).strip():
        raise ValueError("URL must be an http(s) URL with a host")
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("URL must be an http(s) URL with a host")
    return url.strip()

"""SSRF helpers for outbound fetches of untrusted URLs."""

from __future__ import annotations

import ipaddress
import socket
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests


def _ip_is_blocked(ip_str: str) -> bool:
    """Whether an address is not a public unicast destination."""
    try:
        addr = ipaddress.ip_address(ip_str.split("%", maxsplit=1)[0])
    except ValueError:
        return True
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def fetch_url_validation_error(url: str) -> Optional[str]:
    """Return an error string if a fetch URL is not safe.

    Blocks non-HTTP(S) schemes and hosts that resolve to loopback,
    link-local, private, reserved, multicast, or unspecified addresses
    (e.g. 169.254.169.254). Fail closed when DNS resolution fails.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return "unparseable URL"
    if parsed.scheme not in ("http", "https"):
        return f"scheme '{parsed.scheme}' is not http/https"
    host = parsed.hostname
    if not host:
        return "no hostname"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return f"DNS resolution failed: {exc}"
    if not infos:
        return "DNS resolution returned no addresses"
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        if _ip_is_blocked(sockaddr[0]):
            return f"host resolves to blocked address {sockaddr[0]}"
    return None


def safe_get(
    url: str,
    *,
    headers: Optional[dict] = None,
    timeout: float = 10,
    max_redirects: int = 5,
) -> requests.Response:
    """GET with SSRF checks on the initial URL and every redirect hop."""
    current = url
    for _ in range(max_redirects + 1):
        err = fetch_url_validation_error(current)
        if err:
            raise ValueError(f"blocked fetch URL ({err}): {current}")
        response = requests.get(
            current,
            headers=headers,
            timeout=timeout,
            allow_redirects=False,
        )
        if 300 <= response.status_code < 400:
            location = response.headers.get("Location")
            if not location:
                return response
            current = urljoin(current, location)
            continue
        return response
    raise ValueError(f"too many redirects fetching {url}")

"""Unit tests for SSRF URL validation used by WebContentFetcher."""

from unittest.mock import patch

import pytest

from app.utils.url_safety import fetch_url_validation_error, safe_get


def test_rejects_loopback_literal():
    assert fetch_url_validation_error("http://127.0.0.1/") is not None
    assert fetch_url_validation_error("http://[::1]/") is not None


def test_rejects_link_local_metadata():
    assert fetch_url_validation_error("http://169.254.169.254/latest/meta-data/") is not None


def test_rejects_non_http_scheme():
    err = fetch_url_validation_error("ftp://example.com/file")
    assert err is not None
    assert "scheme" in err


def test_rejects_empty_host():
    assert fetch_url_validation_error("http:///path") is not None


def test_allows_public_literal():
    # 1.1.1.1 is public anycast; no DNS needed.
    assert fetch_url_validation_error("https://1.1.1.1/") is None


def test_safe_get_revalidates_redirect_to_loopback():
    class FakeResp:
        def __init__(self, status_code, location=None):
            self.status_code = status_code
            self.headers = {"Location": location} if location else {}

    calls = []

    def fake_get(url, headers=None, timeout=None, allow_redirects=None):
        calls.append(url)
        if url.startswith("http://example.com"):
            return FakeResp(302, "http://127.0.0.1/secret")
        return FakeResp(200)

    with patch("app.utils.url_safety.requests.get", side_effect=fake_get):
        with patch(
            "app.utils.url_safety.fetch_url_validation_error",
            side_effect=lambda u: (
                "blocked" if "127.0.0.1" in u else None
            ),
        ):
            with pytest.raises(ValueError, match="blocked"):
                safe_get("http://example.com/page")

    assert calls == ["http://example.com/page"]

"""Crawl4aiTool rejects private/loopback URLs before crawler.arun (SSRF).

Mirrors Crawl4aiTool._is_valid_url which delegates to fetch_url_validation_error.
"""

from pathlib import Path

from app.utils.url_safety import fetch_url_validation_error


def _is_valid_url(url: str) -> bool:
    return fetch_url_validation_error(url) is None


def test_crawl4ai_rejects_loopback_and_metadata():
    assert _is_valid_url("http://127.0.0.1/") is False
    assert _is_valid_url("http://[::1]/") is False
    assert _is_valid_url("http://169.254.169.254/latest/meta-data/") is False
    assert _is_valid_url("http://192.168.1.1/") is False


def test_crawl4ai_allows_public_literal():
    assert _is_valid_url("https://1.1.1.1/") is True


def test_crawl4ai_rejects_non_http_scheme():
    assert _is_valid_url("ftp://example.com/file") is False
    assert _is_valid_url("javascript:alert(1)") is False


def test_crawl4ai_tool_wires_fetch_url_validation_error():
    src = Path("app/tool/crawl4ai.py").read_text(encoding="utf-8")
    assert "from app.utils.url_safety import fetch_url_validation_error" in src
    assert "return fetch_url_validation_error(url) is None" in src

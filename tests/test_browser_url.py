"""Tests for browser navigation URL scheme allowlist."""

import unittest

from app.utils.browser_url import assert_browser_http_url


class TestAssertBrowserHttpUrl(unittest.TestCase):
    def test_allows_http_https(self):
        self.assertEqual(
            assert_browser_http_url("https://example.com/path"),
            "https://example.com/path",
        )
        self.assertEqual(
            assert_browser_http_url("http://127.0.0.1:8080/"),
            "http://127.0.0.1:8080/",
        )

    def test_rejects_non_http_schemes(self):
        with self.assertRaisesRegex(ValueError, r"http\(s\)"):
            assert_browser_http_url("file:///etc/passwd")
        with self.assertRaisesRegex(ValueError, r"http\(s\)"):
            assert_browser_http_url("javascript:alert(1)")
        with self.assertRaisesRegex(ValueError, r"http\(s\)"):
            assert_browser_http_url("not a url")


if __name__ == "__main__":
    unittest.main()

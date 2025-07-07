import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests
import app.scraper as scraper

class DummyResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error")


def test_fetch_html_success(monkeypatch):
    def fake_get(url, headers=None, timeout=10):
        return DummyResponse('<html><body><p>Hello</p></body></html>')
    monkeypatch.setattr(requests, "get", fake_get)
    html = scraper.fetch_html("http://example.com")
    assert "Hello" in html


def test_fetch_html_failure(monkeypatch):
    def fake_get(url, headers=None, timeout=10):
        raise requests.RequestException("boom")
    monkeypatch.setattr(requests, "get", fake_get)
    html = scraper.fetch_html("http://bad.com", retries=1)
    assert html is None


def test_scrape_content(monkeypatch):
    def fake_get(url, headers=None, timeout=10):
        return DummyResponse('<html><body><p>Hello</p></body></html>')
    monkeypatch.setattr(requests, "get", fake_get)
    result = scraper.scrape_content("http://example.com")
    assert result["text_content"].strip() == "Hello"

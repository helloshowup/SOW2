import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("OPENAI_API_KEY", "test")
from app import scraper


def test_generate_search_terms():
    keywords = ['pizza', 'culture', 'engagement']
    terms = scraper.generate_search_terms(keywords, max_terms=2)
    assert len(terms) == 2
    for term in terms:
        assert term.endswith(' news')
        assert term[:-5] in keywords


def test_load_brand_keywords():
    keywords = scraper.load_brand_keywords('debonairs', 'dev-research/debonair_brand.yaml')
    assert 'pizza' in keywords
    assert 'interactive' in keywords


import asyncio


@pytest.mark.asyncio
async def test_simple_scraper_search_and_crawl(monkeypatch):
    class Dummy:
        def __init__(self, url, title, description):
            self.url = url
            self.title = title
            self.description = description

    def fake_search(term, num_results=10, advanced=False, **kwargs):
        assert term == 'test'
        return [
            Dummy('http://example.com/1', 'T1', 'Hello'),
            Dummy('http://example.com/2', 'T2', 'World'),
        ]

    monkeypatch.setattr(scraper, 'google_search', fake_search)
    async def fake_is_url_visited(self, session, url):
        return False
    monkeypatch.setattr(scraper.SimpleScraper, '_is_url_visited', fake_is_url_visited)

    s = scraper.SimpleScraper()

    results = await s.search(None, 'test', max_results=2)
    assert results == [
        {
            'url': 'http://example.com/1',
            'snippet': 'Hello',
            'source_title': 'T1',
            'publication_time': None,
        },
        {
            'url': 'http://example.com/2',
            'snippet': 'World',
            'source_title': 'T2',
            'publication_time': None,
        },
    ]

    pages = await s.crawl(None, ['test'], max_results=2)
    assert pages == results


@pytest.mark.asyncio
async def test_simple_scraper_skips_invalid_results(monkeypatch):
    class Dummy:
        def __init__(self, url, title, description):
            self.url = url
            self.title = title
            self.description = description

    def fake_search(term, num_results=10, advanced=False, **kwargs):
        return [
            Dummy('', 'T1', 'desc'),
            Dummy('http://valid.com', 'T2', None),
            Dummy('http://ok.com', 'T3', 'ok'),
        ]

    monkeypatch.setattr(scraper, 'google_search', fake_search)
    async def fake_is_url_visited(self, session, url):
        return False
    monkeypatch.setattr(scraper.SimpleScraper, '_is_url_visited', fake_is_url_visited)

    s = scraper.SimpleScraper()
    results = await s.search(None, 'whatever', max_results=3)
    assert results == [
        {
            'url': 'http://ok.com',
            'snippet': 'ok',
            'source_title': 'T3',
            'publication_time': None,
        }
    ]


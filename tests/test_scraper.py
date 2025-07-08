import pytest

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


def test_simple_scraper_search_and_scrape(monkeypatch):
    sample_search_html = (
        '<a class="result__a" href="http://example.com/1">One</a>'
        '<a class="result__a" href="http://example.com/2">Two</a>'
    )
    sample_page_html = '<p>Hello</p><p>World</p>'

    s = scraper.SimpleScraper()

    def fake_get(url):
        if 'duckduckgo' in url:
            return sample_search_html
        return sample_page_html

    monkeypatch.setattr(s, '_get', lambda url: fake_get(url))

    links = s.search('test', max_results=2)
    assert links == ['http://example.com/1', 'http://example.com/2']

    text = s.scrape_page('http://example.com/1')
    assert text == 'Hello\nWorld'


def test_simple_scraper_redirect_resolution(monkeypatch):
    html = '<a class="result__a" href="/l/?uddg=http%3A%2F%2Fexample.com">Link</a>'
    s = scraper.SimpleScraper()

    monkeypatch.setattr(s, '_get', lambda url: html)

    links = s.search('test', max_results=1)
    assert links == ['http://example.com']

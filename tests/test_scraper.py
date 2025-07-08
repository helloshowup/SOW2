import pytest
import asyncio
from sqlmodel import SQLModel, Session, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.pool import StaticPool

from app import scraper, database
from app.models import VisitedUrl


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


def test_crawl_records_and_skips(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async_session_local = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    asyncio.run(init_models())

    database.engine = engine
    database.async_session = async_session_local
    scraper.engine = engine

    s = scraper.SimpleScraper()

    monkeypatch.setattr(s, "search", lambda term, max_results=5: ["http://example.com"])
    monkeypatch.setattr(s, "scrape_page", lambda url: "hi")

    pages = s.crawl(["test"], max_results=1)
    assert pages == [{"url": "http://example.com", "text": "hi"}]

    pages2 = s.crawl(["test"], max_results=1)
    assert pages2 == []

    with Session(engine.sync_engine) as session:
        rows = session.exec(select(VisitedUrl)).all()
        assert len(rows) == 1
        assert rows[0].domain == "example.com"

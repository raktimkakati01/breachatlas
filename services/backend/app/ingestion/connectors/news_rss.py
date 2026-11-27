"""News RSS discovery connector — security-news feeds, used ONLY to create leads.

Feeds are configured per deployment (NEWS_RSS_FEEDS) after each feed's ToU is checked; the list is
empty by default. XML is parsed with defusedxml to block XXE / billion-laughs attacks, since feed
content is untrusted.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from defusedxml.ElementTree import fromstring

from app.core.config import settings
from app.ingestion.connectors.base import Fetch
from app.ingestion.extractor import Extractor, NewsRssExtractor

_ATOM = "{http://www.w3.org/2005/Atom}"


def _text(element, tag: str) -> str:
    child = element.find(tag) if element is not None else None
    return child.text.strip() if child is not None and child.text else ""


def _parse_feed(data: bytes, default_source: str) -> list[dict]:
    root = fromstring(data)  # defused: external entities / entity expansion are rejected
    channel = root.find("channel")
    source = _text(channel, "title") or default_source

    items: list[dict] = []
    for item in root.iter("item"):  # RSS 2.0
        items.append(
            {
                "title": _text(item, "title"),
                "link": _text(item, "link"),
                "published": _text(item, "pubDate"),
                "summary": _text(item, "description"),
                "source": source,
            }
        )
    if items:
        return items

    for entry in root.iter(f"{_ATOM}entry"):  # Atom fallback
        link_el = entry.find(f"{_ATOM}link")
        items.append(
            {
                "title": _text(entry, f"{_ATOM}title"),
                "link": link_el.get("href", "") if link_el is not None else "",
                "published": _text(entry, f"{_ATOM}updated") or _text(entry, f"{_ATOM}published"),
                "summary": _text(entry, f"{_ATOM}summary"),
                "source": source,
            }
        )
    return items


class NewsRssConnector:
    name = "news_rss"

    def __init__(self, feeds: list[str] | None = None, extractor: Extractor | None = None) -> None:
        self.feeds = feeds if feeds is not None else settings.news_rss_feeds
        self.extractor = extractor or NewsRssExtractor()

    def discover(self, fetch: Fetch) -> list[dict]:
        records: list[dict] = []
        for url in self.feeds:
            records.extend(_parse_feed(fetch(url), urlsplit(url).netloc or url))
        return records

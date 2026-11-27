"""UK ICO enforcement connector.

The ICO publishes enforcement actions (monetary penalties, enforcement notices, reprimands) as
an HTML list. robots.txt permits /action-weve-taken/enforcement/ with a 6s crawl-delay. We parse
the list into entries; CSS selectors may need tuning if the ICO markup changes (see decisions.md).
Built/tested against fixtures.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from app.ingestion.connectors.base import Fetch
from app.ingestion.extractor import Extractor, IcoExtractor

ICO_URL = "https://ico.org.uk/action-weve-taken/enforcement/"


class IcoConnector:
    name = "uk_ico"

    def __init__(self, extractor: Extractor | None = None) -> None:
        self.extractor = extractor or IcoExtractor()

    def discover(self, fetch: Fetch) -> list[dict]:
        html = fetch(ICO_URL).decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")

        entries: list[dict] = []
        for article in soup.select("article.action"):
            title = article.select_one("h2 a") or article.select_one("h2")
            date_el = article.select_one(".date")
            type_el = article.select_one(".type")
            entries.append(
                {
                    "organization": title.get_text(strip=True) if title else "",
                    "date": date_el.get_text(strip=True) if date_el else "",
                    "type": type_el.get_text(strip=True) if type_el else "",
                    "url": title.get("href", "") if title and title.has_attr("href") else "",
                }
            )
        return entries

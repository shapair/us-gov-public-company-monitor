"""Fetchers for federal direct equity stake / bailout signals.

Sources:
- U.S. Department of the Treasury press releases (RSS)
- Federal Reserve press releases (RSS)
- SEC EDGAR full-text search (EFTS) for filings mentioning equity/warrant/bailout terms
"""
import logging
import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Optional
from xml.etree import ElementTree as ET

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TREASURY_RSS_URL = "https://home.treasury.gov/rss.xml"
FED_RSS_URL = "https://www.federalreserve.gov/feeds/press_all.xml"
SEC_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"

DEFAULT_HEADERS = {
    "User-Agent": settings.sec_user_agent,
    "Accept": "application/rss+xml, application/xml, text/xml, application/json",
}

# Force IPv4 in environments where IPv6 routes are missing.
_HTTP_TRANSPORT = httpx.HTTPTransport(local_address="0.0.0.0")

STAKE_KEYWORDS = [
    "equity stake",
    "equity investment",
    "preferred stock",
    "common stock purchase",
    "purchase agreement",
    "direct investment",
    "warrant",
    "bailout",
    "TARP",
    "Troubled Asset Relief",
    "rescue package",
    "government assistance",
    "federal assistance",
    "bridge loan",
    "direct loan",
]

EDGAR_STAKE_QUERIES = [
    '"equity stake"',
    '"preferred stock"',
    '"common stock purchase"',
    '"purchase agreement"',
    "warrant",
    "bailout",
    '"direct investment"',
]


def _parse_rss_date(value: str | None) -> Optional[date]:
    if not value:
        return None
    value = str(value).strip()
    # Common RSS date formats: RFC 2822 and ISO-like
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def _keyword_matches(text: str) -> list[str]:
    text_lower = text.lower()
    return [kw for kw in STAKE_KEYWORDS if kw.lower() in text_lower]


def _contains_stake_keyword(text: str) -> bool:
    return bool(_keyword_matches(text))


def fetch_treasury_rss(start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
    """Fetch Treasury RSS feed and return items that look like stake announcements."""
    end_date = end_date or date.today()
    start_date = start_date or end_date - timedelta(days=30)

    logger.info("Fetching Treasury RSS: %s", TREASURY_RSS_URL)
    with httpx.Client(
        headers=DEFAULT_HEADERS, timeout=30, transport=_HTTP_TRANSPORT
    ) as client:
        resp = client.get(TREASURY_RSS_URL)
        resp.raise_for_status()
        xml_text = resp.text

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.warning("Failed to parse Treasury RSS: %s", e)
        return []

    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title", default="") or "").strip()
        link = (item.findtext("link", default="") or "").strip()
        description = (item.findtext("description", default="") or "").strip()
        pub_date = item.findtext("pubDate", default="") or ""
        content_encoded = item.find("content:encoded", ns)
        content = (content_encoded.text or "") if content_encoded is not None else ""

        clean_text = _strip_html(" ".join([title, description, content]))
        item_date = _parse_rss_date(pub_date)
        if item_date and (item_date < start_date or item_date > end_date):
            continue
        if not _contains_stake_keyword(clean_text):
            continue

        items.append(
            {
                "agency": "treasury",
                "title": title,
                "url": link,
                "published_at": item_date.isoformat() if item_date else None,
                "text": clean_text,
                "matched_keywords": _keyword_matches(clean_text),
                "source_id": link,
            }
        )

    logger.info("Treasury RSS returned %s stake-related items", len(items))
    return items


def fetch_fed_rss(start_date: date | None = None, end_date: date | None = None) -> list[dict[str, Any]]:
    """Fetch Federal Reserve RSS feed and return items that look like stake announcements."""
    end_date = end_date or date.today()
    start_date = start_date or end_date - timedelta(days=30)

    logger.info("Fetching Fed RSS: %s", FED_RSS_URL)
    with httpx.Client(
        headers=DEFAULT_HEADERS, timeout=30, transport=_HTTP_TRANSPORT
    ) as client:
        resp = client.get(FED_RSS_URL)
        resp.raise_for_status()
        xml_text = resp.text

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.warning("Failed to parse Fed RSS: %s", e)
        return []

    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title", default="") or "").strip()
        link = (item.findtext("link", default="") or "").strip()
        description = (item.findtext("description", default="") or "").strip()
        pub_date = item.findtext("pubDate", default="") or ""

        clean_text = _strip_html(" ".join([title, description]))
        item_date = _parse_rss_date(pub_date)
        if item_date and (item_date < start_date or item_date > end_date):
            continue
        if not _contains_stake_keyword(clean_text):
            continue

        items.append(
            {
                "agency": "fed",
                "title": title,
                "url": link,
                "published_at": item_date.isoformat() if item_date else None,
                "text": clean_text,
                "matched_keywords": _keyword_matches(clean_text),
                "source_id": link,
            }
        )

    logger.info("Fed RSS returned %s stake-related items", len(items))
    return items


def _sec_filing_url(hit_id: str, cik: str) -> str:
    """Build a direct SEC filing URL from an EFTS hit id."""
    # hit_id format: "0001213900-20-012347:ea121805ex4-11_protara.htm"
    accession, filename = hit_id.split(":", 1)
    accession_no_dash = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dash}/{filename}"


def _extract_ticker_from_display_name(display_name: str) -> Optional[str]:
    m = re.search(r"\(([A-Z]{1,5})\)", display_name)
    return m.group(1) if m else None


def search_sec_edgar_stakes(
    start_date: date | None = None,
    end_date: date | None = None,
    max_results_per_query: int = 50,
) -> list[dict[str, Any]]:
    """Search SEC EDGAR full-text index for stake-related 8-K / 8-K/A filings."""
    end_date = end_date or date.today()
    start_date = start_date or end_date - timedelta(days=30)

    all_hits: list[dict[str, Any]] = []
    with httpx.Client(
        headers=DEFAULT_HEADERS, timeout=60, transport=_HTTP_TRANSPORT
    ) as client:
        for query in EDGAR_STAKE_QUERIES:
            params = {
                "q": query,
                "forms": "8-K,8-K/A",
                "dateRange": "custom",
                "startdt": start_date.isoformat(),
                "enddt": end_date.isoformat(),
                "size": min(max_results_per_query, 100),
            }
            logger.info("Searching SEC EFTS: q=%r", query)
            try:
                resp = client.get(SEC_EFTS_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.warning("SEC EFTS query failed for %r: %s", query, e)
                continue

            hits = data.get("hits", {}).get("hits", [])
            for hit in hits:
                src = hit.get("_source", {})
                ciks = src.get("ciks", []) or []
                cik = ciks[0] if ciks else None
                display_names = src.get("display_names", []) or []
                display_name = display_names[0] if display_names else ""
                ticker = _extract_ticker_from_display_name(display_name)
                file_date = src.get("file_date")
                form = src.get("form")
                description = src.get("file_description") or ""
                hit_id = hit.get("_id", "")
                filing_url = _sec_filing_url(hit_id, cik) if cik and hit_id else None

                all_hits.append(
                    {
                        "agency": "sec_edgar",
                        "title": f"{form}: {description}".strip(": "),
                        "url": filing_url,
                        "published_at": file_date,
                        "text": " ".join([display_name, description]),
                        "matched_keywords": [query.strip('"')],
                        "source_id": hit_id,
                        "cik": cik,
                        "ticker": ticker,
                        "form": form,
                        "filing_date": file_date,
                    }
                )

            # Respect SEC rate limit: 10 req/sec
            time.sleep(0.15)

    logger.info("SEC EDGAR returned %s stake-related hits", len(all_hits))
    return all_hits


def fetch_equity_stakes(
    start_date: date | None = None,
    end_date: date | None = None,
    max_edgar_results: int = 50,
) -> list[dict[str, Any]]:
    """Aggregate stake signals from all configured sources."""
    results: list[dict[str, Any]] = []
    results.extend(fetch_treasury_rss(start_date, end_date))
    results.extend(fetch_fed_rss(start_date, end_date))
    results.extend(search_sec_edgar_stakes(start_date, end_date, max_edgar_results))
    return results

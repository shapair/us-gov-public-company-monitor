"""Fetchers for foreign-government-linked SEC 13F/13D/13G filings.

Data sources:
- SEC EDGAR submissions JSON for known sovereign filer CIKs (primary)
- SEC EDGAR full-text search (EFTS) for discovery of new government-linked filers (secondary)
"""
import logging
import time
from datetime import date, timedelta
from typing import Any, Optional
from xml.etree import ElementTree as ET

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
SEC_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"

DEFAULT_HEADERS = {
    "User-Agent": settings.sec_user_agent,
    "Accept": "application/json",
}

# Force IPv4 in environments where IPv6 routes are missing.
_HTTP_TRANSPORT = httpx.HTTPTransport(local_address="0.0.0.0")

FOREIGN_HOLDING_FORMS = {"13F-HR", "13F-HR/A", "13D", "13D/A", "13G", "13G/A", "SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A"}

# Broad aliases used for EFTS discovery only.
SOVEREIGN_KEYWORDS = [
    "NORGES BANK",
    "CHINA INVESTMENT",
    "GIC PRIVATE",
    "TEMASEK",
    "ABU DHABI INVESTMENT",
    "KUWAIT INVESTMENT",
    "QATAR INVESTMENT",
    "SAUDI ARABIAN",
    "PUBLIC INVESTMENT FUND",
    "GOVERNMENT OF SINGAPORE",
    "CENTRAL BANK",
    "SOVEREIGN WEALTH",
]


def _cik_str(cik: str | int) -> str:
    """Return CIK as zero-padded 10-digit string."""
    return str(cik).lstrip("0").zfill(10)


def _accession_no_dash(accession: str) -> str:
    return accession.replace("-", "")


def _parse_iso_date(value: str | None) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def fetch_submissions_for_cik(
    cik: str | int,
    start_date: date | None = None,
    end_date: date | None = None,
    max_recent: int = 200,
) -> list[dict[str, Any]]:
    """Fetch recent SEC submissions for a CIK and return 13F/13D/13G filings."""
    end_date = end_date or date.today()
    start_date = start_date or end_date - timedelta(days=365)

    cik_padded = _cik_str(cik)
    url = f"{SEC_SUBMISSIONS_URL}/CIK{cik_padded}.json"
    logger.info("Fetching SEC submissions for CIK %s", cik_padded)

    with httpx.Client(headers=DEFAULT_HEADERS, timeout=30, transport=_HTTP_TRANSPORT) as client:
        resp = client.get(url)
        resp.raise_for_status()
        time.sleep(0.15)
        data = resp.json()

    entity_name = data.get("name") or data.get("entityName", "")
    filings = data.get("filings", {}).get("recent", {})
    keys = [
        "accessionNumber",
        "filingDate",
        "reportDate",
        "form",
        "primaryDocument",
        "primaryDocDescription",
    ]
    arrays = {k: filings.get(k, []) for k in keys}
    length = len(arrays["accessionNumber"])

    results: list[dict[str, Any]] = []
    for i in range(min(length, max_recent)):
        form = arrays["form"][i]
        if form not in FOREIGN_HOLDING_FORMS:
            continue
        filing_date = _parse_iso_date(arrays["filingDate"][i])
        if filing_date and (filing_date < start_date or filing_date > end_date):
            continue
        results.append(
            {
                "cik": cik_padded,
                "entity_name": entity_name,
                "accession_number": arrays["accessionNumber"][i],
                "filing_date": arrays["filingDate"][i],
                "report_date": arrays["reportDate"][i],
                "form": form,
                "primary_document": arrays["primaryDocument"][i],
                "primary_doc_description": arrays["primaryDocDescription"][i],
            }
        )

    logger.info("Found %s relevant filings for CIK %s", len(results), cik_padded)
    return results


def fetch_filing_index(cik: str | int, accession_number: str) -> list[dict[str, Any]]:
    """Return the directory listing for a filing."""
    cik_padded = _cik_str(cik)
    acc_no_dash = _accession_no_dash(accession_number)
    url = f"{SEC_ARCHIVES_URL}/{int(cik_padded)}/{acc_no_dash}/index.json"

    with httpx.Client(headers=DEFAULT_HEADERS, timeout=30, transport=_HTTP_TRANSPORT) as client:
        try:
            resp = client.get(url)
            resp.raise_for_status()
            time.sleep(0.15)
            return resp.json().get("directory", {}).get("item", [])
        except Exception as e:
            logger.warning("Failed to fetch filing index %s: %s", url, e)
            return []


def fetch_13f_info_table(cik: str | int, accession_number: str) -> str | None:
    """Download the 13F information table XML if available."""
    items = fetch_filing_index(cik, accession_number)
    candidates = [
        item
        for item in items
        if item.get("name", "").lower().endswith(".xml")
        and "infotable" in item.get("name", "").lower()
    ]
    if not candidates:
        # Fallback: any XML that is not the primary doc.
        candidates = [
            item
            for item in items
            if item.get("name", "").lower().endswith(".xml")
        ]
    if not candidates:
        return None

    cik_padded = _cik_str(cik)
    acc_no_dash = _accession_no_dash(accession_number)
    filename = candidates[0]["name"]
    url = f"{SEC_ARCHIVES_URL}/{int(cik_padded)}/{acc_no_dash}/{filename}"

    with httpx.Client(headers=DEFAULT_HEADERS, timeout=60, transport=_HTTP_TRANSPORT) as client:
        try:
            resp = client.get(url)
            resp.raise_for_status()
            time.sleep(0.15)
            return resp.text
        except Exception as e:
            logger.warning("Failed to fetch 13F info table %s: %s", url, e)
            return None


def fetch_primary_document(cik: str | int, accession_number: str, primary_document: str) -> str | None:
    """Download the primary document of a filing (used for 13D/13G)."""
    if not primary_document:
        return None
    cik_padded = _cik_str(cik)
    acc_no_dash = _accession_no_dash(accession_number)
    url = f"{SEC_ARCHIVES_URL}/{int(cik_padded)}/{acc_no_dash}/{primary_document}"

    with httpx.Client(headers=DEFAULT_HEADERS, timeout=60, transport=_HTTP_TRANSPORT) as client:
        try:
            resp = client.get(url)
            resp.raise_for_status()
            time.sleep(0.15)
            return resp.text
        except Exception as e:
            logger.warning("Failed to fetch primary document %s: %s", url, e)
            return None


def _sec_filing_url(hit_id: str, cik: str) -> str | None:
    """Build a direct SEC filing URL from an EFTS hit id."""
    if not hit_id or ":" not in hit_id:
        return None
    accession, filename = hit_id.split(":", 1)
    accession_no_dash = accession.replace("-", "")
    return f"{SEC_ARCHIVES_URL}/{int(cik)}/{accession_no_dash}/{filename}"


def search_sec_edgar_foreign_holdings(
    start_date: date | None = None,
    end_date: date | None = None,
    max_results_per_query: int = 25,
) -> list[dict[str, Any]]:
    """Use SEC EFTS to discover 13F/13D/13G filings mentioning sovereign entities."""
    end_date = end_date or date.today()
    start_date = start_date or end_date - timedelta(days=90)

    all_hits: list[dict[str, Any]] = []
    seen = set()
    with httpx.Client(headers=DEFAULT_HEADERS, timeout=60, transport=_HTTP_TRANSPORT) as client:
        for query in SOVEREIGN_KEYWORDS:
            params = {
                "q": query,
                "forms": "13F-HR,13F-HR/A,13D,13D/A,13G,13G/A",
                "dateRange": "custom",
                "startdt": start_date.isoformat(),
                "enddt": end_date.isoformat(),
                "size": min(max_results_per_query, 100),
            }
            logger.info("Searching SEC EFTS for foreign holdings: q=%r", query)
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
                if not cik:
                    continue
                display_names = src.get("display_names", []) or []
                display_name = display_names[0] if display_names else ""
                file_date = src.get("file_date")
                form = src.get("form")
                description = src.get("file_description") or ""
                hit_id = hit.get("_id", "")
                key = (cik, hit_id)
                if key in seen:
                    continue
                seen.add(key)
                filing_url = _sec_filing_url(hit_id, cik)
                all_hits.append(
                    {
                        "cik": cik,
                        "filer_name": display_name,
                        "form": form,
                        "filing_date": file_date,
                        "description": description,
                        "source_id": hit_id,
                        "url": filing_url,
                    }
                )

            time.sleep(0.15)

    logger.info("SEC EFTS foreign-holdings discovery returned %s hits", len(all_hits))
    return all_hits

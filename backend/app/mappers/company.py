"""Company identifier/name to ticker mapping utilities."""
import re
from sqlmodel import Session, select

from app.database import engine
from app.models import CompanyMapping


# Common corporate suffixes and noise words to strip when normalizing names.
SUFFIX_RE = re.compile(
    r"\b(inc\.?|incorporated|corp\.?|corporation|company|co\.?|llc|lp|l\.p\.?|"
    r"ltd\.?|limited|plc|holdings?|group|corp\s*/\s*[a-z]{2}/?|/\s*(de|md|ny|ca|tx)\s*/?)\b",
    re.IGNORECASE,
)


def normalize_name(name: str) -> str:
    """Strip suffixes, punctuation, and extra whitespace from a company name.

    This makes substring matching more forgiving between sources like
    USASpending ("MICROSOFT CORPORATION") and SEC ("MICROSOFT CORP").
    """
    if not name:
        return ""

    # Uppercase and remove common suffixes.
    cleaned = name.upper().strip()
    cleaned = SUFFIX_RE.sub(" ", cleaned)

    # Remove punctuation and extra whitespace.
    cleaned = re.sub(r"[^A-Z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned


def lookup_ticker(name: str) -> str | None:
    """Attempt to map a company name to a ticker using the mapping table."""
    if not name:
        return None

    name_lower = name.lower().strip()
    name_norm = normalize_name(name)

    with Session(engine) as session:
        # Exact canonical name match (case-insensitive).
        mapping = session.exec(
            select(CompanyMapping).where(
                CompanyMapping.canonical_name.ilike(name_lower)
            )
        ).first()
        if mapping and mapping.ticker:
            return mapping.ticker.upper()

        # Exact ticker match when name itself looks like a ticker symbol.
        if name_norm and len(name_norm) <= 8 and name_norm.isalpha():
            mapping = session.exec(
                select(CompanyMapping).where(
                    CompanyMapping.ticker == name_norm.upper()
                )
            ).first()
            if mapping and mapping.ticker:
                return mapping.ticker.upper()

        # Normalized / substring / alias match.
        mappings = session.exec(select(CompanyMapping)).all()
        best_match: CompanyMapping | None = None
        best_len = 0

        for m in mappings:
            if not m.ticker:
                continue

            candidates = [m.canonical_name] + (m.aliases or [])
            for candidate in candidates:
                if not candidate:
                    continue

                candidate_norm = normalize_name(candidate)
                if not candidate_norm:
                    continue

                # Strong: normalized names are equal.
                if name_norm == candidate_norm:
                    return m.ticker.upper()

                # Fallback: normalized substring in either direction.
                if name_norm and candidate_norm:
                    if name_norm in candidate_norm or candidate_norm in name_norm:
                        # Prefer the longest canonical/alias to avoid short-name
                        # false positives (e.g. "GM" matching "GMAIL").
                        if len(candidate_norm) > best_len:
                            best_len = len(candidate_norm)
                            best_match = m

                # Original raw substring match for backward compatibility.
                cand_lower = candidate.lower()
                if name_lower in cand_lower or cand_lower in name_lower:
                    if len(cand_lower) > best_len:
                        best_len = len(cand_lower)
                        best_match = m

        if best_match:
            return best_match.ticker.upper()

    return None


def seed_sample_mappings():
    """Seed a few well-known mappings for local development/demo."""
    samples = [
        CompanyMapping(
            canonical_name="Boeing Company",
            ticker="BA",
            aliases=["BOEING", "THE BOEING COMPANY"],
            source="manual",
            confidence="high",
        ),
        CompanyMapping(
            canonical_name="Lockheed Martin",
            ticker="LMT",
            aliases=["LOCKHEED MARTIN CORPORATION", "LOCKHEED MARTIN CORP"],
            source="manual",
            confidence="high",
        ),
        CompanyMapping(
            canonical_name="Pfizer Inc",
            ticker="PFE",
            aliases=["PFIZER", "PFIZER INC."],
            source="manual",
            confidence="high",
        ),
        CompanyMapping(
            canonical_name="Moderna Inc",
            ticker="MRNA",
            aliases=["MODERNA", "MODERNA, INC."],
            source="manual",
            confidence="high",
        ),
        CompanyMapping(
            canonical_name="General Motors",
            ticker="GM",
            aliases=["GENERAL MOTORS COMPANY", "GM"],
            source="manual",
            confidence="high",
        ),
    ]

    with Session(engine) as session:
        for sample in samples:
            existing = session.exec(
                select(CompanyMapping).where(CompanyMapping.ticker == sample.ticker)
            ).first()
            if not existing:
                session.add(sample)
        session.commit()

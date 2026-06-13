"""News date parsing and formatting for Oracle pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def parse_published(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError, OverflowError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw[:19], fmt[: len(raw)])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def enrich_item(item: dict) -> dict:
    raw = item.get("published", "")
    dt = parse_published(raw)
    now = datetime.now(timezone.utc)
    enriched = dict(item)
    if dt:
        ist = dt.astimezone(IST)
        age_min = int((now - dt).total_seconds() // 60)
        enriched["published_iso"] = dt.isoformat()
        enriched["published_display"] = ist.strftime("%a %d %b %Y, %H:%M IST")
        enriched["age_minutes"] = age_min
        enriched["age_display"] = _age_label(age_min)
    else:
        enriched["published_iso"] = ""
        enriched["published_display"] = raw or "Unknown time"
        enriched["age_minutes"] = 99999
        enriched["age_display"] = ""
    return enriched


def _age_label(minutes: int) -> str:
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 48:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def sort_by_date(items: list[dict]) -> list[dict]:
    return sorted(
        items,
        key=lambda x: x.get("published_iso") or "",
        reverse=True,
    )

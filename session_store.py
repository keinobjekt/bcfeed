"""
Session and release metadata persistence utilities.

Stores Gmail-scraped release metadata (not Bandcamp-enriched) keyed by
release date so we can reuse it across runs and avoid re-downloading
messages for dates we've already processed. Also persists empty-date
ranges and scrape status for the same date buckets.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from paths import EMPTY_DATES_PATH, RELEASE_CACHE_PATH, SCRAPE_STATUS_PATH
from util import dedupe_by_url

CacheType = Dict[str, List[dict]]

CACHE_PATH = RELEASE_CACHE_PATH
EMPTY_PATH = EMPTY_DATES_PATH


def _ensure_cache_dir() -> None:
    CACHE_PATH.parent.mkdir(exist_ok=True)


def _load_cache() -> CacheType:
    _ensure_cache_dir()
    if not CACHE_PATH.exists():
        return {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data  # type: ignore[return-value]
    except Exception:
        # Fall back to empty cache on malformed file
        pass
    return {}


def _save_cache(cache: CacheType) -> None:
    _ensure_cache_dir()
    tmp_path = CACHE_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
    tmp_path.replace(CACHE_PATH)


def _load_date_set(path: Path) -> Set[datetime.date]:
    _ensure_cache_dir()
    if not path.exists():
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            dates = set()
            for item in raw if isinstance(raw, list) else []:
                day = _to_date(item)
                if day:
                    dates.add(day)
            return dates
    except Exception:
        return set()


def _save_date_set(path: Path, dates: Set[datetime.date], *, drop_today: bool = False) -> None:
    _ensure_cache_dir()
    tmp_path = path.with_suffix(".tmp")
    if drop_today:
        today = datetime.date.today()
        # Always treat today as not-scraped.
        if today in dates:
            dates = set(dates)
            dates.discard(today)
    payload = sorted(day.isoformat() for day in dates)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    tmp_path.replace(path)


def _load_empty_dates() -> Set[datetime.date]:
    return _load_date_set(EMPTY_PATH)


def _load_scrape_status() -> Set[datetime.date]:
    return _load_date_set(SCRAPE_STATUS_PATH)


def _save_scrape_status(dates: Set[datetime.date]) -> None:
    _save_date_set(SCRAPE_STATUS_PATH, dates, drop_today=True)


def _save_empty_dates(dates: Set[datetime.date]) -> None:
    _save_date_set(EMPTY_PATH, dates)


def _to_date(val) -> datetime.date | None:
    """Normalize string or date into a date object (YYYY-MM-DD; legacy YYYY/MM/DD)."""
    if val is None:
        return None
    if isinstance(val, datetime.date):
        return val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return None


def get_full_release_cache() -> List[dict]:
    """
    Return all cached release metadata, flattened across all dates.
    """
    cache = _load_cache()
    all_items: List[dict] = []
    for day in sorted(cache.keys()):
        day_entries = cache.get(day) or []
        if isinstance(day_entries, list):
            all_items.extend(day_entries)
    return dedupe_by_url(all_items)


def mark_dates_scraped(dates: Iterable[datetime.date], *, exclude_today: bool = True) -> None:
    """
    Mark specific dates as having been scraped from Gmail.
    """
    scraped = _load_scrape_status()
    today = datetime.date.today()
    for day in dates:
        if not isinstance(day, datetime.date):
            continue
        if exclude_today and day == today:
            continue
        scraped.add(day)
    _save_scrape_status(scraped)


def mark_date_range_scraped(start: datetime.date, end: datetime.date, *, exclude_today: bool = True) -> None:
    """Mark a contiguous date range as scraped."""
    if start > end:
        return
    scraped = _load_scrape_status()
    today = datetime.date.today()
    cursor = start
    one_day = datetime.timedelta(days=1)
    while cursor <= end:
        if not (exclude_today and cursor == today):
            scraped.add(cursor)
        cursor += one_day
    _save_scrape_status(scraped)


def mark_dates_not_scraped(dates: Iterable[datetime.date]) -> None:
    """Explicitly mark dates as not-scraped (removes from scraped set)."""
    scraped = _load_scrape_status()
    for day in dates:
        if isinstance(day, datetime.date) and day in scraped:
            scraped.discard(day)
    _save_scrape_status(scraped)


def scrape_status_for_range(start: datetime.date, end: datetime.date) -> Dict[str, bool]:
    """
    Return a mapping of ISO date -> scraped flag for the inclusive range.
    Today's date is always False (not scraped).
    """
    status = {}
    scraped = _load_scrape_status()
    today = datetime.date.today()
    cursor = start
    one_day = datetime.timedelta(days=1)
    while cursor <= end:
        is_scraped = cursor in scraped and cursor != today
        status[cursor.isoformat()] = is_scraped
        cursor += one_day
    return status


def persist_release_metadata(releases: Iterable[dict], *, exclude_today: bool = True) -> None:
    """
    Save release metadata into the cache, keyed by release date.
    Skips today's date when exclude_today is True.
    """
    cache = _load_cache()
    empty_dates = _load_empty_dates()
    today = datetime.date.today()
    scraped_days: Set[datetime.date] = set()
    for release in releases:
        day = _to_date(release.get("date"))
        if not day:
            continue
        if exclude_today and day == today:
            continue
        key = day.isoformat()
        existing = cache.get(key, [])
        # avoid duplicates for the same day by URL
        combined = dedupe_by_url([*existing, release])
        cache[key] = combined
        scraped_days.add(day)
        # if we now have data for a day that was previously marked empty, clear that marker
        if day in empty_dates:
            empty_dates.discard(day)
    _save_cache(cache)
    _save_empty_dates(empty_dates)
    if scraped_days:
        mark_dates_scraped(scraped_days, exclude_today=exclude_today)


def cached_releases_for_range(start: datetime.date, end: datetime.date) -> Tuple[List[dict], List[datetime.date]]:
    """
    Return (cached_releases, missing_dates) for the inclusive date range.
    missing_dates are days that have not been scraped yet.
    """
    cache = _load_cache()
    empty_dates = _load_empty_dates()
    scraped_dates = _load_scrape_status()
    # Treat explicitly empty days as already scraped (so they are not missing).
    scraped_dates.update(empty_dates)
    cursor = start
    cached: List[dict] = []
    missing: List[datetime.date] = []
    one_day = datetime.timedelta(days=1)
    while cursor <= end:
        iso = cursor.isoformat()
        releases_for_day = cache.get(iso)
        if releases_for_day:
            cached.extend(releases_for_day)
        elif cursor not in scraped_dates:
            missing.append(cursor)
        cursor += one_day
    return dedupe_by_url(cached), missing


def collapse_date_ranges(dates: List[datetime.date]) -> List[Tuple[datetime.date, datetime.date]]:
    """Collapse a list of dates into contiguous inclusive ranges."""
    if not dates:
        return []
    dates = sorted(set(dates))
    ranges: List[Tuple[datetime.date, datetime.date]] = []
    start = prev = dates[0]
    for day in dates[1:]:
        if day == prev + datetime.timedelta(days=1):
            prev = day
            continue
        ranges.append((start, prev))
        start = prev = day
    ranges.append((start, prev))
    return ranges


def persist_empty_date_range(start: datetime.date, end: datetime.date, *, exclude_today: bool = True) -> None:
    """
    Record a contiguous date range that returned no Gmail results so we avoid
    querying it again. Optionally excludes today's date.
    """
    if start > end:
        return
    empty_dates = _load_empty_dates()
    today = datetime.date.today()
    cursor = start
    one_day = datetime.timedelta(days=1)
    while cursor <= end:
        if not (exclude_today and cursor == today):
            empty_dates.add(cursor)
        cursor += one_day
    _save_empty_dates(empty_dates)
    mark_date_range_scraped(start, end, exclude_today=exclude_today)

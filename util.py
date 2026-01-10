import datetime
from email.utils import parsedate_to_datetime
from typing import Iterable


def parse_date(val, *, allow_none: bool = False) -> datetime.date | None:
    """Parse an ISO (YYYY-MM-DD) or RFC 2822 date string into a date."""
    if val is None:
        if allow_none:
            return None
        raise ValueError("Missing date")
    if isinstance(val, datetime.datetime):
        return val.date()
    if isinstance(val, datetime.date):
        return val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        try:
            parsed = parsedate_to_datetime(val)
            if parsed is not None:
                return parsed.date()
        except (TypeError, ValueError, IndexError):
            pass
    if allow_none:
        return None
    raise ValueError("Incorrect date format, should be YYYY-MM-DD or RFC 2822 date")


def construct_release(
    is_track=None,
    release_url=None,
    date=None,
    img_url=None,
    artist_name=None,
    release_title=None,
    page_name=None,
    release_id=None,
):
    release = {}
    release['img_url'] = img_url
    release['date'] = date
    release['artist'] = artist_name
    release['title'] = release_title
    release['page_name'] = page_name
    release['url'] = release_url
    release['release_id'] = release_id
    release['is_track'] = is_track
    return release


def dedupe_by_url(items: Iterable[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for item in items:
        url = item.get("url")
        if url and url in seen:
            continue
        if url:
            seen.add(url)
        deduped.append(item)
    return deduped


def dedupe_by_date(items: Iterable[dict], *, keep: str = "last") -> list[dict]:
    """Deduplicate by URL, keeping the first/last entry based on release date."""
    if keep not in {"first", "last"}:
        raise ValueError("keep must be 'first' or 'last'")

    kept: dict[str, tuple[datetime.date, dict]] = {}
    without_url: list[dict] = []

    for item in items:
        url = item.get("url")
        if not url:
            without_url.append(item)
            continue
        date = parse_date(item.get("date"))
        if url not in kept:
            kept[url] = (date, item)
            continue
        existing_date, _ = kept[url]
        if keep == "last":
            replace = date >= existing_date
        else:
            replace = date <= existing_date
        if replace:
            kept[url] = (date, item)

    deduped = [item for _, item in kept.values()]
    deduped.extend(without_url)
    return deduped

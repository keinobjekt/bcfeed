from typing import Dict, Iterable, Tuple
import datetime

from gmail import gmail_authenticate, search_messages, get_messages, scrape_info_from_email
from util import construct_release, parse_date, dedupe_by_date, dedupe_by_url
from session_store import (
    cached_releases_for_range,
    collapse_date_ranges,
    persist_empty_date_range,
    persist_release_metadata,
    mark_date_range_scraped,
)


class MaxResultsExceeded(Exception):
    def __init__(self, max_results: int, found: int):
        super().__init__(f"Exceeded maximum number of results per Gmail search (max={max_results}, num results={found})")
        self.max_results = max_results
        self.found = found


def construct_release_list(emails: Dict, *, log=print) -> list[dict]:
    """Parse Gmail messages into release lists."""
    if log:
        log("Parsing messages...")
    releases_unsifted = []
    for _, email in emails.items():
        date = None
        html_text = email
        if isinstance(email, dict):
            html_text = email.get("html")
            date = parse_date(email.get("date")).strftime("%Y-%m-%d")

        img_url, release_url, is_track, artist_name, release_title, page_name = scrape_info_from_email(
            html_text, email.get("subject")
        )

        if not all(x is None for x in [date, img_url, release_url, is_track, artist_name, release_title, page_name]):
            releases_unsifted.append(
                construct_release(
                    date=date,
                    img_url=img_url,
                    release_url=release_url,
                    is_track=is_track,
                    artist_name=artist_name,
                    release_title=release_title,
                    page_name=page_name,
                )
            )

    # Sift releases with identical urls
    if log:
        log("Checking for releases with identical URLS...")
    releases = dedupe_by_url(releases_unsifted)

    return releases


def populate_release_cache(after_date: str, before_date: str, max_results: int, batch_size: int, log=print) -> None:
    """
    Use cached Gmail-scraped release metadata for previously seen dates.
    Only hit Gmail for dates in the requested range that have no cache entry.
    """
    start_date = parse_date(after_date)
    end_date = parse_date(before_date)
    if start_date > end_date:
        raise ValueError("Start date must be on or before end date")

    cached_releases, missing_dates = cached_releases_for_range(start_date, end_date)
    missing_ranges: Iterable[Tuple[datetime.date, datetime.date]] = collapse_date_ranges(missing_dates)
    releases = list(cached_releases)

    if missing_ranges:
        log("The following date ranges will be downloaded from Gmail:")
        for start_missing, end_missing in missing_ranges:
            log(f"  {start_missing} to {end_missing}")
    else:
        log(f"This date range has already been scraped; no Gmail download needed.")

    try:
        service = gmail_authenticate()
    except Exception as exc:
        log(f"ERROR: {exc}")
        raise

    for start_missing, end_missing in missing_ranges:
        query_after = start_missing.strftime("%Y-%m-%d")
        query_before = (end_missing+datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        search_query = f"from:noreply@bandcamp.com subject:'New release from' before:{query_before} after:{query_after}"
        log("")
        log(f"Querying Gmail for {query_after} to {query_before}...")
        try:
            message_ids = search_messages(service, search_query)
            # Enforce max_results limit explicitly so callers can surface the condition.
            if max_results and len(message_ids) > max_results:
                raise MaxResultsExceeded(max_results, len(message_ids))
        except Exception as exc:
            log(f"ERROR: {exc}")
            raise
        if not message_ids:
            log(f"No messages found for {query_after} to {query_before}")
            persist_empty_date_range(start_missing, end_missing, exclude_today=True)
            continue
        log(f"Found {len(message_ids)} messages for {query_after} to {query_before}")
        try:
            emails = get_messages(service, [msg["id"] for msg in message_ids], "full", batch_size, log=log)
        except Exception as exc:
            log(f"ERROR: {exc}")
            raise
        new_releases = construct_release_list(emails, log=log)
        log(f"Parsed {len(new_releases)} releases from Gmail for {query_after} to {query_before}.")
        releases.extend(new_releases)
        # Mark the entire queried span as scraped so we do not re-fetch it.
        mark_date_range_scraped(start_missing, end_missing, exclude_today=True)

    # Deduplicate on URL after combining cached + new
    deduped = dedupe_by_date(releases, keep="last")

    log("")
    log(f"Loaded {len(deduped)} unique releases including cache.")

    # Always persist the run results when a page will be generated, so cache is up to date.
    persist_release_metadata(deduped, exclude_today=True)

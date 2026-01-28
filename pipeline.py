from typing import Dict, Iterable, Tuple
import datetime

from bandcamp_email_parser import parse_release_email
from provider_factory import create_provider, get_current_provider_type
from email_provider import AuthenticationError, SearchQuery
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
        super().__init__(f"Exceeded maximum number of results per search (max={max_results}, num results={found})")
        self.max_results = max_results
        self.found = found


def construct_release_list(emails: Dict, *, log=print) -> list[dict]:
    """Parse email messages into release lists."""
    if log:
        log("Parsing messages...")
    releases_unsifted = []
    skipped = 0
    for _msg_id, email in emails.items():
        # Handle both EmailMessage objects and legacy dict format
        if hasattr(email, 'html'):
            # EmailMessage from provider
            html_text = email.html
            date = email.date if email.date else None
            subject = email.subject
        elif isinstance(email, dict):
            # Legacy dict format
            html_text = email.get("html")
            date = parse_date(email.get("date")).strftime("%Y-%m-%d") if email.get("date") else None
            subject = email.get("subject", "")
        else:
            # Fallback for string-only emails
            html_text = str(email)
            date = None
            subject = ""

        if not html_text:
            skipped += 1
            continue

        try:
            img_url, release_url, is_track, artist_name, release_title, page_name = parse_release_email(
                html_text, subject
            )
        except Exception as exc:
            skipped += 1
            if log:
                log(f"Warning: failed to parse one message: {exc}")
            continue

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
        if skipped:
            log(f"Skipped {skipped} message(s) due to parse errors.")
    releases = dedupe_by_url(releases_unsifted)

    return releases


def populate_release_cache(after_date: str, before_date: str, max_results: int, batch_size: int, log=print) -> None:
    """
    Use cached email-scraped release metadata for previously seen dates.
    Only hit email provider for dates in the requested range that have no cache entry.
    """
    start_date = parse_date(after_date)
    end_date = parse_date(before_date)
    if start_date > end_date:
        raise ValueError("Start date must be on or before end date")

    cached_releases, missing_dates = cached_releases_for_range(start_date, end_date)
    missing_ranges: Iterable[Tuple[datetime.date, datetime.date]] = collapse_date_ranges(missing_dates)
    releases = list(cached_releases)

    # Get provider type for logging
    provider_type = get_current_provider_type()
    provider_name = "IMAP" if provider_type == "imap" else "Gmail"

    if missing_ranges:
        log(f"The following date ranges will be downloaded from {provider_name}:")
        for start_missing, end_missing in missing_ranges:
            log(f"  {start_missing} to {end_missing}")
    else:
        log(f"This date range has already been scraped; no {provider_name} download needed.")
        # Still need to dedupe and persist cached releases
        deduped = dedupe_by_date(releases, keep="last")
        persist_release_metadata(deduped, exclude_today=True)
        log("")
        log(f"Loaded {len(deduped)} unique releases from cache.")
        return

    provider = None
    try:
        provider = create_provider()
        provider.authenticate()

        for start_missing, end_missing in missing_ranges:
            query_after = start_missing.strftime("%Y-%m-%d")
            query_before = (end_missing + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            log("")
            log(f"Querying {provider_name} for {query_after} to {query_before}...")
            try:
                # Build search query based on provider type
                search_query = SearchQuery(
                    sender="noreply@bandcamp.com",
                    subject_contains="New release from",
                    after_date=query_after.replace("-", "/"),  # Provider expects YYYY/MM/DD
                    before_date=query_before.replace("-", "/"),
                )
                message_ids = provider.search(search_query, max_results=max_results, log=log)
                # Enforce max_results limit explicitly so callers can surface the condition.
                if max_results and len(message_ids) > max_results:
                    raise MaxResultsExceeded(max_results, len(message_ids))
            except MaxResultsExceeded:
                raise
            except Exception as exc:
                log(f"ERROR: {exc}")
                raise
            if not message_ids:
                log(f"No messages found for {query_after} to {query_before}")
                persist_empty_date_range(start_missing, end_missing, exclude_today=True)
                continue
            log(f"Found {len(message_ids)} messages for {query_after} to {query_before}")
            try:
                emails = provider.fetch(message_ids, batch_size=batch_size, log=log)
            except Exception as exc:
                log(f"ERROR: {exc}")
                raise
            new_releases = construct_release_list(emails, log=log)
            log(f"Parsed {len(new_releases)} releases from {provider_name} for {query_after} to {query_before}.")
            releases.extend(new_releases)
            # Mark the entire queried span as scraped so we do not re-fetch it.
            mark_date_range_scraped(start_missing, end_missing, exclude_today=True)
    except AuthenticationError as exc:
        log(f"ERROR: Authentication failed: {exc}")
        raise
    except Exception as exc:
        log(f"ERROR: {exc}")
        raise
    finally:
        if provider is not None:
            try:
                provider.close()
            except Exception:
                pass

    # Deduplicate on URL after combining cached + new
    deduped = dedupe_by_date(releases, keep="last")

    log("")
    log(f"Loaded {len(deduped)} unique releases including cache.")

    # Always persist the run results when a page will be generated, so cache is up to date.
    persist_release_metadata(deduped, exclude_today=True)

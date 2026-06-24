"""
IMAP email provider implementation.

Supports generic IMAP servers including Gmail, iCloud, Outlook, and others.
"""

from __future__ import annotations

import email
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Callable, Optional

from email_provider import (
    EmailProvider,
    EmailMessage,
    SearchQuery,
    AuthenticationError,
)

from imap_client import ImapClient, ImapConfig


class ImapProvider(EmailProvider):
    """
    IMAP-based email provider.

    Supports any IMAP-compatible email server.
    """

    def __init__(self, config: ImapConfig):
        """
        Initialize IMAP provider.

        Args:
            config: IMAP server configuration
        """
        self.config = config
        self._client = ImapClient(config)

    def authenticate(self) -> None:
        """
        Connect and authenticate with the IMAP server.

        Raises:
            AuthenticationError: If connection or login fails
        """
        self._client.authenticate()

    def search(
        self,
        query: SearchQuery,
        max_results: int = 100,
        log: Optional[Callable[[str], None]] = None,
    ) -> list[str]:
        """
        Search for messages matching the query using IMAP UID SEARCH.

        Args:
            query: Search parameters
            max_results: Maximum number of message IDs to return
            log: Optional progress callback

        Returns:
            List of IMAP UIDs (as strings)
        """
        # Build IMAP search criteria
        criteria = self._build_search_criteria(query)

        if log:
            log(f"IMAP UID search: {' '.join(criteria)}")

        message_ids = self._client.uid_search(criteria)

        # IMAP returns oldest first; reverse for newest first
        message_ids.reverse()

        # Apply max_results limit
        return message_ids[:max_results]

    def _build_search_criteria(self, query: SearchQuery) -> list[str]:
        """
        Build IMAP SEARCH criteria from SearchQuery.

        Note: IMAP search capabilities vary by server. We use a conservative
        set of criteria that should work on most servers. String values with
        spaces must be quoted for strict servers like iCloud.
        """
        criteria = []

        # FROM filter - quote if contains spaces
        if query.sender:
            criteria.extend(["FROM", f'"{query.sender}"'])

        # SUBJECT filter (partial match) - quote if contains spaces
        if query.subject_contains:
            criteria.extend(["SUBJECT", f'"{query.subject_contains}"'])

        # Date filters
        # IMAP uses SINCE (inclusive) and BEFORE (exclusive) with DD-Mon-YYYY format
        if query.after_date:
            imap_date = self._to_imap_date(query.after_date)
            if imap_date:
                criteria.extend(["SINCE", imap_date])

        if query.before_date:
            imap_date = self._to_imap_date(query.before_date)
            if imap_date:
                criteria.extend(["BEFORE", imap_date])

        return criteria if criteria else ["ALL"]

    def _to_imap_date(self, date_str: str) -> Optional[str]:
        """
        Convert YYYY/MM/DD or YYYY-MM-DD to DD-Mon-YYYY for IMAP.

        Args:
            date_str: Date in YYYY/MM/DD or YYYY-MM-DD format

        Returns:
            Date in DD-Mon-YYYY format (e.g., "25-Dec-2024"), or None if invalid
        """
        # Normalize separators
        date_str = date_str.replace("/", "-")

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%d-%b-%Y")  # e.g., "25-Dec-2024"
        except ValueError:
            return None

    def fetch(
        self,
        message_ids: list[str],
        batch_size: int = 20,
        log: Optional[Callable[[str], None]] = None,
    ) -> dict[str, EmailMessage]:
        """
        Fetch full message content for given IDs.

        Args:
            message_ids: List of IMAP UIDs
            batch_size: Used for progress logging (IMAP fetches one at a time)
            log: Optional progress callback

        Returns:
            Dict mapping message ID to EmailMessage
        """
        if not message_ids:
            return {}

        results = {}
        total = len(message_ids)

        for i, msg_id in enumerate(message_ids):
            if log and i % batch_size == 0:
                end = min(i + batch_size, total)
                log(f"Downloading messages {i} to {end}")

            try:
                email_msg = self._fetch_single(msg_id)
                if email_msg:
                    results[msg_id] = email_msg
            except Exception as e:
                if log:
                    log(f"Warning: Failed to fetch message {msg_id}: {e}")

        return results

    def _fetch_single(self, msg_id: str) -> Optional[EmailMessage]:
        """
        Fetch and parse a single message.

        Args:
            msg_id: IMAP UID

        Returns:
            EmailMessage if successful, None if message couldn't be parsed
        """
        # Use BODY[] instead of RFC822 for better compatibility
        # Some servers (like iCloud) don't return message content with RFC822
        # Use UID FETCH since we're working with UIDs from search
        raw_email = self._client.uid_fetch_body(msg_id)
        if not raw_email:
            return None

        msg = email.message_from_bytes(raw_email)

        # Extract HTML body
        html_content = self._extract_html(msg)

        # Extract and parse date
        date_header = msg.get("Date", "")
        parsed_date = ""
        if date_header:
            try:
                dt = parsedate_to_datetime(date_header)
                parsed_date = dt.strftime("%Y-%m-%d")
            except Exception:
                pass

        # Extract and decode subject
        subject = self._decode_header(msg.get("Subject", ""))

        return EmailMessage(
            html=html_content,
            date=parsed_date,
            subject=subject,
        )

    def _extract_html(self, msg: email.message.Message) -> str:
        """
        Extract HTML content from an email message.

        Walks the MIME structure to find text/html parts.

        Args:
            msg: Parsed email message

        Returns:
            HTML content as string, or empty string if not found
        """
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Skip attachments
                if "attachment" in content_disposition:
                    continue

                if content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")
        else:
            # Single-part message
            if msg.get_content_type() == "text/html":
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")

        return ""

    def _decode_header(self, header_value: str) -> str:
        """
        Decode RFC 2047 encoded header (e.g., =?UTF-8?Q?...?=).

        Args:
            header_value: Raw header value

        Returns:
            Decoded header as string
        """
        if not header_value:
            return ""

        try:
            decoded_parts = decode_header(header_value)
            result = []
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    result.append(part.decode(charset or "utf-8", errors="replace"))
                else:
                    result.append(part)
            return "".join(result)
        except Exception:
            return header_value

    def close(self) -> None:
        """Close the IMAP connection."""
        self._client.close()

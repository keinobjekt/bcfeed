"""
IMAP email provider implementation.

Supports generic IMAP servers including Gmail, iCloud, Outlook, and others.
Uses Python's standard library imaplib and email modules.
"""

from __future__ import annotations

import email
import imaplib
import ssl
from dataclasses import dataclass
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Callable, Optional

from email_provider import (
    EmailProvider,
    EmailMessage,
    SearchQuery,
    AuthenticationError,
    ProviderError,
)


@dataclass
class ImapConfig:
    """IMAP server configuration."""
    host: str
    port: int = 993
    username: str = ""
    password: str = ""  # App-specific password recommended
    use_ssl: bool = True
    folder: str = "INBOX"  # Use "[Gmail]/All Mail" for Gmail


class ImapProvider(EmailProvider):
    """
    IMAP-based email provider.

    Supports any IMAP-compatible email server. For Gmail, Outlook, iCloud,
    and Yahoo, users typically need to generate an app-specific password.
    """

    def __init__(self, config: ImapConfig):
        """
        Initialize IMAP provider.

        Args:
            config: IMAP server configuration
        """
        self.config = config
        self._connection: Optional[imaplib.IMAP4_SSL | imaplib.IMAP4] = None

    def authenticate(self) -> None:
        """
        Connect and authenticate with the IMAP server.

        Raises:
            AuthenticationError: If connection or login fails
        """
        if not self.config.host:
            raise AuthenticationError("IMAP host not configured")
        if not self.config.username:
            raise AuthenticationError("IMAP username not configured")
        if not self.config.password:
            raise AuthenticationError("IMAP password not configured")

        try:
            if self.config.use_ssl:
                context = ssl.create_default_context()
                self._connection = imaplib.IMAP4_SSL(
                    self.config.host,
                    self.config.port,
                    ssl_context=context,
                )
            else:
                self._connection = imaplib.IMAP4(
                    self.config.host,
                    self.config.port,
                )

            self._connection.login(
                self.config.username,
                self.config.password,
            )

            # Select folder (readonly to avoid modifying messages)
            status, data = self._connection.select(self.config.folder, readonly=True)
            if status != "OK":
                raise AuthenticationError(
                    f"Failed to select folder '{self.config.folder}'. "
                    f"Check that the folder exists."
                )

        except imaplib.IMAP4.error as e:
            self._connection = None
            error_msg = str(e)
            if "authentication" in error_msg.lower() or "login" in error_msg.lower():
                raise AuthenticationError(
                    f"IMAP login failed. Check username and password. "
                    f"For Gmail/iCloud/Outlook, use an app-specific password. ({e})"
                )
            raise AuthenticationError(f"IMAP error: {e}")
        except (OSError, TimeoutError) as e:
            self._connection = None
            raise AuthenticationError(
                f"Could not connect to {self.config.host}:{self.config.port}. "
                f"Check server address and network connection. ({e})"
            )
        except Exception as e:
            self._connection = None
            raise AuthenticationError(f"IMAP connection failed: {e}")

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
        if not self._connection:
            raise AuthenticationError("Not authenticated. Call authenticate() first.")

        # Build IMAP search criteria
        criteria = self._build_search_criteria(query)

        if log:
            log(f"IMAP UID search: {' '.join(criteria)}")

        try:
            # Use UID SEARCH for stable message IDs
            # This is more reliable across different IMAP servers including iCloud
            status, data = self._connection.uid('SEARCH', *criteria)
            if status != "OK":
                raise ProviderError(f"IMAP search failed: {status}")

            # data[0] is space-separated list of UIDs
            if not data or not data[0]:
                return []

            message_ids = data[0].decode().split()

            # IMAP returns oldest first; reverse for newest first
            message_ids.reverse()

            # Apply max_results limit
            return message_ids[:max_results]

        except imaplib.IMAP4.error as e:
            raise ProviderError(f"IMAP search error: {e}")

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
        if not self._connection:
            raise AuthenticationError("Not authenticated. Call authenticate() first.")

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
        status, data = self._connection.uid('FETCH', msg_id, 'BODY[]')
        
        if status != "OK" or not data or not data[0]:
            return None

        # data[0] can be either:
        # - A tuple: (envelope, message_bytes) - most common format
        # - Raw bytes directly - some servers like iCloud return this
        if isinstance(data[0], tuple) and len(data[0]) >= 2:
            raw_email = data[0][1]
        elif isinstance(data[0], bytes):
            raw_email = data[0]
        else:
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
        if self._connection:
            try:
                self._connection.close()
                self._connection.logout()
            except Exception:
                pass
            finally:
                self._connection = None

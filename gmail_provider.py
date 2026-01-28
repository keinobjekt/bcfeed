"""
Gmail API provider implementation.

Wraps the existing gmail.py functionality to implement the EmailProvider interface.
"""

from __future__ import annotations

from typing import Callable, Optional

from email_provider import (
    EmailProvider,
    EmailMessage,
    SearchQuery,
    AuthenticationError,
    ProviderError,
)
from gmail_client import (
    gmail_authenticate,
    search_messages,
    get_messages,
    GmailAuthError,
)


class GmailProvider(EmailProvider):
    """
    Gmail API provider using OAuth2 authentication.

    This wraps the existing gmail.py functionality to provide a consistent
    interface with the IMAP provider.
    """

    def __init__(self):
        """Initialize Gmail provider (does not authenticate yet)."""
        self._service = None

    def authenticate(self) -> None:
        """
        Authenticate with Gmail using OAuth2.

        Raises:
            AuthenticationError: If credentials are missing or invalid.
        """
        try:
            self._service = gmail_authenticate()
        except GmailAuthError as e:
            raise AuthenticationError(str(e))
        except FileNotFoundError as e:
            raise AuthenticationError(
                f"Gmail credentials not found. Please upload credentials.json: {e}"
            )
        except Exception as e:
            raise AuthenticationError(f"Gmail authentication failed: {e}")

    def search(
        self,
        query: SearchQuery,
        max_results: int = 100,
        log: Optional[Callable[[str], None]] = None,
    ) -> list[str]:
        """
        Search for messages matching the query using Gmail query syntax.

        Args:
            query: Search parameters
            max_results: Maximum number of message IDs to return
            log: Optional progress callback (unused for Gmail)

        Returns:
            List of Gmail message IDs
        """
        if not self._service:
            raise AuthenticationError("Not authenticated. Call authenticate() first.")

        # Build Gmail search query from SearchQuery
        gmail_query = self._build_gmail_query(query)

        try:
            messages = search_messages(self._service, gmail_query)
            # Extract just the IDs and limit results
            ids = [m['id'] for m in messages]
            return ids[:max_results]
        except GmailAuthError as e:
            raise AuthenticationError(str(e))
        except Exception as e:
            raise ProviderError(f"Gmail search error: {e}")

    def _build_gmail_query(self, query: SearchQuery) -> str:
        """Convert SearchQuery to Gmail search syntax."""
        parts = []

        if query.sender:
            parts.append(f"from:{query.sender}")

        if query.subject_contains:
            parts.append(f"subject:{query.subject_contains}")

        if query.after_date:
            # Gmail uses YYYY/MM/DD format
            parts.append(f"after:{query.after_date}")

        if query.before_date:
            parts.append(f"before:{query.before_date}")

        return " ".join(parts)

    def fetch(
        self,
        message_ids: list[str],
        batch_size: int = 20,
        log: Optional[Callable[[str], None]] = None,
    ) -> dict[str, EmailMessage]:
        """
        Fetch full message content for given IDs.

        Args:
            message_ids: List of Gmail message IDs
            batch_size: Number of messages to fetch per batch
            log: Optional progress callback

        Returns:
            Dict mapping message ID to EmailMessage
        """
        if not self._service:
            raise AuthenticationError("Not authenticated. Call authenticate() first.")

        if not message_ids:
            return {}

        try:
            # get_messages returns dict with string keys and dict values
            raw_messages = get_messages(
                self._service,
                message_ids,
                format='full',
                batch_size=batch_size,
                log=log,
            )

            # Convert to EmailMessage format
            results = {}
            for idx, msg_data in raw_messages.items():
                # Map back to original message ID
                # Note: get_messages returns indices as keys, so we need to look up
                original_id = message_ids[int(idx)] if idx.isdigit() else idx

                results[original_id] = EmailMessage(
                    html=msg_data.get('html', ''),
                    date=msg_data.get('date', ''),
                    subject=msg_data.get('subject', ''),
                )

            return results

        except GmailAuthError as e:
            raise AuthenticationError(str(e))
        except Exception as e:
            raise ProviderError(f"Gmail fetch error: {e}")

    def close(self) -> None:
        """Clean up Gmail service connection."""
        self._service = None

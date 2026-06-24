"""
Abstract email provider interface.

Defines the contract that all email providers must implement,
enabling bcfeed to work with Gmail API, IMAP, or other email backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class EmailMessage:
    """Normalized email message structure returned by providers."""
    html: str       # HTML body content (decoded)
    date: str       # YYYY-MM-DD format
    subject: str    # Email subject line


@dataclass
class SearchQuery:
    """Provider-agnostic search parameters for finding Bandcamp emails."""
    sender: str             # e.g., "noreply@bandcamp.com"
    subject_contains: str   # e.g., "New release from"
    after_date: str         # YYYY/MM/DD format
    before_date: str        # YYYY/MM/DD format


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class ProviderError(Exception):
    """Raised for provider-specific errors during search/fetch."""
    pass


class EmailProvider(ABC):
    """
    Base class for email providers.

    Implementations must handle:
    - Authentication with the email service
    - Searching for messages matching criteria
    - Fetching full message content
    - Cleanup on close
    """

    @abstractmethod
    def authenticate(self) -> None:
        """
        Authenticate with the email service.

        Raises:
            AuthenticationError: If authentication fails (invalid credentials,
                                 network issues, missing config, etc.)
        """
        pass

    @abstractmethod
    def search(
        self,
        query: SearchQuery,
        max_results: int = 100,
        log: Optional[Callable[[str], None]] = None,
    ) -> list[str]:
        """
        Search for messages matching the query.

        Args:
            query: Search parameters (sender, subject, date range)
            max_results: Maximum number of message IDs to return
            log: Optional callback for progress logging

        Returns:
            List of message IDs (provider-specific format)

        Raises:
            AuthenticationError: If not authenticated
            ProviderError: If search fails
        """
        pass

    @abstractmethod
    def fetch(
        self,
        message_ids: list[str],
        batch_size: int = 20,
        log: Optional[Callable[[str], None]] = None,
    ) -> dict[str, EmailMessage]:
        """
        Fetch full message content for given IDs.

        Args:
            message_ids: List of message IDs from search()
            batch_size: Number of messages to fetch per batch (for progress)
            log: Optional callback for progress logging

        Returns:
            Dict mapping message ID to EmailMessage

        Raises:
            AuthenticationError: If not authenticated
            ProviderError: If fetch fails
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Clean up resources (close connections, clear state, etc.).

        Should be safe to call multiple times.
        """
        pass

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.close()
        return False

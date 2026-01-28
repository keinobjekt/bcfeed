"""
IMAP client utilities.

Handles low-level IMAP connection/login/select/search/fetch operations.
Parsing MIME content into EmailMessage lives in the provider layer.
"""

from __future__ import annotations

import imaplib
import ssl
from dataclasses import dataclass
from typing import Optional

from email_provider import AuthenticationError, ProviderError


@dataclass
class ImapConfig:
    """IMAP server configuration."""

    host: str
    port: int = 993
    username: str = ""
    password: str = ""  # App-specific password recommended
    use_ssl: bool = True
    folder: str = "INBOX"  # Use "[Gmail]/All Mail" for Gmail


class ImapClient:
    def __init__(self, config: ImapConfig):
        self.config = config
        self._connection: Optional[imaplib.IMAP4_SSL | imaplib.IMAP4] = None

    def authenticate(self) -> None:
        """
        Connect, login, and select the configured folder (readonly).
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

            status, _data = self._connection.select(self.config.folder, readonly=True)
            if status != "OK":
                raise AuthenticationError(
                    f"Failed to select folder '{self.config.folder}'. "
                    f"Check that the folder exists."
                )

        except imaplib.IMAP4.error as exc:
            self._connection = None
            error_msg = str(exc)
            if "authentication" in error_msg.lower() or "login" in error_msg.lower():
                raise AuthenticationError(
                    "IMAP login failed. Check username and password. "
                    f"For Gmail/iCloud/Outlook, use an app-specific password. ({exc})"
                )
            raise AuthenticationError(f"IMAP error: {exc}")
        except (OSError, TimeoutError) as exc:
            self._connection = None
            raise AuthenticationError(
                f"Could not connect to {self.config.host}:{self.config.port}. "
                f"Check server address and network connection. ({exc})"
            )
        except Exception as exc:
            self._connection = None
            raise AuthenticationError(f"IMAP connection failed: {exc}")

    def uid_search(self, criteria: list[str]) -> list[str]:
        if not self._connection:
            raise AuthenticationError("Not authenticated. Call authenticate() first.")

        try:
            status, data = self._connection.uid("SEARCH", *criteria)
            if status != "OK":
                raise ProviderError(f"IMAP search failed: {status}")
            if not data or not data[0]:
                return []
            return data[0].decode().split()
        except imaplib.IMAP4.error as exc:
            raise ProviderError(f"IMAP search error: {exc}")

    def uid_fetch_body(self, msg_id: str) -> bytes | None:
        if not self._connection:
            raise AuthenticationError("Not authenticated. Call authenticate() first.")

        status, data = self._connection.uid("FETCH", msg_id, "BODY[]")
        if status != "OK" or not data or not data[0]:
            return None

        # data[0] can be either:
        # - A tuple: (envelope, message_bytes) - most common format
        # - Raw bytes directly - some servers like iCloud return this
        if isinstance(data[0], tuple) and len(data[0]) >= 2:
            return data[0][1]
        if isinstance(data[0], bytes):
            return data[0]
        return None

    def close(self) -> None:
        if self._connection:
            try:
                self._connection.close()
                self._connection.logout()
            except Exception:
                pass
            finally:
                self._connection = None


"""
Factory for creating email providers and managing provider configuration.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Literal, Optional

from email_provider import EmailProvider
from paths import get_data_dir


ProviderType = Literal["gmail", "imap"]

CONFIG_FILENAME = "provider_config.json"


def _get_config_path() -> Path:
    """Return the path to the provider configuration file."""
    return get_data_dir() / CONFIG_FILENAME


def load_provider_config() -> dict:
    """
    Load provider configuration from disk.

    Returns:
        Configuration dict with at least {"provider": "gmail"} as default.
    """
    config_path = _get_config_path()
    if not config_path.exists():
        return {"provider": "gmail"}

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return {"provider": "gmail"}


def save_provider_config(config: dict) -> None:
    """
    Save provider configuration to disk with restrictive permissions.

    Args:
        config: Configuration dict to save
    """
    config_path = _get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    tmp = config_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, indent=2), encoding="utf-8")

    # Set restrictive permissions before replacing (password may be in config)
    try:
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)  # 600
    except OSError:
        pass  # May fail on some platforms, but continue anyway

    tmp.replace(config_path)


def create_provider(
    provider_type: Optional[ProviderType] = None,
    config: Optional[dict] = None,
) -> EmailProvider:
    """
    Create an email provider instance.

    Args:
        provider_type: Either "gmail" or "imap". If None, reads from config.
        config: Provider-specific configuration. If None, reads from disk.

    Returns:
        Configured EmailProvider instance (not yet authenticated)

    Raises:
        ValueError: If provider type is unknown or IMAP config is missing
    """
    if config is None:
        config = load_provider_config()

    if provider_type is None:
        provider_type = config.get("provider", "gmail")

    if provider_type == "gmail":
        from gmail_provider import GmailProvider
        return GmailProvider()

    elif provider_type == "imap":
        from imap_provider import ImapProvider, ImapConfig

        imap_config = config.get("imap_config")
        if not imap_config:
            raise ValueError(
                "IMAP provider requires configuration. "
                "Please configure IMAP settings first."
            )

        return ImapProvider(
            ImapConfig(
                host=imap_config.get("host", ""),
                port=imap_config.get("port", 993),
                username=imap_config.get("username", ""),
                password=imap_config.get("password", ""),
                use_ssl=imap_config.get("use_ssl", True),
                folder=imap_config.get("folder", "INBOX"),
            )
        )

    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


def get_current_provider_type() -> ProviderType:
    """
    Get the currently configured provider type.

    Returns:
        "gmail" or "imap"
    """
    config = load_provider_config()
    provider = config.get("provider", "gmail")
    if provider not in ("gmail", "imap"):
        return "gmail"
    return provider

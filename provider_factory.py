"""
Factory for creating email providers and managing provider configuration.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Literal, Optional

from credential_store import CredentialStoreError, get_imap_password, save_imap_password
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
            return _migrate_legacy_imap_password(data)
    except Exception:
        pass

    return {"provider": "gmail"}


def save_provider_config(config: dict) -> None:
    """
    Save provider configuration to disk and store IMAP password in keychain.

    Args:
        config: Configuration dict to save
    """
    stored_config = _store_imap_password_and_strip_from_config(config)
    _write_provider_config_file(stored_config)


def _write_provider_config_file(config: dict) -> None:
    """Write provider configuration file to disk."""
    config_path = _get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    tmp = config_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, indent=2), encoding="utf-8")

    tmp.replace(config_path)


def _store_imap_password_and_strip_from_config(config: dict) -> dict:
    """Persist the IMAP password to the keychain and remove it from the config copy."""
    stored_config = deepcopy(config)
    imap_config = stored_config.get("imap_config")
    if isinstance(imap_config, dict):
        password = imap_config.pop("password", None)
        if password:
            save_imap_password(password)
    return stored_config


def _migrate_legacy_imap_password(config: dict) -> dict:
    """Move any legacy plaintext IMAP password from config into the keychain."""
    imap_config = config.get("imap_config")
    if not isinstance(imap_config, dict):
        return config

    legacy_password = imap_config.get("password")
    if not legacy_password:
        return config

    migrated = deepcopy(config)
    migrated_imap = dict(imap_config)
    migrated_imap.pop("password", None)
    migrated["imap_config"] = migrated_imap

    try:
        save_imap_password(str(legacy_password))
        _write_provider_config_file(migrated)
    except CredentialStoreError:
        return config

    return migrated


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
        from imap_provider import ImapConfig, ImapProvider

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
                password=_load_imap_password(imap_config),
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


def _load_imap_password(imap_config: dict) -> str:
    """Load the IMAP password from the keychain, falling back to legacy config."""
    try:
        return get_imap_password() or imap_config.get("password", "")
    except CredentialStoreError:
        return imap_config.get("password", "")

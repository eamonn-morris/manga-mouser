"""
Configuration management for MangaMouser.

Centralizes all configuration in a typed dataclass with validation.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


@dataclass
class QBittorrentConfig:
    """qBittorrent connection configuration."""

    host: str = "localhost"
    port: int = 8080
    username: str = ""
    password: str = ""
    category: str = "manga"


@dataclass
class Config:
    """Application configuration."""

    # Required
    feed_url: str

    # Paths
    base_dir: Path
    matches_file: Path
    log_file: Path

    # Feed settings
    target_category: str = "Literature - English-translated"
    user_agent: str = "MangaMouser/1.0"

    # qBittorrent settings
    qbittorrent: QBittorrentConfig = field(default_factory=QBittorrentConfig)


def load_config(base_dir: Path | None = None) -> Config:
    """
    Load configuration from environment variables.

    Args:
        base_dir: Base directory for paths. Defaults to script directory.

    Returns:
        Config object with all settings.

    Raises:
        ConfigError: If required configuration is missing.
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.resolve()

    # Load .env file
    env_file = base_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # Required: FEED_URL
    feed_url = os.getenv("FEED_URL")
    if not feed_url:
        raise ConfigError(
            "FEED_URL environment variable is required. "
            "Set it in .env or export it directly."
        )

    # Paths
    downloads_dir = base_dir / "downloads"
    matches_file = downloads_dir / "matches.jsonl"
    log_file = downloads_dir / "mouser.log"

    # qBittorrent config
    qb_config = QBittorrentConfig(
        host=os.getenv("QB_HOST", "localhost"),
        port=int(os.getenv("QB_PORT", "8080")),
        username=os.getenv("QB_USER", ""),
        password=os.getenv("QB_PASSWORD", ""),
        category=os.getenv("QB_CATEGORY", "manga"),
    )

    return Config(
        feed_url=feed_url,
        base_dir=base_dir,
        matches_file=matches_file,
        log_file=log_file,
        target_category=os.getenv("TARGET_CATEGORY", "Literature - English-translated"),
        user_agent=os.getenv("USER_AGENT", "MangaMouser/1.0"),
        qbittorrent=qb_config,
    )

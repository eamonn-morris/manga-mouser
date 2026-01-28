"""
qBittorrent downloader functions.

This module provides backward-compatible functions that wrap the
QBittorrentDownloader class. New code should use QBittorrentDownloader directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from downloaders.qbittorrent import QBittorrentDownloader

if TYPE_CHECKING:
    from config import Config


def is_available(config: Config) -> bool:
    """Check if qBittorrent is reachable."""
    return QBittorrentDownloader(config).is_available()


def add_torrents(magnets: list[str], config: Config) -> tuple[int, int]:
    """
    Add multiple magnet links to qBittorrent.
    Returns tuple of (success_count, fail_count).
    """
    return QBittorrentDownloader(config).add_torrents(magnets)


def get_torrent_status(infohashes: list[str], config: Config) -> dict[str, dict] | None:
    """
    Query qBittorrent for status of torrents by infohash.
    Returns dict mapping infohash -> status dict, or None if connection fails.
    """
    return QBittorrentDownloader(config).get_torrent_status_dicts(infohashes)


def get_all_torrents(config: Config) -> list[dict] | None:
    """
    Get all torrents from qBittorrent.
    Returns list of torrent status dicts or None if connection fails.
    """
    return QBittorrentDownloader(config).get_all_torrents()

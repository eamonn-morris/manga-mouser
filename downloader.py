from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import qbittorrentapi

if TYPE_CHECKING:
    from config import Config

logger = logging.getLogger("mangamouser")


def connect(config: Config) -> qbittorrentapi.Client | None:
    """
    Authenticate with qBittorrent and return client instance.
    Returns None if connection fails.
    """
    qb = config.qbittorrent
    try:
        client = qbittorrentapi.Client(
            host=qb.host,
            port=qb.port,
            username=qb.username,
            password=qb.password,
        )
        client.auth_log_in()
        logger.debug(f"Connected to qBittorrent at {qb.host}:{qb.port}")
        return client
    except qbittorrentapi.LoginFailed as e:
        logger.error(f"qBittorrent login failed: {e}")
        return None
    except qbittorrentapi.APIConnectionError as e:
        logger.error(f"qBittorrent connection error: {e}")
        return None


def is_available(config: Config) -> bool:
    """
    Check if qBittorrent is reachable.
    """
    client = connect(config)
    if client:
        client.auth_log_out()
        return True
    return False


def add_torrent(
    client: qbittorrentapi.Client, magnet: str, category: str
) -> bool:
    """
    Add magnet link to qBittorrent client.
    Returns True on success, False on failure.
    """
    try:
        result = client.torrents_add(urls=magnet, category=category)
        if result == "Ok.":
            logger.debug(f"Added torrent to qBittorrent: {magnet[:60]}...")
            return True
        else:
            logger.warning(f"qBittorrent returned unexpected result: {result}")
            return False
    except Exception as e:
        logger.error(f"Failed to add torrent: {e}")
        return False


def add_torrents(magnets: list[str], config: Config) -> tuple[int, int]:
    """
    Add multiple magnet links to qBittorrent.
    Returns tuple of (success_count, fail_count).
    """
    if not magnets:
        return 0, 0

    client = connect(config)
    if not client:
        logger.warning("Cannot add torrents: qBittorrent unavailable")
        return 0, len(magnets)

    success_count = 0
    fail_count = 0
    category = config.qbittorrent.category

    for magnet in magnets:
        if add_torrent(client, magnet, category):
            success_count += 1
        else:
            fail_count += 1

    client.auth_log_out()
    return success_count, fail_count


def get_torrent_status(
    infohashes: list[str], config: Config
) -> dict[str, dict] | None:
    """
    Query qBittorrent for status of torrents by infohash.
    Returns dict mapping infohash -> status dict with keys:
        - state: qBittorrent state string
        - progress: float 0.0-1.0
        - name: torrent name
        - size: total size in bytes
        - downloaded: bytes downloaded
        - uploaded: bytes uploaded
        - ratio: share ratio
    Returns None if connection fails.
    """
    if not infohashes:
        return {}

    client = connect(config)
    if not client:
        logger.warning("Cannot get torrent status: qBittorrent unavailable")
        return None

    # Normalize infohashes to lowercase for comparison
    hash_set = {h.lower() for h in infohashes}

    try:
        torrents = client.torrents_info()
        results = {}
        for torrent in torrents:
            torrent_hash = torrent.hash.lower()
            if torrent_hash in hash_set:
                results[torrent_hash] = {
                    "state": torrent.state,
                    "progress": torrent.progress,
                    "name": torrent.name,
                    "size": torrent.size,
                    "downloaded": torrent.downloaded,
                    "uploaded": torrent.uploaded,
                    "ratio": torrent.ratio,
                }
        client.auth_log_out()
        return results
    except Exception as e:
        logger.error(f"Failed to get torrent status: {e}")
        client.auth_log_out()
        return None


def get_all_torrents(config: Config) -> list[dict] | None:
    """
    Get all torrents from qBittorrent.
    Returns list of torrent status dicts or None if connection fails.
    """
    client = connect(config)
    if not client:
        logger.warning("Cannot get torrents: qBittorrent unavailable")
        return None

    try:
        category = config.qbittorrent.category
        torrents = client.torrents_info(category=category)
        results = []
        for torrent in torrents:
            results.append({
                "hash": torrent.hash.lower(),
                "state": torrent.state,
                "progress": torrent.progress,
                "name": torrent.name,
                "size": torrent.size,
                "downloaded": torrent.downloaded,
                "uploaded": torrent.uploaded,
                "ratio": torrent.ratio,
            })
        client.auth_log_out()
        return results
    except Exception as e:
        logger.error(f"Failed to get torrents: {e}")
        client.auth_log_out()
        return None

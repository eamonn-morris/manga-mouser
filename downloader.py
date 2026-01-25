import logging
import os

import qbittorrentapi

logger = logging.getLogger("mangamouser")


def get_config():
    """
    Get qBittorrent configuration from environment variables.
    """
    return {
        "host": os.getenv("QB_HOST", "localhost"),
        "port": int(os.getenv("QB_PORT", "8080")),
        "username": os.getenv("QB_USER", ""),
        "password": os.getenv("QB_PASSWORD", ""),
        "category": os.getenv("QB_CATEGORY", "manga"),
    }


def connect():
    """
    Authenticate with qBittorrent and return client instance.
    Returns None if connection fails.
    """
    config = get_config()
    try:
        client = qbittorrentapi.Client(
            host=config["host"],
            port=config["port"],
            username=config["username"],
            password=config["password"],
        )
        client.auth_log_in()
        logger.debug(f"Connected to qBittorrent at {config['host']}:{config['port']}")
        return client
    except qbittorrentapi.LoginFailed as e:
        logger.error(f"qBittorrent login failed: {e}")
        return None
    except qbittorrentapi.APIConnectionError as e:
        logger.error(f"qBittorrent connection error: {e}")
        return None


def is_available():
    """
    Check if qBittorrent is reachable.
    """
    client = connect()
    if client:
        client.auth_log_out()
        return True
    return False


def add_torrent(client, magnet, category=None):
    """
    Add magnet link to qBittorrent client.
    Returns True on success, False on failure.
    """
    if category is None:
        category = get_config()["category"]

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


def add_torrents(magnets):
    """
    Add multiple magnet links to qBittorrent.
    Returns tuple of (success_count, fail_count).
    """
    if not magnets:
        return 0, 0

    client = connect()
    if not client:
        logger.warning("Cannot add torrents: qBittorrent unavailable")
        return 0, len(magnets)

    success_count = 0
    fail_count = 0

    for magnet in magnets:
        if add_torrent(client, magnet):
            success_count += 1
        else:
            fail_count += 1

    client.auth_log_out()
    return success_count, fail_count

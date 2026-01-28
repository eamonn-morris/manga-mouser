"""qBittorrent download client implementation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import qbittorrentapi

from models import TorrentStatus

if TYPE_CHECKING:
    from config import Config

logger = logging.getLogger("mangamouser")


class QBittorrentDownloader:
    """qBittorrent download client."""

    def __init__(self, config: Config) -> None:
        """
        Initialize the qBittorrent downloader.

        Args:
            config: Application configuration with qBittorrent settings.
        """
        self.config = config
        self._qb = config.qbittorrent

    def _connect(self) -> qbittorrentapi.Client | None:
        """
        Authenticate with qBittorrent and return client instance.
        Returns None if connection fails.
        """
        try:
            client = qbittorrentapi.Client(
                host=self._qb.host,
                port=self._qb.port,
                username=self._qb.username,
                password=self._qb.password,
            )
            client.auth_log_in()
            logger.debug(f"Connected to qBittorrent at {self._qb.host}:{self._qb.port}")
            return client
        except qbittorrentapi.LoginFailed:
            logger.exception("qBittorrent login failed")
            return None
        except qbittorrentapi.APIConnectionError:
            logger.exception("qBittorrent connection error")
            return None

    def is_available(self) -> bool:
        """Check if qBittorrent is reachable."""
        client = self._connect()
        if client:
            client.auth_log_out()
            return True
        return False

    def add_torrent(self, magnet: str) -> bool:
        """
        Add a magnet link to qBittorrent.

        Args:
            magnet: The magnet link to add.

        Returns:
            True if the torrent was added successfully, False otherwise.
        """
        client = self._connect()
        if not client:
            logger.warning("Cannot add torrent: qBittorrent unavailable")
            return False

        try:
            result = client.torrents_add(urls=magnet, category=self._qb.category)
            client.auth_log_out()
            if result == "Ok.":
                logger.debug(f"Added torrent to qBittorrent: {magnet[:60]}...")
                return True
            else:
                logger.warning(f"qBittorrent returned unexpected result: {result}")
                return False
        except Exception:
            logger.exception("Failed to add torrent")
            client.auth_log_out()
            return False

    def add_torrents(self, magnets: list[str]) -> tuple[int, int]:
        """
        Add multiple magnet links to qBittorrent.

        Args:
            magnets: List of magnet links to add.

        Returns:
            Tuple of (success_count, fail_count).
        """
        if not magnets:
            return 0, 0

        client = self._connect()
        if not client:
            logger.warning("Cannot add torrents: qBittorrent unavailable")
            return 0, len(magnets)

        success_count = 0
        fail_count = 0

        for magnet in magnets:
            try:
                result = client.torrents_add(urls=magnet, category=self._qb.category)
                if result == "Ok.":
                    logger.debug(f"Added torrent to qBittorrent: {magnet[:60]}...")
                    success_count += 1
                else:
                    logger.warning(f"qBittorrent returned unexpected result: {result}")
                    fail_count += 1
            except Exception:
                logger.exception("Failed to add torrent")
                fail_count += 1

        client.auth_log_out()
        return success_count, fail_count

    def get_torrent_status(
        self, infohashes: list[str]
    ) -> dict[str, TorrentStatus] | None:
        """
        Get the status of torrents by infohash.

        Args:
            infohashes: List of infohashes to query.

        Returns:
            Dict mapping infohash to TorrentStatus, or None if unavailable.
        """
        if not infohashes:
            return {}

        client = self._connect()
        if not client:
            logger.warning("Cannot get torrent status: qBittorrent unavailable")
            return None

        # Normalize infohashes to lowercase for comparison
        hash_set = {h.lower() for h in infohashes}

        try:
            torrents = client.torrents_info()
            results: dict[str, TorrentStatus] = {}
            for torrent in torrents:
                torrent_hash = torrent.hash.lower()
                if torrent_hash in hash_set:
                    results[torrent_hash] = TorrentStatus(
                        state=torrent.state,
                        progress=torrent.progress,
                        name=torrent.name,
                        size=torrent.size,
                        downloaded=torrent.downloaded,
                        uploaded=torrent.uploaded,
                        ratio=torrent.ratio,
                    )
            client.auth_log_out()
            return results
        except Exception:
            logger.exception("Failed to get torrent status")
            client.auth_log_out()
            return None

    def get_torrent_status_dicts(self, infohashes: list[str]) -> dict[str, dict] | None:
        """
        Get the status of torrents by infohash as dictionaries.

        This is a compatibility method that returns dicts instead of TorrentStatus objects.

        Args:
            infohashes: List of infohashes to query.

        Returns:
            Dict mapping infohash to status dict, or None if unavailable.
        """
        status_map = self.get_torrent_status(infohashes)
        if status_map is None:
            return None

        return {
            h: {
                "state": s.state,
                "progress": s.progress,
                "name": s.name,
                "size": s.size,
                "downloaded": s.downloaded,
                "uploaded": s.uploaded,
                "ratio": s.ratio,
            }
            for h, s in status_map.items()
        }

    def get_all_torrents(self) -> list[dict] | None:
        """
        Get all torrents from qBittorrent in the configured category.

        Returns:
            List of torrent status dicts or None if connection fails.
        """
        client = self._connect()
        if not client:
            logger.warning("Cannot get torrents: qBittorrent unavailable")
            return None

        try:
            torrents = client.torrents_info(category=self._qb.category)
            results = []
            for torrent in torrents:
                results.append(
                    {
                        "hash": torrent.hash.lower(),
                        "state": torrent.state,
                        "progress": torrent.progress,
                        "name": torrent.name,
                        "size": torrent.size,
                        "downloaded": torrent.downloaded,
                        "uploaded": torrent.uploaded,
                        "ratio": torrent.ratio,
                    }
                )
            client.auth_log_out()
            return results
        except Exception:
            logger.exception("Failed to get torrents")
            client.auth_log_out()
            return None

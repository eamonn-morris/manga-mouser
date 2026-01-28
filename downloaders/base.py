"""Base protocol for download clients."""

from typing import Protocol

from models import TorrentStatus


class Downloader(Protocol):
    """Protocol for torrent download clients."""

    def is_available(self) -> bool:
        """
        Check if the download client is reachable.

        Returns:
            True if the client is available, False otherwise.
        """
        ...

    def add_torrent(self, magnet: str) -> bool:
        """
        Add a magnet link to the download client.

        Args:
            magnet: The magnet link to add.

        Returns:
            True if the torrent was added successfully, False otherwise.
        """
        ...

    def add_torrents(self, magnets: list[str]) -> tuple[int, int]:
        """
        Add multiple magnet links to the download client.

        Args:
            magnets: List of magnet links to add.

        Returns:
            Tuple of (success_count, fail_count).
        """
        ...

    def get_torrent_status(self, infohashes: list[str]) -> dict[str, TorrentStatus] | None:
        """
        Get the status of torrents by infohash.

        Args:
            infohashes: List of infohashes to query.

        Returns:
            Dict mapping infohash to TorrentStatus, or None if unavailable.
        """
        ...

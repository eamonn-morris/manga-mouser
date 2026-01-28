"""
MangaMouser service layer.

Contains the core business logic for RSS monitoring and matching.
"""

import logging
import urllib.parse

from config import Config
from downloaders.qbittorrent import QBittorrentDownloader
from feeds.nyaa import NyaaFeedSource
from models import FeedEntry, Match
import storage
import watchlist as watchlist_module

logger = logging.getLogger("mangamouser")


class MangaMouser:
    """Core service for RSS monitoring and matching."""

    def __init__(self, config: Config) -> None:
        """
        Initialize the MangaMouser service.

        Args:
            config: Application configuration.
        """
        self.config = config
        self.feed_source = NyaaFeedSource(config.feed_url, config.user_agent)
        self.downloader = QBittorrentDownloader(config)

    @staticmethod
    def make_magnet(infohash: str, title: str) -> str:
        """Generate magnet link from infohash and title."""
        return f"magnet:?xt=urn:btih:{infohash}&dn={urllib.parse.quote(title)}"

    @staticmethod
    def match_title(entry_title: str, watchlist: list[str]) -> str | None:
        """
        Check if entry title contains any watchlist title (case-insensitive).

        Returns the matched watchlist title or None.
        """
        entry_title_lower = entry_title.lower()
        for title in watchlist:
            if title.lower() in entry_title_lower:
                return title
        return None

    def filter_and_match(
        self, entries: list[FeedEntry], watchlist_titles: list[str]
    ) -> list[Match]:
        """
        Filter entries by category and match against watchlist.

        Returns list of Match objects for entries that matched.
        """
        matches = []

        for entry in entries:
            # Filter by category
            if entry.category != self.config.target_category:
                continue

            # Match against watchlist
            matched_title = self.match_title(entry.title, watchlist_titles)
            if matched_title:
                magnet = self.make_magnet(entry.infohash, entry.title)
                match = Match.from_entry(entry, matched_title, magnet)
                matches.append(match)

        return matches

    def check_feed(self, download: bool = False) -> int:
        """
        Run a single check of the RSS feed.

        Args:
            download: If True, automatically download new matches via qBittorrent.

        Returns:
            The number of new entries saved.
        """
        logger.info("Starting RSS feed check")

        # Load watchlist
        titles = watchlist_module.load()
        logger.debug(f"Watchlist: {titles}")

        # Get feed entries
        feed_entries = self.feed_source.fetch()
        logger.info(f"Total feed entries: {len(feed_entries)}")

        # Filter and match
        matches = self.filter_and_match(feed_entries, titles)
        logger.info(f"Matched entries: {len(matches)}")

        # Convert to dicts for storage (maintaining backward compatibility)
        match_dicts = [m.to_dict() for m in matches]

        # Get seen hashes to identify new matches
        seen_hashes = storage.load_seen_hashes(self.config.matches_file)
        new_matches = [m for m in matches if m.infohash not in seen_hashes]

        # Save matches (with deduplication)
        new_count = storage.save_matches(self.config.matches_file, match_dicts)
        logger.info(f"New entries saved: {new_count}")

        # Log matched entries
        if matches:
            logger.debug("Matched entries:")
            for match in matches:
                logger.debug(f"  - {match.title}")
                logger.debug(f"    Matched: {match.matched_title}")
                logger.debug(f"    Magnet: {match.magnet}")

        # Send new matches to qBittorrent if download enabled
        if download and new_matches:
            magnets = [m.magnet for m in new_matches]
            logger.info(f"Adding {len(magnets)} torrent(s) to qBittorrent")
            success, fail = self.downloader.add_torrents(magnets)
            logger.info(f"qBittorrent: {success} added, {fail} failed")

        return new_count

    def sync_download_status(self) -> int:
        """
        Sync download status from qBittorrent to storage.

        Returns:
            Number of matches updated, or -1 if connection failed.
        """
        matches = storage.load_all_matches(self.config.matches_file)
        if not matches:
            return 0

        infohashes = [m.get("infohash") for m in matches if m.get("infohash")]
        status_map = self.downloader.get_torrent_status_dicts(infohashes)

        if status_map is None:
            return -1

        return storage.update_all_statuses(self.config.status_file, status_map)

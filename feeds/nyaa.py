"""Nyaa.si RSS feed source."""

import logging

import feedparser

from exceptions import FeedError
from models import FeedEntry

logger = logging.getLogger("mangamouser")


class NyaaFeedSource:
    """Fetches entries from Nyaa.si RSS feed."""

    def __init__(self, url: str, user_agent: str = "MangaMouser/1.0") -> None:
        """
        Initialize the Nyaa feed source.

        Args:
            url: The RSS feed URL.
            user_agent: User agent string for requests.
        """
        self.url = url
        self.user_agent = user_agent

    def fetch(self) -> list[FeedEntry]:
        """
        Fetch entries from the Nyaa RSS feed.

        Returns:
            List of FeedEntry objects from the feed.

        Raises:
            FeedError: If feed parsing fails or required fields are missing.
        """
        try:
            feed = feedparser.parse(self.url, agent=self.user_agent)
        except Exception as e:
            logger.exception("Failed to fetch RSS feed")
            raise FeedError(f"Failed to fetch RSS feed: {e}") from e

        if feed.bozo and feed.bozo_exception:
            logger.warning(f"Feed parsing warning: {feed.bozo_exception}")

        entries = []
        for entry in feed.entries:
            title = getattr(entry, "title", None)
            link = getattr(entry, "link", None)
            infohash = getattr(entry, "nyaa_infohash", None)

            if not title or not infohash:
                logger.warning(f"Skipping entry with missing required fields: {entry}")
                continue

            entries.append(
                FeedEntry(
                    title=title,
                    link=link or "",
                    category=getattr(entry, "nyaa_category", None) or "",
                    size=getattr(entry, "nyaa_size", None) or "",
                    infohash=infohash,
                    published=getattr(entry, "published", None) or "",
                    seeders=int(getattr(entry, "nyaa_seeders", 0) or 0),
                )
            )

        return entries

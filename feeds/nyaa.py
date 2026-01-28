"""Nyaa.si RSS feed source."""

import feedparser

from models import FeedEntry


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
        """
        feed = feedparser.parse(self.url, agent=self.user_agent)

        entries = []
        for entry in feed.entries:
            entries.append(
                FeedEntry(
                    title=entry.title,
                    link=entry.link,
                    category=entry.nyaa_category,
                    size=entry.nyaa_size,
                    infohash=entry.nyaa_infohash,
                    published=entry.published,
                    seeders=int(entry.nyaa_seeders),
                )
            )

        return entries

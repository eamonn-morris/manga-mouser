"""Base protocol for feed sources."""

from typing import Protocol

from models import FeedEntry


class FeedSource(Protocol):
    """Protocol for RSS feed sources."""

    def fetch(self) -> list[FeedEntry]:
        """
        Fetch entries from the feed.

        Returns:
            List of FeedEntry objects from the feed.
        """
        ...

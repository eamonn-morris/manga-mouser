"""
Data types for MangaMouser.

Defines typed dataclasses for feed entries, matches, and torrent status.
"""

from dataclasses import dataclass


@dataclass
class FeedEntry:
    """A single entry from an RSS feed."""

    title: str
    link: str
    category: str
    size: str
    infohash: str
    published: str
    seeders: int


@dataclass
class TorrentStatus:
    """Status of a torrent from the download client."""

    state: str
    progress: float  # 0.0 - 1.0
    name: str
    size: int  # bytes
    downloaded: int  # bytes
    uploaded: int  # bytes
    ratio: float


@dataclass
class Match(FeedEntry):
    """A feed entry that matched a watchlist title."""

    matched_title: str = ""
    magnet: str = ""
    download_status: TorrentStatus | None = None

    @classmethod
    def from_entry(cls, entry: FeedEntry, matched_title: str, magnet: str) -> "Match":
        """Create a Match from a FeedEntry."""
        return cls(
            title=entry.title,
            link=entry.link,
            category=entry.category,
            size=entry.size,
            infohash=entry.infohash,
            published=entry.published,
            seeders=entry.seeders,
            matched_title=matched_title,
            magnet=magnet,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "title": self.title,
            "link": self.link,
            "category": self.category,
            "size": self.size,
            "infohash": self.infohash,
            "published": self.published,
            "seeders": self.seeders,
            "matched_title": self.matched_title,
            "magnet": self.magnet,
        }
        if self.download_status:
            result["download_status"] = {
                "state": self.download_status.state,
                "progress": self.download_status.progress,
                "name": self.download_status.name,
                "size": self.download_status.size,
                "downloaded": self.download_status.downloaded,
                "uploaded": self.download_status.uploaded,
                "ratio": self.download_status.ratio,
            }
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Match":
        """Create a Match from a dictionary."""
        status_data = data.get("download_status")
        download_status = None
        if status_data:
            download_status = TorrentStatus(
                state=status_data.get("state", "unknown"),
                progress=status_data.get("progress", 0.0),
                name=status_data.get("name", ""),
                size=status_data.get("size", 0),
                downloaded=status_data.get("downloaded", 0),
                uploaded=status_data.get("uploaded", 0),
                ratio=status_data.get("ratio", 0.0),
            )
        return cls(
            title=data.get("title", ""),
            link=data.get("link", ""),
            category=data.get("category", ""),
            size=data.get("size", ""),
            infohash=data.get("infohash", ""),
            published=data.get("published", ""),
            seeders=data.get("seeders", 0),
            matched_title=data.get("matched_title", ""),
            magnet=data.get("magnet", ""),
            download_status=download_status,
        )

"""
MangaMouser exception hierarchy.

All application exceptions inherit from MangaMouserError.
"""


class MangaMouserError(Exception):
    """Base exception for MangaMouser errors."""

    pass


class ConfigError(MangaMouserError):
    """Configuration is invalid or missing."""

    pass


class FeedError(MangaMouserError):
    """Error fetching or parsing RSS feed."""

    pass


class DownloaderError(MangaMouserError):
    """Error communicating with download client."""

    pass

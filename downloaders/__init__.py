"""Downloader implementations."""

from downloaders.base import Downloader
from downloaders.qbittorrent import QBittorrentDownloader

__all__ = ["Downloader", "QBittorrentDownloader"]

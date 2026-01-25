import argparse
import json
import logging
import os
import signal
import sys
import time
import urllib.parse
from pathlib import Path

import feedparser
from dotenv import load_dotenv

import downloader
import storage

# Base directory for resolving paths relative to script location
BASE_DIR = Path(__file__).parent.resolve()
WATCHLIST_PATH = BASE_DIR / "watchlist.json"
MATCHES_FILE = BASE_DIR / "downloads" / "matches.jsonl"
LOG_FILE = BASE_DIR / "downloads" / "mouser.log"

# load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

user_agent = "MangaMouser/1.0"
FEED_URL = os.getenv("FEED_URL")
TARGET_CATEGORY = "Literature - English-translated"

# Global flag for graceful shutdown
shutdown_requested = False
logger = logging.getLogger("mangamouser")


def setup_logging(verbose=False):
    """
    Configure logging to stdout and file.
    """
    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

    # Create downloads directory if needed for log file
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # Stream handler (stdout)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    # Configure root logger
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


def signal_handler(signum, frame):
    """
    Handle SIGINT/SIGTERM for graceful shutdown.
    """
    global shutdown_requested
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name}, shutting down gracefully...")
    shutdown_requested = True


def make_magnet(infohash, title):
    """
    Generate magnet link from infohash and title.
    """
    return f"magnet:?xt=urn:btih:{infohash}&dn={urllib.parse.quote(title)}"


def load_watchlist(filepath=WATCHLIST_PATH):
    """
    Load watchlist titles from JSON file.
    """
    with open(filepath, "r") as f:
        return json.load(f)


def match_title(entry_title, watchlist):
    """
    Check if entry title contains any watchlist title (case-insensitive).
    Returns the matched watchlist title or None.
    """
    entry_title_lower = entry_title.lower()
    for title in watchlist:
        if title.lower() in entry_title_lower:
            return title
    return None


def get_feed_entries(rss_url):
    """
    Returns list of RSS feed entries with all relevant fields.
    """
    manga_feed = feedparser.parse(rss_url, agent=user_agent)
    feed_entries = manga_feed.entries

    entry_list = []

    for entry in feed_entries:
        temp = {
            "title": entry.title,
            "link": entry.link,
            "category": entry.nyaa_category,
            "size": entry.nyaa_size,
            "infohash": entry.nyaa_infohash,
            "published": entry.published,
            "seeders": entry.nyaa_seeders,
        }
        entry_list.append(temp)

    return entry_list


def filter_and_match(entries, watchlist, category=TARGET_CATEGORY):
    """
    Filter entries by category and match against watchlist.
    Returns list of matched entries with matched_title and magnet fields added.
    """
    matches = []

    for entry in entries:
        # Filter by category
        if entry.get("category") != category:
            continue

        # Match against watchlist
        matched_title = match_title(entry.get("title", ""), watchlist)
        if matched_title:
            entry["matched_title"] = matched_title
            # Add magnet link
            entry["magnet"] = make_magnet(entry["infohash"], entry["title"])
            matches.append(entry)

    return matches


def run_once(download=False):
    """
    Run a single check of the RSS feed.
    Returns the number of new entries saved.
    """
    logger.info("Starting RSS feed check")

    # Load watchlist
    watchlist = load_watchlist()
    logger.debug(f"Watchlist: {watchlist}")

    # Get feed entries
    feed_entries = get_feed_entries(rss_url=FEED_URL)
    logger.info(f"Total feed entries: {len(feed_entries)}")

    # Filter and match
    matches = filter_and_match(feed_entries, watchlist)
    logger.info(f"Matched entries: {len(matches)}")

    # Get seen hashes to identify new matches
    seen_hashes = storage.load_seen_hashes(MATCHES_FILE)
    new_matches = [m for m in matches if m.get("infohash") not in seen_hashes]

    # Save matches (with deduplication)
    new_count = storage.save_matches(MATCHES_FILE, matches)
    logger.info(f"New entries saved: {new_count}")

    # Log matched entries
    if matches:
        logger.debug("Matched entries:")
        for match in matches:
            logger.debug(f"  - {match['title']}")
            logger.debug(f"    Matched: {match['matched_title']}")
            logger.debug(f"    Magnet: {match['magnet']}")

    # Send new matches to qBittorrent if download enabled
    if download and new_matches:
        magnets = [m["magnet"] for m in new_matches]
        logger.info(f"Adding {len(magnets)} torrent(s) to qBittorrent")
        success, fail = downloader.add_torrents(magnets)
        logger.info(f"qBittorrent: {success} added, {fail} failed")

    return new_count


def run_daemon(interval, download=False):
    """
    Run continuously, polling at the specified interval.
    """
    logger.info(f"Starting daemon mode with {interval}s interval")

    while not shutdown_requested:
        try:
            run_once(download=download)
        except Exception as e:
            logger.error(f"Error during feed check: {e}")

        # Sleep in small increments to check for shutdown
        elapsed = 0
        while elapsed < interval and not shutdown_requested:
            time.sleep(1)
            elapsed += 1

    logger.info("Daemon shutdown complete")


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="MangaMouser RSS Monitor - Watch for manga releases"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        default=True,
        help="Run once and exit (default behavior)",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously with polling",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        metavar="N",
        help="Polling interval in seconds (default: 300 = 5 min)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Auto-download matched torrents via qBittorrent",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose)

    logger.info("MangaMouser RSS Monitor")

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.daemon:
        run_daemon(args.interval, download=args.download)
    else:
        run_once(download=args.download)


if __name__ == "__main__":
    main()

import argparse
import json
import logging
import signal
import sys
import time
import urllib.parse

import feedparser

import downloader
import storage
import watchlist
from config import Config, ConfigError, load_config

# Global state
shutdown_requested = False
logger = logging.getLogger("mangamouser")

# Global config - initialized in main()
_config: Config | None = None


def setup_logging(config: Config, verbose: bool = False) -> None:
    """
    Configure logging to stdout and file.
    """
    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

    # Create downloads directory if needed for log file
    config.log_file.parent.mkdir(parents=True, exist_ok=True)

    # File handler
    file_handler = logging.FileHandler(config.log_file)
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


def get_feed_entries(rss_url: str, user_agent: str) -> list[dict]:
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


def filter_and_match(entries: list[dict], watchlist_titles: list[str], category: str) -> list[dict]:
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
        matched_title = match_title(entry.get("title", ""), watchlist_titles)
        if matched_title:
            entry["matched_title"] = matched_title
            # Add magnet link
            entry["magnet"] = make_magnet(entry["infohash"], entry["title"])
            matches.append(entry)

    return matches


def run_once(config: Config, download: bool = False) -> int:
    """
    Run a single check of the RSS feed.
    Returns the number of new entries saved.
    """
    logger.info("Starting RSS feed check")

    # Load watchlist
    titles = watchlist.load()
    logger.debug(f"Watchlist: {titles}")

    # Get feed entries
    feed_entries = get_feed_entries(config.feed_url, config.user_agent)
    logger.info(f"Total feed entries: {len(feed_entries)}")

    # Filter and match
    matches = filter_and_match(feed_entries, titles, config.target_category)
    logger.info(f"Matched entries: {len(matches)}")

    # Get seen hashes to identify new matches
    seen_hashes = storage.load_seen_hashes(config.matches_file)
    new_matches = [m for m in matches if m.get("infohash") not in seen_hashes]

    # Save matches (with deduplication)
    new_count = storage.save_matches(config.matches_file, matches)
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
        success, fail = downloader.add_torrents(magnets, config)
        logger.info(f"qBittorrent: {success} added, {fail} failed")

    return new_count


def run_daemon(config: Config, interval: int, download: bool = False) -> None:
    """
    Run continuously, polling at the specified interval.
    """
    logger.info(f"Starting daemon mode with {interval}s interval")

    while not shutdown_requested:
        try:
            run_once(config, download=download)
        except Exception:
            logger.exception("Error during feed check")

        # Sleep in small increments to check for shutdown
        elapsed = 0
        while elapsed < interval and not shutdown_requested:
            time.sleep(1)
            elapsed += 1

    logger.info("Daemon shutdown complete")


def cmd_watchlist_list(args):
    """Handle watchlist list command."""
    titles = watchlist.list_all()
    if not titles:
        print("Watchlist is empty")
        return
    print(f"Watchlist ({len(titles)} titles):")
    for title in titles:
        print(f"  - {title}")


def cmd_watchlist_add(args):
    """Handle watchlist add command."""
    title = args.title
    if watchlist.add(title):
        print(f"Added: {title}")
    else:
        print(f"Already exists: {title}")


def cmd_watchlist_remove(args):
    """Handle watchlist remove command."""
    title = args.title
    if watchlist.remove(title):
        print(f"Removed: {title}")
    else:
        print(f"Not found: {title}")


def cmd_run(args, config: Config) -> None:
    """Handle run command (default behavior)."""
    setup_logging(config, verbose=args.verbose)
    logger.info("MangaMouser RSS Monitor")

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.daemon:
        run_daemon(config, args.interval, download=args.download)
    else:
        run_once(config, download=args.download)


def format_size(size_bytes):
    """Format bytes as human-readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_state(state):
    """Format qBittorrent state to human-readable string."""
    state_map = {
        "downloading": "Downloading",
        "uploading": "Seeding",
        "stalledDL": "Stalled (DL)",
        "stalledUP": "Stalled (UP)",
        "pausedDL": "Paused (DL)",
        "pausedUP": "Paused (UP)",
        "queuedDL": "Queued (DL)",
        "queuedUP": "Queued (UP)",
        "checkingDL": "Checking",
        "checkingUP": "Checking",
        "forcedDL": "Forced DL",
        "forcedUP": "Forced UP",
        "missingFiles": "Missing",
        "error": "Error",
        "moving": "Moving",
        "unknown": "Unknown",
    }
    return state_map.get(state, state)


def is_active_state(state):
    """Check if torrent state is active (downloading or seeding)."""
    return state in ["downloading", "uploading", "forcedDL", "forcedUP", "stalledDL", "stalledUP"]


def is_completed_state(state):
    """Check if torrent state indicates completion."""
    return state in ["uploading", "pausedUP", "queuedUP", "stalledUP", "forcedUP"]


def cmd_downloads_list(args, config: Config) -> None:
    """Handle downloads list command."""
    matches = storage.load_all_matches(config.matches_file)

    if not matches:
        print("No tracked downloads")
        return

    # Get current status from qBittorrent
    infohashes = [m.get("infohash") for m in matches if m.get("infohash")]
    status_map = downloader.get_torrent_status(infohashes, config)

    # Merge status into matches
    if status_map:
        for match in matches:
            infohash = match.get("infohash", "").lower()
            if infohash in status_map:
                match["download_status"] = status_map[infohash]

    # Filter by state if requested (use getattr for optional args)
    if getattr(args, "active", False):
        matches = [m for m in matches if is_active_state(m.get("download_status", {}).get("state", ""))]
    elif getattr(args, "completed", False):
        matches = [m for m in matches if is_completed_state(m.get("download_status", {}).get("state", ""))]

    if not matches:
        print("No matching downloads")
        return

    # Output format
    if getattr(args, "json", False):
        print(json.dumps(matches, indent=2))
    else:
        # Table format
        print(f"Downloads ({len(matches)} entries):")
        print("-" * 80)
        for match in matches:
            title = match.get("matched_title", "Unknown")
            full_title = match.get("title", "")
            status = match.get("download_status", {})
            state = format_state(status.get("state", "unknown"))
            progress = status.get("progress", 0) * 100
            size = format_size(status.get("size", 0))

            print(f"  {title}")
            print(f"    {full_title[:60]}...")
            print(f"    State: {state} | Progress: {progress:.1f}% | Size: {size}")
            print()


def cmd_downloads_sync(args, config: Config) -> None:
    """Handle downloads sync command."""
    matches = storage.load_all_matches(config.matches_file)

    if not matches:
        print("No tracked downloads to sync")
        return

    infohashes = [m.get("infohash") for m in matches if m.get("infohash")]
    status_map = downloader.get_torrent_status(infohashes, config)

    if status_map is None:
        print("Failed to connect to qBittorrent")
        return

    updated = storage.update_all_statuses(config.matches_file, status_map)
    print(f"Synced {updated} download(s) from qBittorrent")


def parse_args():
    """
    Parse command line arguments with subcommand support.
    """
    parser = argparse.ArgumentParser(
        description="MangaMouser RSS Monitor - Watch for manga releases"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )

    subparsers = parser.add_subparsers(dest="command")

    # Run subcommand (also default behavior)
    run_parser = subparsers.add_parser("run", help="Run RSS monitor")
    run_parser.add_argument(
        "--once",
        action="store_true",
        default=True,
        help="Run once and exit (default behavior)",
    )
    run_parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously with polling",
    )
    run_parser.add_argument(
        "--interval",
        type=int,
        default=300,
        metavar="N",
        help="Polling interval in seconds (default: 300 = 5 min)",
    )
    run_parser.add_argument(
        "--download",
        action="store_true",
        help="Auto-download matched torrents via qBittorrent",
    )

    # Watchlist subcommand
    watchlist_parser = subparsers.add_parser("watchlist", help="Manage watchlist")
    watchlist_subparsers = watchlist_parser.add_subparsers(dest="watchlist_command")

    # watchlist list
    watchlist_subparsers.add_parser("list", help="List all watchlist titles")

    # watchlist add
    add_parser = watchlist_subparsers.add_parser("add", help="Add title to watchlist")
    add_parser.add_argument("title", help="Title to add")

    # watchlist remove
    remove_parser = watchlist_subparsers.add_parser(
        "remove", help="Remove title from watchlist"
    )
    remove_parser.add_argument("title", help="Title to remove")

    # Downloads subcommand
    downloads_parser = subparsers.add_parser("downloads", help="Manage downloads")
    downloads_subparsers = downloads_parser.add_subparsers(dest="downloads_command")

    # downloads list
    list_parser = downloads_subparsers.add_parser("list", help="List tracked downloads")
    list_parser.add_argument(
        "--active",
        action="store_true",
        help="Only show active downloads (downloading/seeding)",
    )
    list_parser.add_argument(
        "--completed",
        action="store_true",
        help="Only show completed downloads",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON for scripting",
    )

    # downloads sync
    downloads_subparsers.add_parser("sync", help="Sync download status from qBittorrent")

    # Legacy flags on main parser for backward compatibility
    parser.add_argument(
        "--once",
        action="store_true",
        default=True,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        metavar="N",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Load config - required for most commands
    # Watchlist commands don't need full config (no FEED_URL required)
    config = None
    needs_config = args.command not in ("watchlist",) or args.command is None

    if needs_config:
        try:
            config = load_config()
        except ConfigError as e:
            print(f"Configuration error: {e}", file=sys.stderr)
            sys.exit(1)

    # Handle subcommands
    if args.command == "watchlist":
        if args.watchlist_command == "list":
            cmd_watchlist_list(args)
        elif args.watchlist_command == "add":
            cmd_watchlist_add(args)
        elif args.watchlist_command == "remove":
            cmd_watchlist_remove(args)
        else:
            # Default to list if no watchlist subcommand
            cmd_watchlist_list(args)
    elif args.command == "downloads":
        assert config is not None  # Config loaded above for downloads command
        if args.downloads_command == "list":
            cmd_downloads_list(args, config)
        elif args.downloads_command == "sync":
            cmd_downloads_sync(args, config)
        else:
            # Default to list if no downloads subcommand
            cmd_downloads_list(args, config)
    elif args.command == "run":
        assert config is not None  # Config loaded above for run command
        cmd_run(args, config)
    else:
        # Default behavior (no subcommand) - run RSS monitor
        assert config is not None  # Config loaded above for default run
        cmd_run(args, config)


if __name__ == "__main__":
    main()

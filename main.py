"""
MangaMouser CLI - RSS monitor for manga releases.

This module contains only CLI parsing and command handlers.
Business logic is in service.py.
"""

import argparse
import json
import logging
import signal
import sys
import time

from config import Config, load_config
from exceptions import MangaMouserError
from formatting import format_size, format_state, is_active_state, is_completed_state
from service import MangaMouser
import storage
import watchlist

# Global state for signal handling
shutdown_requested = False
logger = logging.getLogger("mangamouser")


def setup_logging(config: Config, verbose: bool = False) -> None:
    """Configure logging to stdout and file."""
    if logger.handlers:
        return

    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

    config.log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(config.log_file)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


def signal_handler(signum: int, frame) -> None:
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global shutdown_requested
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name}, shutting down gracefully...")
    shutdown_requested = True


def run_daemon(service: MangaMouser, interval: int, download: bool = False) -> None:
    """Run continuously, polling at the specified interval."""
    logger.info(f"Starting daemon mode with {interval}s interval")

    while not shutdown_requested:
        try:
            service.check_feed(download=download)
        except Exception:
            logger.exception("Error during feed check")

        elapsed = 0
        while elapsed < interval and not shutdown_requested:
            time.sleep(1)
            elapsed += 1

    logger.info("Daemon shutdown complete")


# --- Command Handlers ---


def cmd_run(args, config: Config) -> None:
    """Handle run command."""
    setup_logging(config, verbose=args.verbose)
    logger.info("MangaMouser RSS Monitor")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    service = MangaMouser(config)

    if args.daemon:
        run_daemon(service, args.interval, download=args.download)
    else:
        service.check_feed(download=args.download)


def cmd_watchlist_list(args) -> None:
    """Handle watchlist list command."""
    titles = watchlist.list_all()
    if not titles:
        print("Watchlist is empty")
        return
    print(f"Watchlist ({len(titles)} titles):")
    for title in titles:
        print(f"  - {title}")


def cmd_watchlist_add(args) -> None:
    """Handle watchlist add command."""
    if watchlist.add(args.title):
        print(f"Added: {args.title}")
    else:
        print(f"Already exists: {args.title}")


def cmd_watchlist_remove(args) -> None:
    """Handle watchlist remove command."""
    if watchlist.remove(args.title):
        print(f"Removed: {args.title}")
    else:
        print(f"Not found: {args.title}")


def cmd_downloads_list(args, config: Config) -> None:
    """Handle downloads list command."""
    matches = storage.load_all_matches(config.matches_file)

    if not matches:
        print("No tracked downloads")
        return

    # Merge stored status into matches
    matches = storage.get_status_for_matches(config.status_file, matches)

    # Filter by state
    if getattr(args, "active", False):
        matches = [
            m
            for m in matches
            if is_active_state(m.get("download_status", {}).get("state", ""))
        ]
    elif getattr(args, "completed", False):
        matches = [
            m
            for m in matches
            if is_completed_state(m.get("download_status", {}).get("state", ""))
        ]

    if not matches:
        print("No matching downloads")
        return

    # Output format
    if getattr(args, "json", False):
        print(json.dumps(matches, indent=2))
    else:
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
    service = MangaMouser(config)
    updated = service.sync_download_status()

    if updated == -1:
        print("Failed to connect to qBittorrent")
    elif updated == 0:
        print("No tracked downloads to sync")
    else:
        print(f"Synced {updated} download(s) from qBittorrent")


# --- CLI Parsing ---


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MangaMouser RSS Monitor - Watch for manga releases"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable DEBUG logging"
    )

    subparsers = parser.add_subparsers(dest="command")

    # Run subcommand
    run_parser = subparsers.add_parser("run", help="Run RSS monitor")
    run_parser.add_argument(
        "--daemon", action="store_true", help="Run continuously with polling"
    )
    run_parser.add_argument(
        "--interval",
        type=int,
        default=300,
        metavar="N",
        help="Polling interval in seconds (default: 300)",
    )
    run_parser.add_argument(
        "--download",
        action="store_true",
        help="Auto-download matched torrents via qBittorrent",
    )

    # Watchlist subcommand
    watchlist_parser = subparsers.add_parser("watchlist", help="Manage watchlist")
    watchlist_sub = watchlist_parser.add_subparsers(dest="watchlist_command")
    watchlist_sub.add_parser("list", help="List all watchlist titles")
    add_parser = watchlist_sub.add_parser("add", help="Add title to watchlist")
    add_parser.add_argument("title", help="Title to add")
    remove_parser = watchlist_sub.add_parser(
        "remove", help="Remove title from watchlist"
    )
    remove_parser.add_argument("title", help="Title to remove")

    # Downloads subcommand
    downloads_parser = subparsers.add_parser("downloads", help="Manage downloads")
    downloads_sub = downloads_parser.add_subparsers(dest="downloads_command")
    list_parser = downloads_sub.add_parser("list", help="List tracked downloads")
    list_parser.add_argument(
        "--active", action="store_true", help="Only show active downloads"
    )
    list_parser.add_argument(
        "--completed", action="store_true", help="Only show completed downloads"
    )
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    downloads_sub.add_parser("sync", help="Sync download status from qBittorrent")

    # Legacy flags for backward compatibility
    parser.add_argument("--daemon", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--interval", type=int, default=300, metavar="N", help=argparse.SUPPRESS
    )
    parser.add_argument("--download", action="store_true", help=argparse.SUPPRESS)

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    try:
        args = parse_args()

        # Watchlist commands don't need config
        if args.command == "watchlist":
            if args.watchlist_command == "add":
                cmd_watchlist_add(args)
            elif args.watchlist_command == "remove":
                cmd_watchlist_remove(args)
            else:
                cmd_watchlist_list(args)
            return

        # All other commands need config
        config = load_config()

        if args.command == "downloads":
            if args.downloads_command == "sync":
                cmd_downloads_sync(args, config)
            else:
                cmd_downloads_list(args, config)
        else:
            cmd_run(args, config)

    except MangaMouserError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

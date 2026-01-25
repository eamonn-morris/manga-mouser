import json
import os

import feedparser
from dotenv import load_dotenv

import storage

# load environment variables from .env file
load_dotenv()

user_agent = "MangaMouser/1.0"
FEED_URL = os.getenv("FEED_URL")
MATCHES_FILE = "downloads/matches.jsonl"
TARGET_CATEGORY = "Literature - English-translated"


def load_watchlist(filepath="watchlist.json"):
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
    Returns list of matched entries with matched_title field added.
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
            matches.append(entry)

    return matches


def main():
    print("MangaMouser RSS Monitor")
    print("-" * 40)

    # Load watchlist
    watchlist = load_watchlist()
    print(f"Watchlist: {watchlist}")

    # Get feed entries
    feed_entries = get_feed_entries(rss_url=FEED_URL)
    print(f"Total feed entries: {len(feed_entries)}")

    # Filter and match
    matches = filter_and_match(feed_entries, watchlist)
    print(f"Matched entries: {len(matches)}")

    # Save matches (with deduplication)
    new_count = storage.save_matches(MATCHES_FILE, matches)
    print(f"New entries saved: {new_count}")

    # Print matched entries
    if matches:
        print("\nMatched entries:")
        for match in matches:
            print(f"  - {match['title']}")
            print(f"    Matched: {match['matched_title']}")
            print(f"    Link: {match['link']}")


if __name__ == "__main__":
    main()

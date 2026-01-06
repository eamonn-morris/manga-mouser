import json
import os

import feedparser
from dotenv import load_dotenv

# load environment variables from .env file
load_dotenv()

user_agent = "MangaMouser/1.0"
FEED_URL = os.getenv("FEED_URL")


# manga_feed = feedparser.parse(FEED_URL, agent=user_agent)
def get_feed_entries(rss_url):
    """
    returns dictionary of rss feed entries
    """
    manga_feed = feedparser.parse(rss_url, agent=user_agent)
    feed_entries = manga_feed.entries

    entry_list = []

    for entry in feed_entries:
        temp = dict()

        temp["title"] = entry.title
        temp["link"] = entry.link
        temp["category"] = entry.nyaa_category

        entry_list.append(temp)

    return entry_list


def main():
    print("Hello from MangaMouser!")
    feed_entries = get_feed_entries(rss_url=FEED_URL)
    print(json.dumps(feed_entries, indent=2))
    print(f"New Entries Found: {len(feed_entries)}")


if __name__ == "__main__":
    main()

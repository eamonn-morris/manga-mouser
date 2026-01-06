import json
import os

import feedparser
from dotenv import load_dotenv

# load environment variables from .env file
load_dotenv()

user_agent = "MangaMouser/1.0"
FEED_URL = os.getenv("FEED_URL")

manga_feed = feedparser.parse(FEED_URL, agent=user_agent)


def main():
    print(manga_feed.feed.title)  # pyright: ignore[reportAttributeAccessIssue]
    print("Hello from MangaMouser!")
    print(json.dumps(manga_feed.entries, indent=2))


if __name__ == "__main__":
    main()

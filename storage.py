import json
import os


def load_seen_links(filepath):
    """
    Load set of already-seen links for deduplication.
    Returns empty set if file doesn't exist.
    """
    seen_links = set()
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    seen_links.add(entry.get("link"))
    return seen_links


def append_match(filepath, match_dict):
    """
    Append single match to JSONL file.
    Creates directory if it doesn't exist.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "a") as f:
        f.write(json.dumps(match_dict) + "\n")


def save_matches(filepath, matches):
    """
    Save list of matches to JSONL file.
    Skips entries that have already been seen.
    """
    seen_links = load_seen_links(filepath)
    new_count = 0

    for match in matches:
        if match.get("link") not in seen_links:
            append_match(filepath, match)
            seen_links.add(match.get("link"))
            new_count += 1

    return new_count

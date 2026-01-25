import json
from pathlib import Path


def load_seen_hashes(filepath):
    """
    Load set of already-seen infohashes for deduplication.
    Returns empty set if file doesn't exist.
    """
    filepath = Path(filepath)
    seen_hashes = set()
    if filepath.exists():
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    infohash = entry.get("infohash")
                    if infohash:
                        seen_hashes.add(infohash)
    return seen_hashes


def append_match(filepath, match_dict):
    """
    Append single match to JSONL file.
    Creates directory if it doesn't exist.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a") as f:
        f.write(json.dumps(match_dict) + "\n")


def save_matches(filepath, matches):
    """
    Save list of matches to JSONL file.
    Skips entries that have already been seen (by infohash).
    """
    seen_hashes = load_seen_hashes(filepath)
    new_count = 0

    for match in matches:
        infohash = match.get("infohash")
        if infohash and infohash not in seen_hashes:
            append_match(filepath, match)
            seen_hashes.add(infohash)
            new_count += 1

    return new_count

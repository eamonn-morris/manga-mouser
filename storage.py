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


def load_all_matches(filepath):
    """
    Load all match entries from JSONL file.
    Returns list of dicts.
    """
    filepath = Path(filepath)
    matches = []
    if filepath.exists():
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    matches.append(json.loads(line))
    return matches


def update_match_status(filepath, infohash, status_dict):
    """
    Update a match entry with download status.
    Rewrites the file with updated entry.
    Returns True if entry was found and updated.
    """
    filepath = Path(filepath)
    matches = load_all_matches(filepath)

    found = False
    infohash_lower = infohash.lower()
    for match in matches:
        if match.get("infohash", "").lower() == infohash_lower:
            match["download_status"] = status_dict
            found = True
            break

    if found:
        # Rewrite file with updated matches
        with open(filepath, "w") as f:
            for match in matches:
                f.write(json.dumps(match) + "\n")

    return found


def update_all_statuses(filepath, status_map):
    """
    Bulk update download status for multiple matches.
    status_map: dict of infohash -> status_dict
    Returns count of updated entries.
    """
    filepath = Path(filepath)
    matches = load_all_matches(filepath)

    # Normalize keys to lowercase
    status_map_lower = {k.lower(): v for k, v in status_map.items()}

    updated = 0
    for match in matches:
        infohash = match.get("infohash", "").lower()
        if infohash in status_map_lower:
            match["download_status"] = status_map_lower[infohash]
            updated += 1

    if updated > 0:
        with open(filepath, "w") as f:
            for match in matches:
                f.write(json.dumps(match) + "\n")

    return updated

import json
import tempfile
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


def _atomic_write_json(filepath: Path, data: dict) -> None:
    """
    Atomically write JSON data to a file using temp file + rename.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=filepath.parent,
        prefix=".status_",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        json.dump(data, tmp, indent=2)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(filepath)


def load_status(status_file) -> dict[str, dict]:
    """
    Load torrent status from the status file.
    Returns dict mapping infohash (lowercase) -> status dict.
    """
    status_file = Path(status_file)
    if not status_file.exists():
        return {}
    with open(status_file, "r") as f:
        return json.load(f)


def save_status(status_file, status_map: dict[str, dict]) -> None:
    """
    Save torrent status to the status file atomically.
    """
    _atomic_write_json(Path(status_file), status_map)


def update_status(status_file, infohash: str, status_dict: dict) -> None:
    """
    Update status for a single torrent.
    """
    status_map = load_status(status_file)
    status_map[infohash.lower()] = status_dict
    save_status(status_file, status_map)


def update_all_statuses(status_file, new_statuses: dict[str, dict]) -> int:
    """
    Bulk update torrent statuses.
    new_statuses: dict of infohash -> status_dict
    Returns count of updated entries.
    """
    status_map = load_status(status_file)

    # Normalize keys to lowercase
    updated = 0
    for infohash, status in new_statuses.items():
        status_map[infohash.lower()] = status
        updated += 1

    if updated > 0:
        save_status(status_file, status_map)

    return updated


def get_status_for_matches(status_file, matches: list[dict]) -> list[dict]:
    """
    Merge status data into match dicts.
    Returns new list with download_status populated from status file.
    """
    status_map = load_status(status_file)
    result = []
    for match in matches:
        match_copy = match.copy()
        infohash = match.get("infohash", "").lower()
        if infohash in status_map:
            match_copy["download_status"] = status_map[infohash]
        result.append(match_copy)
    return result

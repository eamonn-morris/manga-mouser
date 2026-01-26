import json
from pathlib import Path

# Default watchlist path (can be overridden)
_WATCHLIST_PATH = Path(__file__).parent.resolve() / "watchlist.json"


def _get_path() -> Path:
    """Get the watchlist file path."""
    return _WATCHLIST_PATH


def load() -> list[str]:
    """
    Load watchlist titles from storage.
    Returns empty list if file doesn't exist.
    """
    path = _get_path()
    if not path.exists():
        return []
    with open(path, "r") as f:
        return json.load(f)


def save(titles: list[str]) -> None:
    """
    Save titles to watchlist storage.
    """
    path = _get_path()
    with open(path, "w") as f:
        json.dump(titles, f, indent=2)
        f.write("\n")


def add(title: str) -> bool:
    """
    Add a title to the watchlist.
    Returns False if already exists (case-insensitive check).
    """
    titles = load()
    # Case-insensitive check for duplicates
    if any(t.lower() == title.lower() for t in titles):
        return False
    titles.append(title)
    save(titles)
    return True


def remove(title: str) -> bool:
    """
    Remove a title from the watchlist.
    Returns False if not found (case-insensitive match).
    """
    titles = load()
    # Find case-insensitive match
    for i, t in enumerate(titles):
        if t.lower() == title.lower():
            titles.pop(i)
            save(titles)
            return True
    return False


def list_all() -> list[str]:
    """
    Get all titles in the watchlist.
    """
    return load()

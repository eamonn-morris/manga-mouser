"""Display formatting helpers for MangaMouser."""


def format_size(size_bytes: int | float) -> str:
    """Format bytes as human-readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_state(state: str) -> str:
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


def is_active_state(state: str) -> bool:
    """Check if torrent state is active (downloading or seeding)."""
    return state in [
        "downloading",
        "uploading",
        "forcedDL",
        "forcedUP",
        "stalledDL",
        "stalledUP",
    ]


def is_completed_state(state: str) -> bool:
    """Check if torrent state indicates completion."""
    return state in ["uploading", "pausedUP", "queuedUP", "stalledUP", "forcedUP"]

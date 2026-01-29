# MangaMouser

RSS feed monitor for manga releases with automatic download support.

## About

MangaMouser monitors RSS feeds (e.g., Nyaa) for new manga releases matching your watchlist. It can automatically add matched torrents to qBittorrent for downloading.

**Features:**
- Category filtering (English-translated manga)
- Case-insensitive watchlist matching
- Infohash-based deduplication
- Automatic qBittorrent integration
- Daemon mode with configurable polling interval
- Systemd service/timer support

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- qBittorrent with WebUI enabled (optional, for auto-download)

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd manga-feed

# Install dependencies
uv sync

# Copy and configure environment file
cp .env.tpl .env
```

## Configuration

### Environment Variables (`.env`)

```bash
# RSS feed URL (required)
FEED_URL="https://nyaa.si/?page=rss&c=3_1"

# Category filter (optional, defaults to "Literature - English-translated")
TARGET_CATEGORY="Literature - English-translated"

# qBittorrent WebUI settings (required for --download)
QB_HOST=localhost
QB_PORT=8080
QB_USER=admin
QB_PASSWORD=your_password
QB_CATEGORY=manga
```

### Watchlist (`watchlist.json`)

A JSON array of manga titles to watch for. Matching is case-insensitive and uses substring matching.

```json
["Chainsaw Man", "Gachiakuta", "Jujutsu Kaisen", "Tower Dungeon"]
```

Example: A watchlist entry of `"Chainsaw Man"` will match feed entries like:
- `[Digital] Chainsaw Man - Chapter 180 (Viz)`
- `chainsaw man v15`

## Usage

### Basic (one-shot)

Run once and exit:

```bash
uv run main.py
```

### With Auto-Download

Add matched torrents to qBittorrent:

```bash
uv run main.py --download
```

### Daemon Mode

Run continuously with polling:

```bash
# Poll every 5 minutes (default)
uv run main.py --daemon

# Poll every 10 minutes with download enabled
uv run main.py --daemon --interval 600 --download
```

### Verbose Logging

Enable debug output:

```bash
uv run main.py -v
uv run main.py --daemon --verbose
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--once` | Run once and exit (default) |
| `--daemon` | Run continuously with polling |
| `--interval N` | Polling interval in seconds (default: 300) |
| `--download` | Auto-download via qBittorrent |
| `-v, --verbose` | Enable DEBUG logging |

### Watchlist Management

Manage watched titles from the command line:

```bash
# List all watchlist titles
uv run main.py watchlist list

# Add a title to the watchlist
uv run main.py watchlist add "One Piece"

# Remove a title from the watchlist
uv run main.py watchlist remove "One Piece"
```

Titles are matched case-insensitively. Adding a title that already exists (ignoring case) will be rejected.

### Download Management

Track and manage torrent downloads:

```bash
# List all tracked downloads with status
uv run main.py downloads list

# List only active downloads (downloading/seeding)
uv run main.py downloads list --active

# List only completed downloads
uv run main.py downloads list --completed

# Output as JSON for scripting
uv run main.py downloads list --json

# Sync download status from qBittorrent
uv run main.py downloads sync
```

The `sync` command updates stored match records with current download status from qBittorrent.

## Output Files

All output files are stored in the `downloads/` directory:

- `matches.jsonl` - JSONL file of all matched entries (deduplicated by infohash)
- `status.json` - Download status cache from qBittorrent
- `mouser.log` - Application log file

## Deployment (systemd)

Two deployment approaches are provided in `contrib/`:

### Option 1: Daemon Service

A long-running service with built-in polling. Simpler setup but keeps the process running.

1. Edit the service file to set your paths:
   ```bash
   sudo cp contrib/mangamouser.service /etc/systemd/system/
   sudo nano /etc/systemd/system/mangamouser.service
   ```

2. Update `ExecStart` with the correct path and options:
   ```ini
   ExecStart=/usr/bin/uv run /home/youruser/manga-feed/main.py --daemon --download
   ```

3. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now mangamouser.service
   ```

### Option 2: Timer + Oneshot (Recommended)

Uses systemd's timer to trigger periodic runs. More efficient and provides better logging via journald.

1. Copy both files:
   ```bash
   sudo cp contrib/mangamouser-oneshot.service /etc/systemd/system/
   sudo cp contrib/mangamouser.timer /etc/systemd/system/
   sudo nano /etc/systemd/system/mangamouser-oneshot.service
   ```

2. Update `ExecStart` with the correct path:
   ```ini
   ExecStart=/usr/bin/uv run /home/youruser/manga-feed/main.py --download
   ```

3. Enable and start the timer:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now mangamouser.timer
   ```

4. Check timer status:
   ```bash
   systemctl list-timers mangamouser.timer
   ```

### Customizing the Timer Interval

Edit `mangamouser.timer` to change the polling frequency:

```ini
[Timer]
OnBootSec=1min        # First run after boot
OnUnitActiveSec=5min  # Subsequent runs (change this)
```

### Viewing Logs

```bash
# Daemon service
journalctl -u mangamouser.service -f

# Oneshot service
journalctl -u mangamouser-oneshot.service -f
```

## qBittorrent Setup

1. Enable WebUI in qBittorrent: Tools > Options > Web UI
2. Set a username and password
3. Note the port (default: 8080)
4. Configure the `QB_*` variables in `.env`
5. (Optional) Create a "manga" category in qBittorrent for organization

## License

MIT

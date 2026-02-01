"""MangaMouser TUI dashboard application."""

from datetime import datetime
from functools import partial

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Footer, Header, Rule
from textual.worker import Worker, WorkerState

from config import load_config
from service import MangaMouser
import storage
import watchlist as watchlist_module

from tui.widgets import ActivityLog, DownloadsTable, StatusPanel, WatchlistPanel


class MangaMouserDashboard(App):
    """TUI dashboard for MangaMouser."""

    TITLE = "MangaMouser"
    SUB_TITLE = "RSS Monitor Dashboard"
    CSS_PATH = "styles/dashboard.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "sync", "Sync"),
        Binding("c", "check_feed", "Check Feed"),
        Binding("w", "toggle_watchlist", "Watchlist", priority=True),
        Binding("d", "toggle_dark", "Dark Mode"),
    ]

    def __init__(self, feed_check_interval: int = 300):
        """
        Initialize the dashboard.

        Args:
            feed_check_interval: Seconds between automatic feed checks (default 5 min).
                                 Set to 0 to disable automatic feed checks.
        """
        super().__init__()
        self.config = load_config()
        self.service = MangaMouser(self.config)
        self.refresh_interval = 60  # Display refresh interval
        self.feed_check_interval = feed_check_interval  # Feed check interval
        self._last_feed_check: str = "Never"

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main"):
            yield StatusPanel(id="status")
            yield WatchlistPanel(id="watchlist")
            yield Rule()
            yield DownloadsTable(id="downloads")
            yield Rule()
            yield ActivityLog(id="log")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize on app startup."""
        self.log_activity("Dashboard started")
        self.load_data()
        self._schedule_feed_check()

    # --- Background Workers ---

    @work(thread=True, group="data", exclusive=True)
    def load_data(self) -> dict:
        """Load matches and status from storage."""
        matches = storage.load_all_matches(self.config.matches_file)
        matches = storage.get_status_for_matches(self.config.status_file, matches)
        titles = watchlist_module.load()

        active = sum(
            1
            for m in matches
            if m.get("download_status", {}).get("state")
            in ["downloading", "uploading", "stalledDL", "stalledUP"]
        )

        return {
            "matches": matches,
            "count": len(matches),
            "active": active,
            "watchlist": titles,
            "last_feed_check": self._last_feed_check,
        }

    @work(thread=True, group="sync", exclusive=True)
    def sync_downloads(self) -> int:
        """Sync download status from qBittorrent."""
        return self.service.sync_download_status()

    @work(thread=True, group="feed", exclusive=True)
    def check_feed(self) -> int:
        """Check RSS feed for new matches."""
        return self.service.check_feed(download=True)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker completion."""
        if event.state == WorkerState.SUCCESS:
            self._handle_worker_success(event.worker)
        elif event.state == WorkerState.ERROR:
            self.log_activity(f"Error: {event.worker.error}", level="error")

    def _handle_worker_success(self, worker: Worker) -> None:
        """Process successful worker results."""
        if worker.group == "data":
            result = worker.result
            if result is not None:
                self._update_display(result)
            self._schedule_refresh()

        elif worker.group == "sync":
            synced = worker.result
            if synced == -1:
                self.log_activity("Failed to connect to qBittorrent", level="error")
            else:
                self.log_activity(f"Synced {synced} download(s)", level="success")
            self.load_data()

        elif worker.group == "feed":
            new_count = worker.result
            self._last_feed_check = datetime.now().strftime("%H:%M:%S")
            self.log_activity(
                f"Feed check complete: {new_count} new match(es)", level="success"
            )
            self.load_data()

    def _update_display(self, data: dict) -> None:
        """Update UI with loaded data."""
        status = self.query_one("#status", StatusPanel)
        status.match_count = data["count"]
        status.active_downloads = data["active"]
        status.feed_interval = self.feed_check_interval
        if "last_feed_check" in data:
            status.last_feed_check = data["last_feed_check"]

        table = self.query_one("#downloads", DownloadsTable)
        table.update_data(data["matches"])

        watchlist = self.query_one("#watchlist", WatchlistPanel)
        watchlist.update_titles(data["watchlist"])

    def _schedule_refresh(self) -> None:
        """Schedule next automatic refresh."""
        self.set_timer(
            self.refresh_interval,
            partial(self.load_data),
            name="auto_refresh",
        )

    def _schedule_feed_check(self) -> None:
        """Schedule next automatic feed check."""
        if self.feed_check_interval > 0:
            self.set_timer(
                self.feed_check_interval,
                self._auto_check_feed,
                name="auto_feed_check",
            )

    def _auto_check_feed(self) -> None:
        """Run automatic feed check and reschedule."""
        self.log_activity("Auto-checking RSS feed...")
        self.check_feed()
        self._schedule_feed_check()

    # --- Actions ---

    def action_refresh(self) -> None:
        """Manual refresh."""
        self.log_activity("Refreshing data...")
        self.load_data()

    def action_sync(self) -> None:
        """Sync with qBittorrent."""
        self.log_activity("Syncing with qBittorrent...")
        self.sync_downloads()

    def action_check_feed(self) -> None:
        """Check RSS feed."""
        self.log_activity("Checking RSS feed...")
        self.check_feed()

    def action_toggle_watchlist(self) -> None:
        """Toggle watchlist panel visibility."""
        try:
            watchlist = self.query_one("#watchlist", WatchlistPanel)
            watchlist.toggle()
            state = "collapsed" if watchlist.collapsed else "expanded"
            self.log_activity(f"Watchlist {state}")
        except Exception as e:
            self.log_activity(f"Toggle error: {e}", level="error")

    # --- Event Handlers ---

    def on_watchlist_panel_title_added(self, event: WatchlistPanel.TitleAdded) -> None:
        """Handle new title added from watchlist input."""
        title = event.title
        if watchlist_module.add(title):
            self.log_activity(f"Added '{title}' to watchlist", level="success")
            self.load_data()
        else:
            self.log_activity(f"'{title}' already in watchlist", level="warning")

    # --- Helpers ---

    def log_activity(self, message: str, level: str = "info") -> None:
        """Log message to activity log widget."""
        try:
            log = self.query_one("#log", ActivityLog)
            if level == "error":
                log.log_error(message)
            elif level == "warning":
                log.log_warning(message)
            elif level == "success":
                log.log_success(message)
            else:
                log.log_info(message)
        except Exception:
            pass


def run_dashboard() -> None:
    """Entry point for the dashboard."""
    app = MangaMouserDashboard()
    app.run()


if __name__ == "__main__":
    run_dashboard()

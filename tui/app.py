"""MangaMouser TUI dashboard application."""

from datetime import datetime
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import (
    Footer,
    Header,
    LoadingIndicator,
    TabbedContent,
    TabPane,
)
from textual.worker import Worker, WorkerState

from config import load_config
from exceptions import ConfigError
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
        Binding("h", "toggle_completed_removed", "Done"),
        Binding("d", "toggle_dark", "Dark Mode"),
        Binding("f1", "show_help", "Help"),
        Binding("1", "switch_tab('downloads')", "Downloads", show=False),
        Binding("2", "switch_tab('watchlist')", "Watchlist", show=False),
        Binding("3", "switch_tab('log')", "Log", show=False),
    ]

    def __init__(self, feed_check_interval: int = 300):
        """
        Initialize the dashboard.

        Args:
            feed_check_interval: Seconds between automatic feed checks (default 5 min).
                                 Set to 0 to disable automatic feed checks.
        """
        super().__init__()
        self._config_error: str | None = None
        try:
            self.config = load_config()
            self.service = MangaMouser(self.config)
        except ConfigError as e:
            self._config_error = str(e)
            self.config = None
            self.service = None
        self.refresh_interval = 60  # Display refresh interval
        self.feed_check_interval = feed_check_interval  # Feed check interval
        self._last_feed_check: str = "Never"
        self._active_workers: int = 0
        self._show_completed_removed: bool = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main"):
            yield StatusPanel(id="status")
            yield LoadingIndicator(id="loading")
            with TabbedContent(id="tabs"):
                with TabPane("Downloads", id="downloads-tab"):
                    yield DownloadsTable(id="downloads")
                with TabPane("Watchlist", id="watchlist-tab"):
                    yield WatchlistPanel(id="watchlist")
                with TabPane("Activity Log", id="log-tab"):
                    yield ActivityLog(id="log")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize on app startup."""
        # Set default theme
        self.theme = "flexoki"

        # Hide loading indicator initially
        self.query_one("#loading").display = False

        if self._config_error:
            self.log_activity(f"Config error: {self._config_error}", level="error")
            return

        self.log_activity("Dashboard started")
        self.load_data()
        self.set_interval(self.refresh_interval, self.load_data)
        if self.feed_check_interval > 0:
            self.set_interval(self.feed_check_interval, self._auto_check_feed)

    # --- Background Workers ---

    @work(thread=True, group="data", exclusive=True)
    def load_data(self) -> dict:
        """Load matches and status from storage."""
        if self.config is None:
            return {
                "matches": [],
                "count": 0,
                "active": 0,
                "watchlist": [],
                "last_feed_check": self._last_feed_check,
            }

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
        if self.service is None:
            return -1
        return self.service.sync_download_status()

    @work(thread=True, group="feed", exclusive=True)
    def check_feed(self) -> int:
        """Check RSS feed for new matches."""
        if self.service is None:
            return -1
        return self.service.check_feed(download=True)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        if event.state == WorkerState.RUNNING:
            self._active_workers += 1
            self._show_loading(True)
        elif event.state in (
            WorkerState.SUCCESS,
            WorkerState.ERROR,
            WorkerState.CANCELLED,
        ):
            self._active_workers = max(0, self._active_workers - 1)
            if self._active_workers == 0:
                self._show_loading(False)
            if event.state == WorkerState.SUCCESS:
                self._handle_worker_success(event.worker)
            elif event.state == WorkerState.ERROR:
                self.log_activity(f"Error: {event.worker.error}", level="error")

    def _show_loading(self, show: bool) -> None:
        """Show or hide the loading indicator."""
        try:
            self.query_one("#loading").display = show
        except Exception:
            pass

    def _handle_worker_success(self, worker: Worker) -> None:
        """Process successful worker results."""
        if worker.group == "data":
            result = worker.result
            if result is not None:
                self._update_display(result)

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
        matches = data["matches"]
        if not self._show_completed_removed:
            matches = [
                m
                for m in matches
                if not (
                    m.get("download_status", {}).get("state") == "removed"
                    and m.get("download_status", {}).get("progress", 0) >= 1.0
                )
            ]
        table.update_data(matches)

        watchlist = self.query_one("#watchlist", WatchlistPanel)
        watchlist.update_titles(data["watchlist"])

    def _auto_check_feed(self) -> None:
        """Run automatic feed check."""
        self.log_activity("Auto-checking RSS feed...")
        self.check_feed()

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

    def action_toggle_completed_removed(self) -> None:
        """Toggle visibility of completed+removed downloads."""
        self._show_completed_removed = not self._show_completed_removed
        self.load_data()

    def action_switch_tab(self, tab_id: str) -> None:
        """Switch to a specific tab."""
        tab_map = {
            "downloads": "downloads-tab",
            "watchlist": "watchlist-tab",
            "log": "log-tab",
        }
        if tab_id in tab_map:
            self.query_one("#tabs", TabbedContent).active = tab_map[tab_id]

    def action_show_help(self) -> None:
        """Show keyboard shortcuts help."""
        help_text = """[b]Keyboard Shortcuts[/b]

[cyan]q[/]     Quit
[cyan]r[/]     Refresh data
[cyan]s[/]     Sync with qBittorrent
[cyan]c[/]     Check RSS feed
[cyan]h[/]     Show/hide completed+removed
[cyan]d[/]     Toggle dark mode
[cyan]F1[/]    Show this help

[b]Tab Navigation[/b]
[cyan]1[/]     Downloads tab
[cyan]2[/]     Watchlist tab
[cyan]3[/]     Activity Log tab
"""
        self.notify(help_text, title="Help", timeout=10)

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

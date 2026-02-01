"""Status panel widget displaying summary statistics."""

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static


class StatusPanel(Static):
    """Displays summary statistics."""

    match_count: reactive[int] = reactive(0)
    active_downloads: reactive[int] = reactive(0)
    last_refresh: reactive[str] = reactive("Never")
    last_feed_check: reactive[str] = reactive("Never")
    feed_interval: reactive[int] = reactive(300)

    def compose(self) -> ComposeResult:
        yield Static(self._format_status(), id="status-line")

    def _format_status(self) -> str:
        """Format the full status line."""
        if self.feed_interval > 0:
            mins = self.feed_interval // 60
            mode = f"Auto-download every {mins}m"
        else:
            mode = "Manual mode"
        return f"Matches: {self.match_count}  |  Active: {self.active_downloads}  |  Feed checked: {self.last_feed_check}  |  {mode}"

    def _refresh_status(self) -> None:
        """Update the status line."""
        try:
            self.query_one("#status-line", Static).update(self._format_status())
        except Exception:
            pass

    def watch_match_count(self, value: int) -> None:
        self._refresh_status()

    def watch_active_downloads(self, value: int) -> None:
        self._refresh_status()

    def watch_last_feed_check(self, value: str) -> None:
        self._refresh_status()

    def watch_feed_interval(self, value: int) -> None:
        self._refresh_status()

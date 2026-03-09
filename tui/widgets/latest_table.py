"""Latest downloads table widget showing the most recent downloads."""

from email.utils import parsedate_to_datetime

from textual.widgets import DataTable


class LatestTable(DataTable):
    """Table displaying the most recent downloads."""

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = False
        self.add_columns("Full Name", "Date", "Progress")

    def update_data(self, matches: list[dict]) -> None:
        """Refresh table with the last 5 matches (newest first)."""
        self.clear()
        for match in reversed(matches[-5:]):
            status = match.get("download_status", {})
            progress = f"{status.get('progress', 0) * 100:.0f}%"

            self.add_row(
                match.get("title", ""),
                self._format_date(match.get("published", "")),
                progress,
            )

    @staticmethod
    def _format_date(date_str: str) -> str:
        """Format RFC 2822 date to local time without day name, seconds, or timezone."""
        try:
            dt = parsedate_to_datetime(date_str).astimezone()
            return dt.strftime("%d %b %Y %H:%M")
        except Exception:
            return date_str

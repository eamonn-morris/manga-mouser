"""Latest downloads table widget showing the most recent downloads."""

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
                match.get("published", ""),
                progress,
            )

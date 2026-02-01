"""Downloads table widget displaying tracked downloads with status."""

from textual.widgets import DataTable


class DownloadsTable(DataTable):
    """Table displaying tracked downloads with status."""

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = False
        self.add_columns("Title", "Full Name", "State", "Progress", "Size")

    def update_data(self, matches: list[dict]) -> None:
        """Refresh table with match data."""
        self.clear()
        for match in matches:
            status = match.get("download_status", {})
            state = status.get("state", "unknown")
            progress = f"{status.get('progress', 0) * 100:.0f}%"
            size = self._format_size(status.get("size", 0))

            self.add_row(
                match.get("matched_title", "Unknown"),
                self._truncate(match.get("title", ""), 50),
                state,
                progress,
                size,
            )

    @staticmethod
    def _truncate(text: str, length: int) -> str:
        return text[:length] + "..." if len(text) > length else text

    @staticmethod
    def _format_size(size_bytes: int | float) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes = size_bytes / 1024
        return f"{size_bytes:.1f} TB"

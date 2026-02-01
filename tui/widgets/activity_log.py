"""Activity log widget for displaying application events."""

from datetime import datetime

from textual.widgets import RichLog


class ActivityLog(RichLog):
    """Scrolling log of application activity."""

    def on_mount(self) -> None:
        self.wrap = True
        self.markup = True

    def log_info(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.write(f"[dim]{timestamp}[/] [blue]INFO[/] {message}")

    def log_success(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.write(f"[dim]{timestamp}[/] [green]OK[/] {message}")

    def log_error(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.write(f"[dim]{timestamp}[/] [red]ERROR[/] {message}")

    def log_warning(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.write(f"[dim]{timestamp}[/] [yellow]WARN[/] {message}")

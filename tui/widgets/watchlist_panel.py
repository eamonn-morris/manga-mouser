"""Watchlist panel widget displaying tracked titles."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widgets import Input, Label, Static


class WatchlistPanel(Static):
    """Panel displaying watchlist titles with input for adding new ones."""

    class TitleAdded(Message):
        """Message sent when a title is added."""

        def __init__(self, title: str) -> None:
            self.title = title
            super().__init__()

    def __init__(self, titles: list[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self._titles = titles or []

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Add title and press Enter...", id="watchlist-input")
        with VerticalScroll(id="watchlist-content"):
            if self._titles:
                for title in self._titles:
                    yield Label(f"• {title}", classes="watchlist-item")
            else:
                yield Label("[dim]No titles in watchlist[/]", classes="watchlist-item")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        title = event.value.strip()
        if title:
            self.post_message(self.TitleAdded(title))
            event.input.clear()

    def update_titles(self, titles: list[str]) -> None:
        """Update the watchlist display."""
        self._titles = titles
        content = self.query_one("#watchlist-content", VerticalScroll)
        content.query(".watchlist-item").remove()
        if titles:
            for title in titles:
                content.mount(Label(f"• {title}", classes="watchlist-item"))
        else:
            content.mount(
                Label("[dim]No titles in watchlist[/]", classes="watchlist-item")
            )

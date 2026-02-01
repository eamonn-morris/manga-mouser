"""Watchlist panel widget displaying tracked titles."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Collapsible, Input, Label, Static


class WatchlistPanel(Static):
    """Panel containing a collapsible watchlist."""

    class TitleAdded(Message):
        """Message sent when a title is added."""

        def __init__(self, title: str) -> None:
            self.title = title
            super().__init__()

    def __init__(self, titles: list[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self._titles = titles or []

    def compose(self) -> ComposeResult:
        with Collapsible(title="Watchlist", collapsed=True, id="watchlist-collapsible"):
            with Vertical(id="watchlist-content"):
                if self._titles:
                    for title in self._titles:
                        yield Label(f"• {title}", classes="watchlist-item")
                else:
                    yield Label("[dim]No titles in watchlist[/]", classes="watchlist-item")
            yield Input(placeholder="Add title and press Enter...", id="watchlist-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        title = event.value.strip()
        if title:
            self.post_message(self.TitleAdded(title))
            event.input.clear()

    def update_titles(self, titles: list[str]) -> None:
        """Update the watchlist display."""
        self._titles = titles
        content = self.query_one("#watchlist-content", Vertical)
        content.query(".watchlist-item").remove()
        if titles:
            for title in titles:
                content.mount(Label(f"• {title}", classes="watchlist-item"))
        else:
            content.mount(Label("[dim]No titles in watchlist[/]", classes="watchlist-item"))

    def toggle(self) -> None:
        """Toggle the collapsible."""
        collapsible = self.query_one("#watchlist-collapsible", Collapsible)
        collapsible.collapsed = not collapsible.collapsed

    @property
    def collapsed(self) -> bool:
        """Get collapsed state."""
        return self.query_one("#watchlist-collapsible", Collapsible).collapsed

    @collapsed.setter
    def collapsed(self, value: bool) -> None:
        """Set collapsed state."""
        self.query_one("#watchlist-collapsible", Collapsible).collapsed = value

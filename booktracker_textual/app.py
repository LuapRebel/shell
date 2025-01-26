from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from conn import CONN
from books import (
    BookAddScreen,
    BookDeleteScreen,
    BookDeleteConfirmationScreen,
    BookEditScreen,
    BookEditConfirmationScreen,
    BookFilterScreen,
    BookScreen,
    BookStatsScreen,
)


class BookTracker(App):
    CSS_PATH = "app.tcss"
    SCREENS = {
        "add": BookAddScreen,
        "books": BookScreen,
        "book_stats": BookStatsScreen,
        "delete": BookDeleteScreen,
        "delete_confirmation": BookDeleteConfirmationScreen,
        "edit": BookEditScreen,
        "edit_confirmation": BookEditConfirmationScreen,
        "filter": BookFilterScreen,
    }
    # BINDINGS = [
    #     ("b", "push_screen('books')", "Books"),
    # ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.theme = "gruvbox"
        self.push_screen(BookScreen())

    def _on_screen_resume(self) -> None:
        self.push_screen(BookScreen())

    def on_close(self) -> None:
        CONN.close()


if __name__ == "__main__":
    app = BookTracker()
    app.run()

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Markdown

from conn import CONN
from books import BookFilterScreen, BookInputScreen, BookScreen


MARKDOWN = """
A Python textual TUI to manage books.

Add Books by pressing `b` to View the existing Books and then `a` to add a new one.
"""


class HomeScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield Markdown(MARKDOWN)
        yield Footer()


class BookTracker(App):
    CSS_PATH = "app.tcss"
    SCREENS = {
        "home": HomeScreen,
        "books": BookScreen,
        "book_filter": BookFilterScreen,
        "book_input": BookInputScreen,
    }
    BINDINGS = [
        ("h", "push_screen('home')", "Home"),
        ("b", "push_screen('books')", "Books"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.theme = "gruvbox"
        self.push_screen(HomeScreen())

    def on_close(self) -> None:
        CONN.close()

    def action_quit(self) -> None:
        self.exit()


if __name__ == "__main__":
    app = BookTracker()
    app.run()

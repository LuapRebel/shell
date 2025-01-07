from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Markdown

from conn import CONN
from books import BookInputScreen, BookScreen


MARKDOWN = """
A Python textual TUI to manage books.
"""


class HomeScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield Markdown(MARKDOWN)
        yield Footer()


class BookTracker(App):
    CSS_PATH = "app.tcss"
    SCREENS = {"home": HomeScreen, "books": BookScreen, "book_input": BookInputScreen}
    BINDINGS = [
        ("h", "push_screen('home')", "Home"),
        ("b", "push_screen('books')", "Books"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())

    def on_close(self) -> None:
        CONN.close()

    def action_quit(self) -> None:
        self.exit()


if __name__ == "__main__":
    app = BookTracker()
    app.run()

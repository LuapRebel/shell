from pydantic import ValidationError
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen, Screen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Footer, Header, Input

from conn import CONN
from db import Book


class BookEditWidget(Widget):
    """Widget to edit book information"""

    def compose(self) -> ComposeResult:
        with Container(id="book-edit-widget"):
            yield Input(placeholder="Title", id="book-title")
            yield Input(placeholder="Author (Lastname, First)", id="book-author")
            yield Input(
                placeholder="Status (TBR, IN_PROGRESS, COMPLETED)", id="book-status"
            )
            yield Input(placeholder="Date Started (YYYY-MM-DD)", id="book-date-started")
            yield Input(
                placeholder="Date Completed(YYYY-MM-DD)", id="book-date-completed"
            )
            yield Button("Submit", id="book-submit")


class BookInputScreen(ModalScreen):
    """Modal screen to provide inputs to create a new Book"""

    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        yield BookEditWidget()
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        inputs = self.query(Input)
        values = [i.value for i in inputs]
        keys = ["title", "author", "status", "date_started", "date_completed"]
        validation_dict = dict(zip(keys, values))
        try:
            Book(**validation_dict)
            cur = CONN.cursor()
            cur.execute(
                """INSERT INTO books(title, author, status, date_started, date_completed)
                VALUES (?, ?, ?, ?, ?)
                """,
                values,
            )
            CONN.commit()
            for i in inputs:
                i.clear()
            self.app.push_screen("books")
        except ValidationError as e:
            print(e)


class BookFilterScreen(Screen):
    """Widget to filter books by field and search term"""

    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Input(placeholder="Field to search", id="field"),
            Input(placeholder="Search term", id="value"),
            Button("Submit", id="filter-submit"),
            id="filter-container",
        )
        yield RichLog(id="filter-log")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        field = self.query_one("#field").value
        value = self.query_one("#value").value
        read_sql = f"SELECT * FROM books WHERE {field} LIKE ?"
        binding = (f"%{value}%",)
        cur = CONN.cursor()
        data = cur.execute(read_sql, binding).fetchall()
        books = [Book(**dict(zip(Book.model_fields.keys(), d))) for d in data]
        rich_log = self.query_one("#filter-log")
        rich_log.clear()
        rich_log.write(books)
        for i in self.query(Input):
            i.clear()

    def _on_screen_resume(self) -> None:
        rich_log = self.query_one("#filter-log")
        rich_log.clear()


class BookScreen(Screen):
    """Widget to manage book collection."""

    BINDINGS = [
        ("f", "filter_books", "Filter"),
        ("a", "add_book", "Add"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="books-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#books-table")
        cur = CONN.cursor()
        data = cur.execute("SELECT * FROM books").fetchall()
        columns = [desc[0] for desc in cur.description]
        table.add_columns(*columns)
        table.add_rows(data)
        table.zebra_stripes = True

    def action_filter_books(self) -> None:
        self.app.push_screen("book_filter")

    def action_add_book(self) -> None:
        self.app.push_screen("book_input")

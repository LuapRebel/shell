from pydantic import ValidationError
from textual.app import ComposeResult
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Footer, Header, Input

from conn import CONN
from db import Book


class BookInputScreen(ModalScreen):
    """Modal screen to provide inputs to create a Book"""

    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Title", id="book-title")
        yield Input(placeholder="Author (Lastname, First)", id="book-author")
        yield Input(
            placeholder="Status (TBR, IN_PROGRESS, COMPLETED)", id="book-status"
        )
        yield Input(placeholder="Date Started (YYYY-MM-DD)", id="book-date-started")
        yield Input(placeholder="Date Completed(YYYY-MM-DD)", id="book-date-completed")
        yield Button("Submit", id="book-submit")
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


class BookScreen(Screen):
    """Widget to manage book collection."""

    BINDINGS = [("a", "add_book", "Add Book")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="book-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        cur = CONN.cursor()
        data = cur.execute("SELECT * FROM books").fetchall()
        columns = [desc[0] for desc in cur.description]
        table.add_columns(*columns)
        table.add_rows(data)

    def _on_screen_resume(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        cur = CONN.cursor()
        data = cur.execute("SELECT * FROM books").fetchall()
        table.add_rows(data)

    def action_add_book(self) -> None:
        self.app.push_screen("book_input")

from pydantic import ValidationError
from textual import events
from textual import on
from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen, Screen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Footer, Header, Input, RichLog, Static

from conn import CONN
from db import Book


class BookEditWidget(Widget):
    """Widget to edit book information"""

    def compose(self) -> ComposeResult:
        with Container(id="book-edit-widget"):
            yield Input(placeholder="Title", id="title")
            yield Input(placeholder="Author (Lastname, First)", id="author")
            yield Input(placeholder="Status (TBR, IN_PROGRESS, COMPLETED)", id="status")
            yield Input(placeholder="Date Started (YYYY-MM-DD)", id="date-started")
            yield Input(placeholder="Date Completed (YYYY-MM-DD)", id="date-completed")


class BookDeleteScreen(ModalScreen):
    """Screen to delete a Book given an ID"""

    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def compose(self) -> ComposeResult:
        with Container(id="book-delete-screen"):
            yield Input(placeholder="ID", id="id-delete")
            yield Button("Delete", id="delete-submit")
            yield Footer()

    @on(Button.Pressed, "#delete-submit")
    def delete_book_pressed(self) -> None:

        def check_delete(delete: bool | None) -> None:
            if delete:
                id = self.query_one("#id-delete")
                if id:
                    cur = CONN.cursor()
                    cur.execute("DELETE FROM books WHERE id=?", (id.value,))
                    CONN.commit()
            id.clear()

        self.app.push_screen("delete_confirmation", check_delete)


class BookDeleteConfirmationScreen(ModalScreen[bool]):
    """Widget providing dialog box to allow users to delete a book or cancel"""

    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def compose(self) -> ComposeResult:
        with Container(id="book-delete-widget"):
            yield Static("Are you sure you want to delete?")
            yield Button("Yes", id="delete-book")
            yield Button("No", id="cancel-delete-book")
            yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "delete-book":
            self.dismiss(True)
        else:
            self.dismiss(False)


class BookAddScreen(ModalScreen):
    """Modal screen to provide inputs to create a new Book"""

    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def compose(self) -> ComposeResult:
        yield BookEditWidget()
        yield Button("Submit", id="add")
        yield Footer()

    @on(Button.Pressed, "#add")
    def book_submit_pressed(self):
        inputs = self.query(Input)
        validation_dict = {i.id.replace("-", "_"): i.value for i in inputs}
        try:
            Book(**validation_dict)
            cur = CONN.cursor()
            cur.execute(
                f"INSERT INTO books({", ".join(validation_dict.keys())}) VALUES (?, ?, ?, ?, ?)",
                tuple(validation_dict.values()),
            )
            CONN.commit()
            for i in inputs:
                i.clear()
            self.app.push_screen("books")
        except ValidationError as e:
            self.notify(str(e))


class BookEditConfirmationScreen(ModalScreen[str | None]):
    """Modal screen to confirm ID of book to be edited"""

    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def compose(self) -> ComposeResult:
        yield Input(placeholder="ID", id="id-edit")
        yield Button("Edit", id="edit-submit")

    @on(Button.Pressed, "#edit-submit")
    def edit_book_pressed(self) -> None:
        book_id = self.query_one("#id-edit")
        if book_id:
            self.dismiss(book_id.value)
        else:
            self.dismiss(None)


class BookEditScreen(Screen):
    """Modal Screen to provide inputs to edit an existing book"""

    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def compose(self) -> ComposeResult:
        yield BookEditWidget()
        yield Button("Submit", id="edit-submit")
        yield Footer()

    @work
    async def on_mount(self) -> None:
        book_id = await self.app.push_screen_wait(BookEditConfirmationScreen())
        if book_id:
            self.book_id = book_id
            cur = CONN.cursor()
            book = cur.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
            inputs = self.query(Input)
            for i in inputs:
                key = i.id.replace("-", "_")
                i.value = book[key]
        else:
            self.app.push_screen("books")

    def clear_inputs(self) -> None:
        inputs = self.query(Input)
        for i in inputs:
            i.clear()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.clear_inputs()

    @on(Button.Pressed, "#edit-submit")
    def edit_submit_pressed(self):
        inputs = self.query(Input)
        validation_dict = {i.id.replace("-", "_"): i.value for i in inputs}
        try:
            Book(**validation_dict)
            update_values = []
            update_sql = "SET "
            for k, v in validation_dict.items():
                update_sql += f"{k} = ?, "
                update_values.append(v)
            full_sql = f"""
            UPDATE books
            {update_sql[0:-2]}
            WHERE id = {self.book_id}
            """
            cursor = CONN.cursor()
            cursor.execute(full_sql, update_values)
            CONN.commit()
            self.clear_inputs()
        except ValidationError as e:
            self.notify(str(e))
        self.app.push_screen("books")


class BookFilterScreen(Screen):
    """Widget to filter books by field and search term"""

    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Input(placeholder="Field to search", id="filter-field", classes="column"),
            Input(placeholder="Search term", id="filter-value", classes="column"),
            Button("Submit", id="filter-submit", classes="column"),
            id="filter-container",
        )
        yield RichLog(id="filter-log")
        yield Footer()

    @on(Button.Pressed, "#filter-submit")
    def filter_submit_pressed(self) -> None:
        field = self.query_one("#filter-field").value
        value = self.query_one("#filter-value").value
        read_sql = f"SELECT * FROM books WHERE {field} LIKE ?"
        binding = (f"%{value}%",)
        cur = CONN.cursor()
        data = cur.execute(read_sql, binding).fetchall()
        books = [Book(**d) for d in data]
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
        ("f", "app.push_screen('filter')", "Filter"),
        ("a", "app.push_screen('add')", "Add"),
        ("e", "app.push_screen('edit')", "Edit"),
        ("d", "app.push_screen('delete')", "Delete"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="books-table")
        yield Footer()

    def on_mount(self) -> None:
        self.load_books()

    def _on_screen_resume(self) -> None:
        self.load_books()

    def load_books(self) -> None:
        table = self.query_one("#books-table")
        table.clear(columns=True)
        cur = CONN.cursor()
        data = cur.execute("SELECT * FROM books").fetchall()
        books = [Book(**d).model_dump().values() for d in data]
        columns = [*Book.model_fields.keys(), *Book.model_computed_fields.keys()]
        table.add_columns(*columns)
        table.add_rows(books)
        table.add_rows(data)
        table.zebra_stripes = True

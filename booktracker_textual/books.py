from datetime import datetime
from pydantic import ValidationError
from statistics import mean
from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal
from textual.screen import ModalScreen, Screen
from textual.widget import Widget
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Rule,
    Static,
)

from conn import CONN
from db import Book


def load_books() -> None:
    cur = CONN.cursor()
    data = cur.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    return [Book(**d) for d in data]


class BookStats:
    """
    Class to generate stats for books read, based on date_completed
    """

    def __init__(self, books: list[Book]):
        self.books = books
        self.ymd = [self.get_ymd(book) for book in books]

    def get_ymd(self, book: Book) -> Book:
        if book.status == "COMPLETED" and book.date_completed:
            ymd = datetime.fromisoformat(book.date_completed)
            return (
                ymd.year,
                ymd.month,
                book.days_to_read,
            )

    def flatten(self, l: list) -> list:
        out = []
        for item in l:
            if isinstance(item, list):
                out.extend(self.flatten(item))
            else:
                out.append(item)
        return out

    def complete_stats(self) -> list[dict]:
        years = {book[0] for book in self.ymd if book}
        stats = [
            [self.month_stats(year, month) for month in range(1, 13)] for year in years
        ]
        return self.flatten(stats)

    def month_stats(self, year: int, month: int) -> list[dict]:
        books_read = [
            book for book in self.ymd if book and book[0] == year and book[1] == month
        ]
        count = len(books_read)
        if count:
            avg_days_to_read = round(mean([book[2] for book in books_read]), 2)
        else:
            avg_days_to_read = None
        return [
            {
                "year": year,
                "month": month,
                "count": count,
                "avg_days_to_read": avg_days_to_read,
            }
        ]

    def year_stats(self, year: int, complete: bool = False) -> list[dict]:
        books_read = [book for book in self.ymd if book and book[0] == year]
        count = len(books_read)
        if count:
            avg_days_to_read = round(mean([book[2] for book in books_read]), 2)
        else:
            avg_days_to_read = None
        if complete:
            month_stats = [self.month_stats(year, month) for month in range(1, 13)]
            return self.flatten(month_stats)
        return [
            {
                "year": year,
                "count": count,
                "avg_days_to_read": avg_days_to_read,
            }
        ]


class BookStatsScreen(Screen):
    """Screen to display stats about books read"""

    BINDINGS = [("escape", "push_books", "Books")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Center(id="yearly-stats"):
            yield Label("BookTracker Yearly Stats", id="stats-table-year-label")
            yield DataTable(id="stats-table-year")
        yield Rule(line_style="heavy")
        with Center(id="complete-stats"):
            yield Label("BookTracker Complete Stats", id="stats-table-complete-label")
            yield DataTable(id="stats-table-complete")
        yield Footer()

    def on_mount(self) -> None:
        books = load_books()
        complete_stats = BookStats(books).complete_stats()
        years = {stat["year"] for stat in complete_stats}
        year_table = self.query_one("#stats-table-year")
        year_table_stats = [BookStats(books).year_stats(year)[0] for year in years]
        year_table_columns = year_table_stats[0].keys()
        year_table_rows = [stat.values() for stat in year_table_stats]
        year_table.clear(columns=True)
        year_table.add_columns(*year_table_columns)
        year_table.add_rows(year_table_rows)
        year_table.zebra_stripes = True
        complete_columns = complete_stats[0].keys()
        complete_rows = [stat.values() for stat in complete_stats]
        complete_table = self.query_one("#stats-table-complete")
        complete_table.clear(columns=True)
        complete_table.add_columns(*complete_columns)
        complete_table.add_rows(complete_rows)
        complete_table.zebra_stripes = True

    def action_push_books(self) -> None:
        self.app.push_screen(BookScreen())


class BookEditWidget(Widget):
    """Widget to edit book information. Used in both Add and Edit scenarios."""

    def compose(self) -> ComposeResult:
        with Container(id="book-edit-widget"):
            yield Input(placeholder="Title", id="title")
            yield Input(placeholder="Author (Lastname, First)", id="author")
            yield Input(placeholder="Status (TBR, IN_PROGRESS, COMPLETED)", id="status")
            yield Input(placeholder="Date Started (YYYY-MM-DD)", id="date-started")
            yield Input(placeholder="Date Completed (YYYY-MM-DD)", id="date-completed")


class BookDeleteScreen(ModalScreen):
    """Screen to delete a Book given an ID"""

    BINDINGS = [("escape", "push_books", "Books")]

    def compose(self) -> ComposeResult:
        with Container(id="book-delete-screen"):
            yield Input(placeholder="ID", id="id-delete")
            yield Button("Delete", id="delete-submit")
            yield Footer()

    @on(Button.Pressed, "#delete-submit")
    def delete_book_pressed(self) -> None:

        def check_delete(delete: bool | None) -> None:
            id = self.query_one("#id-delete")
            if delete:
                cur = CONN.cursor()
                cur.execute("DELETE FROM books WHERE id=?", (id.value,))
                CONN.commit()
            id.clear()

        self.app.push_screen(BookDeleteConfirmationScreen(), check_delete)

    def action_push_books(self) -> None:
        self.app.push_screen(BookScreen())


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
        self.app.push_screen(BookScreen())


class BookAddScreen(ModalScreen):
    """Modal screen to provide inputs to create a new Book"""

    BINDINGS = [
        ("escape", "push_books", "Books"),
    ]

    def compose(self) -> ComposeResult:
        with Container(id="add-screen"):
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

    def action_push_books(self) -> None:
        self.app.push_screen(BookScreen())


class BookEditScreen(Screen):
    """Modal Screen to provide inputs to edit an existing book"""

    BINDINGS = [
        ("escape", "push_books", "Books"),
    ]

    def __init__(self, cell_value: str) -> None:
        super().__init__()
        self.cell_value = cell_value

    def compose(self) -> ComposeResult:
        yield BookEditWidget()
        yield Button("Submit", id="edit-submit")
        yield Footer()

    def on_mount(self) -> None:
        if self.cell_value:
            cur = CONN.cursor()
            book = cur.execute(
                "SELECT * FROM books WHERE id=?", (self.cell_value,)
            ).fetchone()
            inputs = self.query(Input)
            for i in inputs:
                key = i.id.replace("-", "_")
                i.value = book.get(key, "")
        else:
            self.app.push_screen(BookScreen())

    def clear_inputs(self) -> None:
        inputs = self.query(Input)
        for i in inputs:
            i.clear()

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
        self.app.push_screen(BookScreen())

    def action_push_books(self) -> None:
        self.clear_inputs()
        self.app.push_screen(BookScreen())


class BookFilterScreen(Screen):
    """Widget to filter books by field and search term"""

    BINDINGS = [
        ("escape", "push_books", "Books"),
        ("e", "push_edit", "Edit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Input(placeholder="Field to search", id="filter-field", classes="column"),
            Input(placeholder="Search term", id="filter-value", classes="column"),
            Button("Submit", id="filter-submit", classes="column"),
            id="filter-container",
        )
        yield DataTable(id="filter-table")
        yield Footer()

    @on(Button.Pressed, "#filter-submit")
    def filter_submit_pressed(self) -> None:
        field = self.query_one("#filter-field").value
        value = self.query_one("#filter-value").value
        if field and value:
            read_sql = f"SELECT * FROM books WHERE {field} LIKE ?"
            binding = (f"%{value}%",)
            cur = CONN.cursor()
            data = cur.execute(read_sql, binding).fetchall()
            books = [Book(**d) for d in data]
            table = self.query_one("#filter-table")
            table.clear(columns=True)
            rows = [book.model_dump().values() for book in books]
            columns = [*Book.model_fields.keys(), *Book.model_computed_fields.keys()]
            table.add_columns(*columns)
            table.add_rows(rows)
            table.zebra_stripes = True
            self.focus_next("#filter-table")
            self.clear_inputs()

    def clear_inputs(self) -> None:
        inputs = self.query(Input)
        for i in inputs:
            i.clear()

    def _on_screen_resume(self) -> None:
        table = self.query_one("#filter-table")
        table.clear(columns=True)

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        self.cell_value = event.value or ""
        self.cell_coordinate = event.coordinate

    def action_push_edit(self) -> None:
        try:
            int(self.cell_value)
        except ValueError:
            pass
        else:
            if self.cell_coordinate.column == 0:
                self.app.push_screen(BookEditScreen(self.cell_value))

    def action_push_books(self) -> None:
        self.clear_inputs()
        self.app.push_screen(BookScreen())


class BookScreen(Screen):
    """Widget to manage book collection."""

    BINDINGS = [
        ("f", "push_filter", "Filter"),
        ("a", "push_add", "Add"),
        ("e", "push_edit", "Edit"),
        ("d", "push_delete", "Delete"),
        ("s", "push_stats", "Stats"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="books-table")
        yield Footer()

    def on_mount(self) -> None:
        books = load_books()
        rows = [book.model_dump().values() for book in books]
        table = self.query_one("#books-table")
        table.clear(columns=True)
        columns = [*Book.model_fields.keys(), *Book.model_computed_fields.keys()]
        table.add_columns(*columns)
        table.add_rows(rows)
        table.zebra_stripes = True

    def _on_screen_resume(self) -> None:
        books = load_books()
        rows = [book.model_dump().values() for book in books]
        table = self.query_one("#books-table")
        table.clear(columns=True)
        columns = [*Book.model_fields.keys(), *Book.model_computed_fields.keys()]
        table.add_columns(*columns)
        table.add_rows(rows)
        table.zebra_stripes = True

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        self.cell_value = event.value or ""
        self.cell_coordinate = event.coordinate

    def action_push_filter(self) -> None:
        self.app.push_screen(BookFilterScreen())

    def action_push_add(self) -> None:
        self.app.push_screen(BookAddScreen())

    def action_push_edit(self) -> None:
        try:
            int(self.cell_value)
        except ValueError:
            pass
        else:
            if self.cell_coordinate.column == 0:
                self.app.push_screen(BookEditScreen(self.cell_value))

    def action_push_delete(self) -> None:
        self.app.push_screen(BookDeleteScreen())

    def action_push_stats(self) -> None:
        self.app.push_screen(BookStatsScreen())

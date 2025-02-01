from datetime import datetime
import re
from statistics import mean
from typing import Optional
from typing_extensions import Annotated

from pydantic import ValidationError
from rich import box, print
from rich.console import Console
from rich.table import Table
import typer

from conn import CONN
from db import Book

app = typer.Typer()
console = Console()


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

    def print_rich_table(self, stats: list[dict[str, int | float | None]]):
        columns = stats[0].keys()
        colors = ["bright_green", "bright_blue", "bright_red", "cyan3"]
        table = Table(title="BookTracker Statistics", box=box.ROUNDED)
        for column, color in zip(columns, colors):
            table.add_column(column, style=color, justify="full", min_width=8)
        for row in stats:
            values = list(map(str, row.values()))
            table.add_row(*values)
        console.print(table)


def get_books(field: str | None = None, value: str | None = None) -> list[Book]:
    if field and value:
        if field == "id":
            read_sql = f"SELECT * FROM books WHERE id=?"
            binding = (value,)
        else:
            read_sql = f"SELECT * FROM books WHERE {field} LIKE ?"
            binding = (str("%" + value + "%"),)
        cursor = CONN.cursor()
        books = cursor.execute(read_sql, binding).fetchall()
    else:
        cursor = CONN.cursor()
        books = cursor.execute("SELECT * FROM books").fetchall()
    if books:
        return [Book(**book) for book in books]


def status_callback(value: str):
    if value not in ["TBR", "IN_PROGRESS", "COMPLETED"]:
        raise typer.BadParameter(
            "status must be one of 'TBR', 'IN_PROGRESS', or 'COMPLETED'"
        )
    return value


def date_callback(value: str):
    if not re.match("[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise typer.BadParameter("date columns must be formatted 'YYYY-MM-DD'")
    return value


@app.command()
def read(
    field: Annotated[
        Optional[str],
        typer.Option("-f", "--field", help="Model field to search (e.g. id or title)"),
    ] = None,
    value: Annotated[
        Optional[str], typer.Option("-v", "--value", help="Search term")
    ] = None,
) -> list[Book]:
    books = get_books(field, value)
    columns = [*Book.model_fields.keys(), *Book.model_computed_fields.keys()]
    colors = [
        "white",
        "bright_green",
        "bright_blue",
        "bright_red",
        "bright_magenta",
        "cyan3",
        "orange1",
    ]
    rows = [map(str, book.model_dump().values()) for book in books]
    table = Table(title="BookTracker", box=box.ROUNDED)
    for column, color in zip(columns, colors):
        table.add_column(column, style=color)
    for row in rows:
        table.add_row(*row)
    console.print(table)


@app.command()
def add(
    title: Annotated[str, typer.Argument()],
    author: Annotated[str, typer.Argument()],
    status: Annotated[
        Optional[str],
        typer.Option(
            "-s",
            "--status",
            callback=status_callback,
            help="TBR, IN_PROGRESS, COMPLETED",
        ),
    ] = "TBR",
    date_started: Annotated[
        Optional[str],
        typer.Option("-d", "--date-started", callback=date_callback, help="YYYY-MM-DD"),
    ] = "",
    date_completed: Annotated[
        Optional[str],
        typer.Option(
            "-c", "--date-completed", callback=date_callback, help="YYYY-MM-DD"
        ),
    ] = "",
) -> None:
    try:
        book = Book(
            title=title,
            author=author,
            status=status,
            date_started=date_started,
            date_completed=date_completed,
        )
    except ValidationError as e:
        print(e)
    cur = CONN.cursor()
    sql = "INSERT INTO books(title, author, status, date_started, date_completed) VALUES (?, ?, ?, ?, ?)"
    binding = (title, author, status, date_started, date_completed)
    cur.execute(sql, binding)
    CONN.commit()


@app.command()
def delete(id: Annotated[int, typer.Argument(help="ID to delete")]) -> None:
    cur = CONN.cursor()
    book = cur.execute("SELECT * FROM books WHERE id=?", (id,)).fetchone()
    if book:
        book_info = f"'{book['title']}' by {book['author']}"
        delete_book = (
            input(f"Are you sure you want to delete {book_info} (y/n): ")
            .lower()
            .strip()
            == "y"
        )
        if delete_book:
            print(f"Deleting {book_info}...")
            cur.execute("DELETE FROM books WHERE id=?", (id,))
            CONN.commit()
            print(f"{book_info} has been deleted.")
    else:
        print(f"There is no book with {id=}.")


@app.command()
def edit(id: Annotated[int, typer.Argument(help="ID of book to edit")]) -> None:
    cur = CONN.cursor()
    book = cur.execute("SELECT * FROM books WHERE id=?", (id,)).fetchone()
    if book:
        update_sql = "SET "
        update_values = []
        for k, v in book.items():
            data = input(f"Edit {k} ({v}): ")
            if data:
                update_sql += f"{k} = ?, "
                update_values.append(data)
        full_sql = f"""
        UPDATE books
        {update_sql[0:-2]}
        WHERE id = {id}
        """
        if update_values:
            cur.execute(full_sql, update_values)
            CONN.commit()
    else:
        print(f"There is no book with {id=}")


@app.command()
def stats(
    year: Annotated[int, typer.Option(help="Limit stats to a particular year")] = None,
    month: Annotated[
        int, typer.Option(min=1, max=12, help="Limit stats to a particular month.")
    ] = None,
    complete: Annotated[
        Optional[bool], typer.Option(help="Print complete stats by month")
    ] = False,
) -> None:
    books = get_books()
    if books:
        stats = BookStats(books)
    if not any([complete, year, month]):
        print("Choose --complete, --year, and/or --month to print stats.")
    if year and not month:
        if complete:
            stats.print_rich_table(stats.year_stats(year=year, complete=complete))
        else:
            stats.print_rich_table(stats.year_stats(year=year))
    if year and month:
        stats.print_rich_table(stats.month_stats(year=year, month=month))
    if month and not year:
        print("You must provide a year and a month.")
    if complete and not year:
        stats.print_rich_table(stats.complete_stats())


if __name__ == "__main__":
    app()
    CONN.close()

import re
from typing import Optional
from typing_extensions import Annotated

from pydantic import ValidationError
from rich import print
from rich.console import Console
from rich.table import Table
import typer

from conn import CONN
from db import Book

app = typer.Typer()
console = Console()


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
    rows = [map(str, book.model_dump().values()) for book in books]
    columns = [*Book.model_fields.keys(), *Book.model_computed_fields.keys()]
    table = Table(title="BookTracker")
    for column in columns:
        table.add_column(column)
    for row in rows:
        table.add_row(*row)
    console.print(table)


@app.command()
def add(
    title: Annotated[str, typer.Argument()],
    author: Annotated[str, typer.Argument()],
    status: Annotated[
        str,
        typer.Option(
            "-s",
            "--status",
            callback=status_callback,
            help="TBR, IN_PROGRESS, COMPLETED",
        ),
    ] = "TBR",
    date_started: Annotated[
        str,
        typer.Option("-d", "--date-started", callback=date_callback, help="YYYY-MM-DD"),
    ] = "",
    date_completed: Annotated[
        str,
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


if __name__ == "__main__":
    app()
    CONN.close()

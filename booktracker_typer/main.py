from typing import Optional
from typing_extensions import Annotated

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
def add():
    print("Adding a book...")


if __name__ == "__main__":
    app()
    CONN.close()

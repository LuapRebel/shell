from rich import print
from rich.console import Console
from rich.table import Table
import typer

from conn import CONN
from db import Book

app = typer.Typer()
console = Console()


@app.command()
def read():
    cur = CONN.cursor()
    data = cur.execute("SELECT * FROM books").fetchall()
    books = [Book(**d) for d in data]
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

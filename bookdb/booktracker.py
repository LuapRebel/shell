from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
import sqlite3

import click


DB_PATH = "bookdb/books.db"
CONN = sqlite3.connect(DB_PATH)

CONN.execute(
    """
    CREATE TABLE IF NOT EXISTS books(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        author TEXT,
        status TEXT,
        date_started TEXT,
        date_completed TEXT
    )
    """
)


class Status(StrEnum):
    TBR = "TBR"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


@dataclass
class Book:
    id: int | None = None
    title: str = ""
    author: str = ""
    status: Status = "TBR"
    date_started: date | None = None
    date_completed: date | None = None

    def __post_init__(self):
        if self.status not in list(Status):
            raise ValueError("status is invalid")


@click.group()
def cli() -> None:
    """
    A booktracker that allows users to add, edit, and delete books
    """


# ADD BOOK
@click.command()
@click.option("-t", "--title", default="")
@click.option("-a", "--author", default="", help="LASTNAME, FIRSTNAME")
@click.option("-s", "--status", type=click.Choice(Status._member_names_), default="TBR")
@click.option("-d", "--date-started", default=None, help="YYYY-MM-DD")
@click.option("-c", "--date-completed", default=None, help="YYYY-MM-DD")
def add(
    title: str, author: str, status: Status, date_started: date, date_completed: date
):
    book = Book(
        title=title,
        author=author,
        status=status,
        date_started=date_started,
        date_completed=date_completed,
    )
    add_sql = f"""
        INSERT INTO books (id, title, author, status, date_started, date_completed)
        VALUES (?, ?, ?, ?, ?, ?);
    """
    cursor = CONN.cursor()
    cursor.execute(add_sql, tuple(asdict(book).values()))
    CONN.commit()
    click.echo(f"Added {book} to database")
    CONN.close()


# READ BOOKS
@click.command()
@click.option("-f", "--field", help="Field to search within")
@click.option("-v", "--value", help="Value to search for")
def read(field: str | None = None, value: str | None = None) -> None:
    if field and value:
        read_sql = f"SELECT * FROM books WHERE {field} LIKE ?"
        cursor = CONN.cursor()
        books = cursor.execute(read_sql, (str("%" + value + "%"),)).fetchall()
        for book in books:
            click.echo(Book(*book))
    else:
        cursor = CONN.cursor()
        books = cursor.execute("SELECT * FROM books").fetchall()
        for book in books:
            click.echo(Book(*book))
    CONN.close()


if __name__ == "__main__":
    cli.add_command(add)
    cli.add_command(read)
    cli()

from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
import sqlite3

import click
from rich import print


DB_PATH = Path(__file__).parent.resolve() / "books.db"
CONN = sqlite3.connect(DB_PATH)


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {k: v for k, v in zip(fields, row)}


CONN.row_factory = dict_factory

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
@click.option(
    "-d",
    "--date-started",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="YYYY-MM-DD",
)
@click.option(
    "-c",
    "--date-completed",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="YYYY-MM-DD",
)
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
    print(f"Added {book} to database")


# READ BOOKS
@click.command()
@click.option(
    "-f",
    "--field",
    type=click.Choice(Book.__annotations__),
    help="Field to search within",
)
@click.option("-v", "--value", help="Value to search for")
def read(field: str | None = None, value: str | None = None) -> list[dict]:
    if field and value:
        read_sql = f"SELECT * FROM books WHERE {field} LIKE ?"
        cursor = CONN.cursor()
        books = cursor.execute(read_sql, (str("%" + value + "%"),)).fetchall()
        if books:
            for book in books:
                print(dict(book))
        else:
            print(f"There are no books with {field} containing {value}.")
    else:
        cursor = CONN.cursor()
        books = cursor.execute("SELECT * FROM books").fetchall()
        for book in books:
            print(dict(book))
    return books


# EDIT BOOK
@click.command()
@click.argument("id")
def edit(id: str) -> None:
    ctx = click.Context(read)
    books = ctx.forward(read, field="id", value=id)
    if books:
        book = dict(books[0])
        update_values = []
        update_sql = "SET "
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
            cursor = CONN.cursor()
            cursor.execute(full_sql, update_values)
            CONN.commit()
    else:
        print(f"There is no book with {id=}")


@click.command()
@click.argument("id")
def delete(id: str) -> None:
    print(f"Attempting to delete book with {id=}")
    ctx = click.Context(read)
    books = ctx.forward(read, field="id", value=id)
    if books:
        to_delete = (
            input("Are you sure you want to delete this book (y/n): ").strip().lower()
            == "y"
        )
        if to_delete:
            delete_sql = f"DELETE FROM books WHERE id = {id}"
            cursor = CONN.cursor()
            cursor.execute(delete_sql)
            CONN.commit()
    else:
        print(f"There is no book with {id=}")


if __name__ == "__main__":
    cli.add_command(add)
    cli.add_command(read)
    cli.add_command(edit)
    cli.add_command(delete)
    cli()
    CONN.close()

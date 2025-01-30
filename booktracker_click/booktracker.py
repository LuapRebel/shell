from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
import re
import sqlite3
from statistics import mean

import click
from rich import print
from rich.console import Console
from rich.table import Table


console = Console()


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {k: v for k, v in zip(fields, row)}


DB_PATH = Path(__file__).parent.resolve() / "books.db"
CONN = sqlite3.connect(DB_PATH)
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
    date_started: str | None = None
    date_completed: str | None = None
    days_to_read: int | None = None

    def __post_init__(self):
        if self.status not in list(Status):
            raise ValueError("status is invalid")
        if self.date_started and self.date_completed:
            ds = datetime.strptime(self.date_started, "%Y-%m-%d")
            dc = datetime.strptime(self.date_completed, "%Y-%m-%d")
            self.days_to_read = (dc - ds).days + 1  # inclusive
        else:
            self.days_to_read = None


def validate_dates(ctx, param, value):
    if value == "":
        return value
    elif re.match("[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return value
    else:
        raise click.BadParameter("Dates must be formatted as 'YYYY-MM-DD'.")


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

    def complete_stats(self) -> dict:
        years = {book[0] for book in self.ymd if book}
        stats = [
            [self.month_stats(year, month) for month in range(1, 13)] for year in years
        ]
        return self.flatten(stats)

    def month_stats(self, year: int, month: int) -> dict:
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
        table = Table(title="BookTracker Statistics")
        columns = stats[0].keys()
        for column in columns:
            table.add_column(column)
        for row in stats:
            values = list(map(str, row.values()))
            table.add_row(*values)
        console.print(table)


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
    type=str,
    callback=validate_dates,
    default="",
    help="YYYY-MM-DD",
)
@click.option(
    "-c",
    "--date-completed",
    type=str,
    callback=validate_dates,
    default="",
    help="YYYY-MM-DD",
)
def add(
    title: str, author: str, status: Status, date_started: str, date_completed: str
):
    book = Book(
        title=title,
        author=author,
        status=status,
        date_started=date_started,
        date_completed=date_completed,
    )
    book_values = tuple(asdict(book).values())[0:-1]  # Remove days_to_read
    add_sql = f"""
        INSERT INTO books (id, title, author, status, date_started, date_completed)
        VALUES (?, ?, ?, ?, ?, ?);
    """
    cursor = CONN.cursor()
    cursor.execute(add_sql, book_values)
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
def read(field: str | None = None, value: str | None = None) -> list[Book]:
    if field and value:
        books = get_books(field=field, value=value)
        if not books:
            print(f"There are no books with {field} containing {value}.")
    else:
        books = get_books()
        if not books:
            print("There are no books.")
    if books:
        print(books)


# EDIT BOOK
@click.command()
@click.argument("id")
def edit(id: str) -> None:
    books = get_books(field="id", value=id)
    if books:
        book = books[0]
        update_values = []
        update_sql = "SET "
        for k, v in asdict(book).items():
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


# DELETE
@click.command()
@click.argument("id")
def delete(id: str) -> None:
    print(f"Attempting to delete book with {id=}")
    books = get_books(field="id", value=id)
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


# STATS
@click.command()
@click.option("--complete", is_flag=True)
@click.option("-y", "--year", type=int)
@click.option("-m", "--month", type=click.IntRange(1, 12))
def stats(
    complete: bool | None = False, year: int | None = None, month: int | None = None
) -> None:
    books = get_books()
    if books:
        stats = BookStats(books)
    else:
        print("There are no books to run stats on.")
        click.Context.close()
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
    cli.add_command(add)
    cli.add_command(read)
    cli.add_command(edit)
    cli.add_command(delete)
    cli.add_command(stats)
    cli()
    CONN.close()

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
import re
from statistics import mean
from typing import Optional

from rich import box, print
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

DIR = Path(__file__).parent.resolve()
DB_PATH = DIR / "books.csv"

console = Console()


class DateAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not re.match("[0-9]{4}-[0-9]{2}-[0-9]{2}", values):
            raise argparse.ArgumentError(self, "Dates must be formatted 'YYYY-MM-DD'")
        setattr(namespace, self.dest, values)


class YearAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not values > 0:
            raise argparse.ArgumentError(self, "Year must be an integer > 0")
        setattr(namespace, self.dest, values)


class MonthAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values not in range(1, 13):
            raise argparse.ArgumentError(
                self, "Month must be an integer between 1 and 12."
            )
        setattr(namespace, self.dest, values)


class Status(StrEnum):
    TBR = "TBR"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


@dataclass
class Book:
    id: str | None = None
    title: str = ""
    author: str = ""
    status: Status = Status.TBR
    date_started: str | None = None
    date_completed: str | None = None
    days_to_read: int | None = None

    def __post_init__(self):
        if not self.id:
            books = read_books()
            if books:
                last_book_id = int(books[-1].id)
                self.id = str(last_book_id + 1)
            else:
                self.id = "1"

        if self.date_started and self.date_completed:
            ds = datetime.fromisoformat(self.date_started)
            dc = datetime.fromisoformat(self.date_completed)
            self.days_to_read = (dc - ds).days + 1  # inclusive
        else:
            self.days_to_read = None


class BookStats:
    """
    Class to generate stats for books read, based on date_completed
    """

    def __init__(self, books: list[Book]):
        self.books = books
        self.ymd = [self.get_ymd(book) for book in books]

    def get_ymd(self, book: Book) -> Optional[tuple[int, int, int]]:
        if book.days_to_read and book.date_completed:
            ymd = datetime.fromisoformat(book.date_completed)
            return (
                ymd.year,
                ymd.month,
                book.days_to_read,
            )
        return None

    def flatten(self, lst: list) -> list:
        out = []
        for item in lst:
            if isinstance(item, list):
                out.extend(self.flatten(item))
            else:
                out.append(item)
        return out

    def detailed_stats(self) -> list[dict]:
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

    def year_stats(self, year: int, detailed: bool = False) -> list[dict]:
        books_read = [book for book in self.ymd if book and book[0] == year]
        count = len(books_read)
        if count:
            avg_days_to_read = round(mean([book[2] for book in books_read]), 2)
        else:
            avg_days_to_read = None
        if detailed:
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


def write_book(book: Book) -> None:
    path = Path(DB_PATH)
    book_dict = asdict(book)
    del book_dict["days_to_read"]  # Do not store this field
    if path.is_file():
        with open(path, "a", newline="\n") as f:
            writer = csv.writer(f)
            writer.writerow(book_dict.values())
    else:
        with open(path, "w", newline="\n") as f:
            fieldnames = list(book_dict.keys())
            writer = csv.writer(f)
            writer.writerow(fieldnames)
            writer.writerow(book_dict)
    print(f"Added {book.title} by {book.author} to book_db.csv")


def read_books(path: Path = Path(DB_PATH)) -> list[Book]:
    if path.is_file():
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            return [
                Book(
                    id=row["id"],
                    title=row["title"],
                    author=row["author"],
                    status=Status[row["status"]],
                    date_started=row["date_started"],
                    date_completed=row["date_completed"],
                )
                for row in reader
            ]
    return []


def filter_books(field: str | None = None, value: str | None = None) -> list[Book]:
    books = read_books()
    if field and value:
        return [b for b in books if value.lower() in str(getattr(b, field).lower())]
    return books


def get_book_by_id(id: str) -> Optional[Book]:
    book = filter_books(field="id", value=id)
    if book:
        return book[0]
    else:
        print(f"There is no book with {id=}")
        return None


def write_books(books: list[dict]) -> None:
    with open(DB_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(list(books[0].keys()))
        for book in books:
            writer.writerow(list(book.values()))


def edit_book(id: str) -> None:
    book = get_book_by_id(id)
    if book:
        book_dict = asdict(book)
        del book_dict["days_to_read"]
        for k, v in book_dict.items():
            data = input(f"Edit {k} ({v}): ")
            if data:
                book_dict[k] = data
            else:
                book_dict[k] = v
        books = [asdict(b) for b in read_books() if b.id != id]
        books.append(book_dict)
        write_books(books)


def delete_book(id: str) -> None:
    book = get_book_by_id(id)
    if book:
        title = f"[bright_green]{book.title}[/bright_green]"
        author = f"[bright_blue]{book.author}[/bright_blue]"
        query = Confirm.ask(
            f"Are you sure you want to delete {title} by {author}? (y/n): "
        )
        if query:
            books = [asdict(b) for b in read_books() if b.id != id]
            write_books(books)
            print(f"Deleting {title} by {author}")


def main():
    parser = argparse.ArgumentParser(
        prog="booktracker", description="Track books read and to be read"
    )
    subparsers = parser.add_subparsers(dest="command")

    # ADD BOOK
    add_parser = subparsers.add_parser("add", help="Add a new book")
    add_parser.add_argument("title", type=str, help="Title")
    add_parser.add_argument("author", type=str, help="Author (Lastname, Firstname)")
    add_parser.add_argument(
        "-s",
        "--status",
        type=str,
        choices=[*Status],
        default="TBR",
        help="Status",
    )
    add_parser.add_argument(
        "-d",
        "--date-started",
        type=str,
        action=DateAction,
        default=None,
        help="Use format: 'YYYY-MM-DD'",
    )
    add_parser.add_argument(
        "-c",
        "--date-completed",
        type=str,
        action=DateAction,
        default=None,
        help="Use format: 'YYYY-MM-DD'",
    )

    # READ BOOKS
    read_parser = subparsers.add_parser("read", help="View existing books")
    read_parser.add_argument(
        "-f",
        "--field",
        type=str,
        help="Field to search",
        choices=["id", "title", "author", "status", "date_started", "date_completed"],
    )
    read_parser.add_argument("-v", "--value", type=str, help="Search term")

    # EDIT BOOKS
    edit_parser = subparsers.add_parser("edit", help="Edit a book using its ID")
    edit_parser.add_argument("id", type=str, help="id of book to edit")

    # DELETE BOOK
    delete_parser = subparsers.add_parser("delete", help="Delete a book using its ID")
    delete_parser.add_argument("id", type=str, help="id of book to delete")

    # STATS
    stats_parser = subparsers.add_parser(
        "stats", help="Generate statistics for books completed"
    )
    stats_parser.add_argument(
        "--detailed",
        action=argparse.BooleanOptionalAction,
        help="Print detailed stats",
    )
    stats_parser.add_argument("-y", "--year", type=int, action=YearAction, default=None)
    stats_parser.add_argument(
        "-m", "--month", type=int, action=MonthAction, default=None, help="1 - 12"
    )

    args = parser.parse_args()

    if args.command == "add":
        new_book = Book(
            title=args.title,
            author=args.author,
            status=args.status,
            date_started=args.date_started,
            date_completed=args.date_completed,
        )
        write_book(new_book)
    elif args.command == "read":
        if args.field and args.value:
            books = filter_books(args.field, args.value)
        else:
            books = read_books()
        if books:
            columns = asdict(books[0]).keys()
            colors = [
                "white",
                "bright_green",
                "bright_blue",
                "bright_red",
                "bright_magenta",
                "cyan3",
                "orange1",
            ]
            rows = [map(str, asdict(book).values()) for book in books]
            table = Table(title="BookTracker", box=box.ROUNDED)
            for column, color in zip(columns, colors):
                table.add_column(column, style=color)
            for row in rows:
                table.add_row(*row)
            console.print(table)
        else:
            print("There are no books available with that search criteria.")
    elif args.command == "edit":
        if args.id:
            edit_book(args.id)
    elif args.command == "delete":
        if args.id:
            delete_book(args.id)
    elif args.command == "stats":
        books = read_books()
        if books:
            stats = BookStats(books)
        if not any([args.detailed, args.year, args.month]):
            print("Choose --detailed, --year, and/or --month to print stats.")
        if args.year and not args.month:
            if args.detailed:
                stats.print_rich_table(
                    stats.year_stats(year=args.year, detailed=args.detailed)
                )
            else:
                stats.print_rich_table(stats.year_stats(year=args.year))
        if args.year and args.month:
            stats.print_rich_table(stats.month_stats(year=args.year, month=args.month))
        if args.month and not args.year:
            print("You must provide a year and a month.")
        if args.detailed and not args.year:
            stats.print_rich_table(stats.detailed_stats())


if __name__ == "__main__":
    main()

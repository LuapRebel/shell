import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from statistics import mean

from rich import print
from rich.console import Console
from rich.table import Table

DIR = Path(__file__).parent.resolve()
DB_PATH = DIR / "books.csv"

console = Console()


class Status(StrEnum):
    TBR = "TBR"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


@dataclass
class Book:
    title: str = ""
    author: str = ""
    status: Status = "TBR"
    date_started: date | None = None
    date_completed: date | None = None
    id: int | None = None
    days_to_read: int | None = None

    def __post_init__(self):
        if not self.id:
            books = read_books()
            if books:
                last_book_id = int(books[-1].id)
                self.id = last_book_id + 1
            else:
                self.id = 1

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
        table = Table(title="BookTracker Statistics")
        columns = stats[0].keys()
        for column in columns:
            table.add_column(column)
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
            fieldnames = list(Book.__annotations__)
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(book_dict)
    print(f"Added {book.title} by {book.author} to book_db.csv")


def read_books(path: Path = Path(DB_PATH)) -> list[Book]:
    if path.is_file():
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            return [Book(**row) for row in reader]
    return []


def filter_books(field: str | None = None, value: str | None = None) -> list[Book]:
    books = read_books()
    if field and value:
        return [b for b in books if value.lower() in str(getattr(b, field).lower())]
    return books


def get_book_by_id(id: str) -> Book:
    book = filter_books(field="id", value=id)
    if book:
        return book[0]
    else:
        print(f"There is no book with {id=}")


def write_books(books: list[dict]) -> None:
    with open(DB_PATH, "w", newline="") as f:
        dict_writer = csv.DictWriter(f, fieldnames=list(Book.__annotations__))
        dict_writer.writeheader()
        dict_writer.writerows(books)


def edit_book(id: str) -> None:
    book = asdict(get_book_by_id(id))
    del book["days_to_read"]
    if book:
        for k, v in book.items():
            data = input(f"Edit {k} ({v}): ")
            if data:
                book[k] = data
            else:
                book[k] = v
        books = [asdict(b) for b in read_books() if b.id != id]
        books.append(book)
        write_books(books)


def delete_book(id: str) -> None:
    book = get_book_by_id(id)
    if book:
        books = [asdict(b) for b in read_books() if b.id != id]
        write_books(books)
        print(f"Deleted {book.title} by {book.author}")


parser = argparse.ArgumentParser(
    prog="booktracker", description="Track books read and to be read"
)
subparsers = parser.add_subparsers(dest="command")

# ADD BOOK
add_parser = subparsers.add_parser("add", help="Add a new book")
add_parser.add_argument("title", type=str, help="Title")
add_parser.add_argument("author", type=str, help="Author")
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
    type=date.fromisoformat,
    default=None,
    help="DDDD-MM-YY",
)
add_parser.add_argument(
    "-c",
    "--date-completed",
    type=date.fromisoformat,
    default=None,
    help="DDDD-MM-YY",
)

# READ BOOKS
read_parser = subparsers.add_parser("read", help="View existing books")
read_parser.add_argument("-f", "--field", type=str)
read_parser.add_argument("-v", "--value", type=str)

# EDIT BOOKS
edit_parser = subparsers.add_parser("edit", help="Edit a book using its ID")
edit_parser.add_argument("id", type=str)

# DELETE BOOK
delete_parser = subparsers.add_parser("delete", help="Delete a book using its ID")
delete_parser.add_argument("id", type=str)

# STATS
stats_parser = subparsers.add_parser(
    "stats", help="Generate statistics for books completed"
)
stats_parser.add_argument("--complete", action=argparse.BooleanOptionalAction)
stats_parser.add_argument("-y", "--year", type=int, default=None)
stats_parser.add_argument("-m", "--month", type=int, default=None)

args = parser.parse_args()

if args.command == "add":
    new_book = Book(
        args.title, args.author, args.status, args.date_started, args.date_completed
    )
    write_book(new_book)
elif args.command == "read":
    if args.field and args.value:
        books = filter_books(args.field, args.value)
    else:
        books = read_books()
    if books:
        rows = [map(str, asdict(book).values()) for book in books]
        columns = asdict(books[0]).keys()
        table = Table(title="BookTracker")
        for column in columns:
            table.add_column(column)
        for row in rows:
            table.add_row(*row)
        console.print(table)
    else:
        print("There are no books available.")
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
    if not any([args.complete, args.year, args.month]):
        print("Choose --complete, --year, and/or --month to print stats.")
    if args.year and not args.month:
        if args.complete:
            stats.print_rich_table(
                stats.year_stats(year=args.year, complete=args.complete)
            )
        else:
            stats.print_rich_table(stats.year_stats(year=args.year))
    if args.year and args.month:
        stats.print_rich_table(stats.month_stats(year=args.year, month=args.month))
    if args.month and not args.year:
        print("You must provide a year and a month.")
    if args.complete and not args.year:
        stats.print_rich_table(stats.complete_stats())

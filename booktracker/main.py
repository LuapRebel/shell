import argparse
import csv
from dataclasses import asdict, dataclass, field
from datetime import date
from enum import StrEnum
from pathlib import Path

from rich import print


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
    id: int = field(init=False)

    def __post_init__(self):
        books = read_books()
        if books:
            last_book_id = int(books[-1]["id"])
            self.id = last_book_id + 1
        else:
            self.id = 1


def read_books(path: Path = Path("booktracker/book_db.csv")) -> list[dict]:
    if path.is_file():
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            return [row for row in reader]
    return []


def filter_books(field: str | None = None, value: str | None = None) -> list[dict]:
    books = read_books()
    if field and value:
        return [b for b in books if value in str(b[field])]
    return books


def write_book(book: Book) -> None:
    path = Path("booktracker/book_db.csv")
    book_dict = asdict(book)
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

args = parser.parse_args()

if args.command == "add":
    new_book = Book(
        args.title, args.author, args.status, args.date_started, args.date_completed
    )
    write_book(new_book)
elif args.command == "read":
    if args.field and args.value:
        print(filter_books(args.field, args.value))
    else:
        print(filter_books())

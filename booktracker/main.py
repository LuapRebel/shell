import argparse
import csv
from dataclasses import dataclass
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
    title: str
    author: str
    status: Status = "TBR"
    date_started: date | None = None
    date_completed: date | None = None


def write_book(book: Book) -> None:
    path = Path("booktracker/book_db.csv")
    if path.is_file():
        with open(path, "a", newline="\n") as f:
            writer = csv.writer(f)
            writer.writerow(book.__dict__.values())
    else:
        with open(path, "w", newline="\n") as f:
            fieldnames = list(Book.__annotations__)
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(book.__dict__)
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

args = parser.parse_args()

if args.command == "add":
    new_book = Book(
        args.title, args.author, args.status, args.date_started, args.date_completed
    )
    write_book(new_book)

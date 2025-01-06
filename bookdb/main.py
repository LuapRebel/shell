from dataclasses import dataclass
from datetime import date
from enum import StrEnum
import sqlite3


DB_PATH = "bookdb/books.db"
CONN = sqlite3.connect(DB_PATH)

CONN.execute(
    """
    CREATE TABLE IF NOT EXISTS books(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        status TEXT,
        author TEXT,
        date_started TEXT,
        date_completed TEXT
    )
    """
)
CONN.close()


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

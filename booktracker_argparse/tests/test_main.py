from pathlib import Path
import pytest

from ..src.main import Book

DB_PATH = Path(__file__).parent.resolve() / "testdata.csv"


@pytest.mark.parametrize(
    "date_completed,expected",
    [("2025-01-02", 2), ("", None), (None, None)],
)
def test_book_days_to_read(date_completed, expected):
    book = Book(
        title="TITLE",
        author="AUTHOR",
        status="TBR",
        date_started="2025-01-01",
        date_completed=date_completed,
    )
    assert book.days_to_read == expected

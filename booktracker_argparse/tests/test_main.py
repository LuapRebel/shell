from pathlib import Path
import pytest


DB_PATH = Path(__file__).parent.resolve() / "testdata.csv"


def test_path():
    assert DB_PATH.is_file()

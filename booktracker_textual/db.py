from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class Book(BaseModel):
    id: Optional[int] = None
    title: str = ""
    author: str = ""
    status: Literal["TBR", "IN_PROGRESS", "COMPLETED"] = "TBR"
    date_started: date | str = ""
    date_completed: date | str = ""

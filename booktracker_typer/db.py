from datetime import datetime
import re
from typing import Literal, Optional
from typing_extensions import Self

from pydantic import (
    BaseModel,
    computed_field,
    field_validator,
    model_validator,
    ValidationError,
)


class Book(BaseModel, extra="allow"):
    id: Optional[int] = None
    title: str = ""
    author: str = ""
    status: Literal["TBR", "IN_PROGRESS", "COMPLETED"] = "TBR"
    date_started: str = ""
    date_completed: str = ""

    @field_validator("date_started", "date_completed", mode="before")
    @classmethod
    def validate_date(cls, value: str) -> str:
        if value:
            if re.match("[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                return value
            else:
                raise ValidationError("dates must be formatted as 'YYYY-MM-DD'.")
        return ""

    @model_validator(mode="after")
    def validate_date_completed(self) -> Self:
        if self.date_started and self.date_completed:
            if datetime.fromisoformat(self.date_completed) >= datetime.fromisoformat(
                self.date_started
            ):
                return self
            else:
                raise ValidationError("date_completed must be after date_started.")
        return self

    @computed_field
    @property
    def days_to_read(self) -> int | None:
        if self.date_started and self.date_completed:
            ds = datetime.strptime(self.date_started, "%Y-%m-%d")
            dc = datetime.strptime(self.date_completed, "%Y-%m-%d")
            return (dc - ds).days + 1

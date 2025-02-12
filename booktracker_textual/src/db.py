from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, computed_field


class Book(BaseModel, extra="allow"):
    id: Optional[int] = None
    title: str = ""
    author: str = ""
    status: Literal["TBR", "IN_PROGRESS", "COMPLETED"] = "TBR"
    date_started: str | None = None
    date_completed: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days_to_read(self) -> Optional[int]:
        if self.date_started and self.date_completed:
            ds = datetime.strptime(self.date_started, "%Y-%m-%d")
            dc = datetime.strptime(self.date_completed, "%Y-%m-%d")
            return (dc - ds).days + 1  # inclusive
        else:
            return None

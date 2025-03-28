from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class FileInfo(BaseModel):
    name: str
    path: str
    size: int
    is_dir: bool
    modified_time: datetime
    children: Optional[List["FileInfo"]] = None
    parent_path: Optional[str] = None
    depth: int = 0

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        data["modified_time"] = self.modified_time.isoformat()
        return data

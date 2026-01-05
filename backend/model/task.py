from datetime import datetime

from pydantic import BaseModel

from app.agent.manus import Manus


class Task(BaseModel):
    id: str
    created_at: datetime
    request: str
    agent: "Manus"

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        data["created_at"] = self.created_at.isoformat()
        return data

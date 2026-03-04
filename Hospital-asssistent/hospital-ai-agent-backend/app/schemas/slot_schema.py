from pydantic import BaseModel
from datetime import datetime


class SlotResponse(BaseModel):
    id: int
    start_time: datetime
    end_time: datetime

    class Config:
        from_attributes = True
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class TravelProfile(BaseModel):
    destination: Optional[str] = None
    days: Optional[int] = Field(default=None, ge=1, le=30)
    budget: Optional[float] = Field(default=None, gt=0)
    travelers: int = Field(default=1, ge=1, le=20)
    preferences: list[str] = Field(default_factory=list)
    departure: Optional[str] = None
    start_date: Optional[date] = None

    @property
    def missing(self) -> list[str]:
        fields = []
        if not self.destination:
            fields.append("目的地")
        if not self.days:
            fields.append("旅行天数")
        if not self.budget:
            fields.append("总预算")
        if not self.preferences:
            fields.append("兴趣偏好")
        return fields


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    status: str
    profile: TravelProfile
    sources: list[str] = Field(default_factory=list)

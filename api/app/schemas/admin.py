from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class AdminLoginResponse(BaseModel):
    token: str
    refresh_token: str


class CropStats(BaseModel):
    crop: str
    count: int


class AnalyticsResponse(BaseModel):
    total_diagnoses: int
    low_confidence_count: int
    crop_stats: List[CropStats]

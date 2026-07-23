from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Prediction(BaseModel):
    class_id: int
    crop: str
    disease: str
    is_healthy: bool
    confidence: float = Field(ge=0, le=100)


class DiagnosisResponse(BaseModel):
    diagnosis_id: str
    results: List[Prediction]
    thumbnail_url: Optional[str]
    advisory: Optional[dict]
    low_confidence: bool
    created_at: datetime


class DiagnosisRequest(BaseModel):
    crop_hint: Optional[str] = None
    retrain_consent: bool = False

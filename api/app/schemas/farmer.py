from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FarmerResponse(BaseModel):
    farmer_id: str
    device_identifier: str
    phone_number: Optional[str]
    preferred_language: str
    registration_date: datetime


class DiagnosisHistoryResponse(BaseModel):
    diagnosis_id: str
    predicted_class_id: Optional[int]
    confidence_score: Optional[float]
    top3_predictions: Optional[dict]
    created_at: datetime

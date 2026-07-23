from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DiseaseResponse(BaseModel):
    class_id: int
    crop_name: str
    disease_name: str
    is_healthy: bool
    description: Optional[str]


class AdvisoryResponse(BaseModel):
    recommended_action: str
    local_treatment_options: Optional[str]


class DiseaseCreate(BaseModel):
    crop_name: str = Field(..., min_length=1, max_length=50)
    disease_name: str = Field(..., min_length=1, max_length=100)
    is_healthy: bool = False
    description: Optional[str] = None


class DiseaseUpdate(BaseModel):
    crop_name: Optional[str] = Field(None, min_length=1, max_length=50)
    disease_name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_healthy: Optional[bool] = None
    description: Optional[str] = None

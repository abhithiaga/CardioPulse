from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class Sex(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


class CardiovascularRiskFactor(str, Enum):
    HYPERTENSION = "hypertension"
    DIABETES = "diabetes"
    SMOKING = "smoking"
    HYPERLIPIDEMIA = "hyperlipidemia"
    OBESITY = "obesity"
    FAMILY_HISTORY = "family_history_cvd"
    PRIOR_MI = "prior_mi"
    HEART_FAILURE = "heart_failure"
    ATRIAL_FIBRILLATION = "atrial_fibrillation"
    CKD = "chronic_kidney_disease"


class Patient(BaseModel):
    id: Optional[str] = None
    mrn: str                        # Medical Record Number
    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex
    email: Optional[EmailStr] = None

    # Clinical context
    risk_factors: List[CardiovascularRiskFactor] = []
    current_medications: List[str] = []
    allergies: List[str] = []
    attending_physician: Optional[str] = None
    notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def age(self) -> int:
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class PatientCreate(BaseModel):
    mrn: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex
    email: Optional[EmailStr] = None
    risk_factors: List[CardiovascularRiskFactor] = []
    current_medications: List[str] = []
    allergies: List[str] = []
    attending_physician: Optional[str] = None
    notes: Optional[str] = None


class PatientSummary(BaseModel):
    """Lightweight version for list views"""
    id: str
    mrn: str
    full_name: str
    age: int
    sex: Sex
    risk_factor_count: int
    last_ecg_date: Optional[datetime] = None
    last_risk_level: Optional[str] = None
    ecg_count: int = 0

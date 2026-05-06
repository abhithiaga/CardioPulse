import uuid
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import date
from app.models.patient import Patient, PatientCreate, PatientSummary

router = APIRouter()

# In-memory — replace with DynamoDB
_patients: dict = {}

# Seed with realistic demo patients
def _seed():
    demo = [
        {
            "id": "pt-001", "mrn": "MRN-10001", "first_name": "James", "last_name": "Holloway",
            "date_of_birth": "1958-03-14", "sex": "M",
            "risk_factors": ["hypertension", "diabetes", "smoking"],
            "current_medications": ["Metoprolol", "Lisinopril", "Metformin"],
            "attending_physician": "Dr. Sarah Chen",
        },
        {
            "id": "pt-002", "mrn": "MRN-10002", "first_name": "Maria", "last_name": "Santos",
            "date_of_birth": "1965-07-22", "sex": "F",
            "risk_factors": ["hyperlipidemia", "family_history_cvd"],
            "current_medications": ["Atorvastatin"],
            "attending_physician": "Dr. Sarah Chen",
        },
        {
            "id": "pt-003", "mrn": "MRN-10003", "first_name": "David", "last_name": "Park",
            "date_of_birth": "1947-11-05", "sex": "M",
            "risk_factors": ["hypertension", "prior_mi", "heart_failure", "atrial_fibrillation"],
            "current_medications": ["Warfarin", "Furosemide", "Carvedilol", "Digoxin"],
            "attending_physician": "Dr. Marcus Webb",
        },
        {
            "id": "pt-004", "mrn": "MRN-10004", "first_name": "Aisha", "last_name": "Patel",
            "date_of_birth": "1982-01-30", "sex": "F",
            "risk_factors": [],
            "current_medications": [],
            "attending_physician": "Dr. Marcus Webb",
        },
    ]
    from datetime import datetime
    for d in demo:
        dob = date.fromisoformat(d.pop("date_of_birth"))
        p = Patient(**d, date_of_birth=dob)
        _patients[p.id] = p.dict()

_seed()


@router.post("/", response_model=Patient)
async def create_patient(payload: PatientCreate):
    patient_id = str(uuid.uuid4())[:8]
    patient = Patient(id=f"pt-{patient_id}", **payload.dict())
    _patients[patient.id] = patient.dict()
    return patient


@router.get("/", response_model=List[dict])
async def list_patients(
    search: Optional[str] = Query(None),
    physician: Optional[str] = Query(None),
    limit: int = Query(default=50, le=500),
):
    patients = list(_patients.values())
    if search:
        q = search.lower()
        patients = [p for p in patients if
                    q in p.get("first_name", "").lower() or
                    q in p.get("last_name", "").lower() or
                    q in p.get("mrn", "").lower()]
    if physician:
        patients = [p for p in patients if p.get("attending_physician") == physician]
    return patients[:limit]


@router.get("/{patient_id}", response_model=dict)
async def get_patient(patient_id: str):
    p = _patients.get(patient_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return p


@router.put("/{patient_id}", response_model=dict)
async def update_patient(patient_id: str, payload: PatientCreate):
    if patient_id not in _patients:
        raise HTTPException(status_code=404, detail="Patient not found")
    existing = _patients[patient_id]
    updated = {**existing, **payload.dict(), "id": patient_id}
    _patients[patient_id] = updated
    return updated


@router.delete("/{patient_id}", response_model=dict)
async def delete_patient(patient_id: str):
    if patient_id not in _patients:
        raise HTTPException(status_code=404, detail="Patient not found")
    del _patients[patient_id]
    return {"status": "deleted", "id": patient_id}

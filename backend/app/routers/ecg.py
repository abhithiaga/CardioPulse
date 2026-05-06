from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.models.ecg import ECGUploadRequest, ECGAnalysisResult, ECGLead
from app.services.risk_engine import RiskEngine
from app.services.ecg_processor import ECGProcessor

router = APIRouter()
risk_engine = RiskEngine()
processor = ECGProcessor()


@router.post("/analyze", response_model=ECGAnalysisResult)
async def analyze_ecg(payload: ECGUploadRequest):
    """
    Full ECG analysis pipeline: ingest raw lead data → extract metrics → ML risk score.
    Returns complete diagnosis with annotations for dashboard rendering.
    """
    try:
        if not payload.leads:
            raise HTTPException(status_code=422, detail="At least one ECG lead is required")
        result = await risk_engine.analyze(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo", response_model=ECGAnalysisResult)
async def analyze_demo_ecg(
    patient_id: str = Query(default="demo-patient"),
    heart_rate: float = Query(default=75),
    noise: float = Query(default=0.02),
):
    """
    Generate a synthetic ECG and run full analysis — for demo and testing.
    Adjust heart_rate and noise to see different risk profiles.
    """
    signal = processor.generate_synthetic_ecg(
        duration_seconds=10, heart_rate=heart_rate, noise_level=noise
    )
    leads = [ECGLead(name="Lead II", samples=signal, sample_rate=500)]
    payload = ECGUploadRequest(patient_id=patient_id, leads=leads)
    result = await risk_engine.analyze(payload)
    return result


@router.get("/records", response_model=List[dict])
async def list_ecg_records(limit: int = Query(default=50, le=500)):
    """List all ECG records across all patients (for dashboard)."""
    return risk_engine.get_all_records(limit=limit)


@router.get("/patient/{patient_id}", response_model=List[dict])
async def get_patient_ecg_history(patient_id: str):
    """Get all ECG records for a specific patient."""
    return risk_engine.get_patient_history(patient_id)


@router.get("/waveform/synthetic")
async def get_synthetic_waveform(
    heart_rate: float = Query(default=75, ge=30, le=250),
    duration: float = Query(default=10, ge=2, le=30),
    noise: float = Query(default=0.02, ge=0, le=0.5),
):
    """Return a raw synthetic ECG waveform for chart rendering."""
    signal = processor.generate_synthetic_ecg(
        duration_seconds=duration, heart_rate=heart_rate, noise_level=noise
    )
    t = [round(i / 500, 4) for i in range(len(signal))]
    return {"time": t, "amplitude": signal, "sample_rate": 500, "heart_rate": heart_rate}

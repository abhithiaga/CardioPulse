from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class RhythmType(str, Enum):
    NORMAL_SINUS = "Normal Sinus Rhythm"
    AFIB = "Atrial Fibrillation"
    VTACH = "Ventricular Tachycardia"
    BRADYCARDIA = "Bradycardia"
    TACHYCARDIA = "Sinus Tachycardia"
    HEART_BLOCK = "Heart Block"
    FLUTTER = "Atrial Flutter"
    PVC = "Premature Ventricular Contractions"
    UNKNOWN = "Unknown"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ECGLead(BaseModel):
    """Single ECG lead signal data"""
    name: str                        # e.g. "Lead I", "Lead II", "V1"..
    samples: List[float]             # raw mV values
    sample_rate: int = 500           # Hz


class ECGUploadRequest(BaseModel):
    patient_id: str
    leads: List[ECGLead]
    duration_seconds: float = 10.0
    recorded_at: Optional[datetime] = None
    device_id: Optional[str] = None
    notes: Optional[str] = None


class ECGMetrics(BaseModel):
    """Computed ECG feature metrics"""
    heart_rate_bpm: float
    pr_interval_ms: Optional[float] = None
    qrs_duration_ms: Optional[float] = None
    qt_interval_ms: Optional[float] = None
    qtc_interval_ms: Optional[float] = None   # Corrected QT
    st_deviation_mv: Optional[float] = None
    p_wave_amplitude_mv: Optional[float] = None
    r_wave_amplitude_mv: Optional[float] = None
    rr_variability_ms: Optional[float] = None  # HRV proxy
    rhythm: RhythmType = RhythmType.UNKNOWN
    is_regular: bool = True
    abnormalities: List[str] = []


class ECGRecord(BaseModel):
    id: Optional[str] = None
    patient_id: str
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: float
    sample_rate: int = 500
    lead_count: int
    metrics: Optional[ECGMetrics] = None
    risk_level: Optional[RiskLevel] = None
    risk_score: Optional[float] = None
    diagnosis_labels: List[str] = []
    reviewed: bool = False
    reviewed_by: Optional[str] = None
    notes: Optional[str] = None


class ECGAnalysisResult(BaseModel):
    ecg_id: str
    patient_id: str
    metrics: ECGMetrics
    risk_score: float          # 0.0 – 1.0
    risk_level: RiskLevel
    diagnosis_labels: List[str]
    confidence: float          # model confidence 0–1
    feature_importances: Dict[str, float] = {}
    waveform_annotations: List[Dict] = []   # for chart overlays
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    processing_ms: Optional[float] = None

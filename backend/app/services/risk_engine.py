"""
Risk Engine — orchestrates ECG processing + ML scoring into a full analysis result.
"""
import time
import uuid
from datetime import datetime
from typing import List

from app.models.ecg import (
    ECGUploadRequest, ECGAnalysisResult, ECGMetrics, RiskLevel, ECGLead
)
from app.models.patient import Patient
from app.services.ecg_processor import ECGProcessor
from app.services.ml_service import MLService
from app.config import settings

processor = ECGProcessor()
ml_service = MLService()

# In-memory store — swap for DynamoDB in production
_ecg_store: List[dict] = []


class RiskEngine:

    async def analyze(self, request: ECGUploadRequest, patient: Patient = None) -> ECGAnalysisResult:
        """Full pipeline: raw leads → metrics → ML → risk result."""
        t0 = time.time()

        # 1. Extract ECG metrics
        metrics: ECGMetrics = processor.process(request.leads)

        # 2. Patient context
        age = patient.age if patient else 55
        rf_count = len(patient.risk_factors) if patient else 0

        # 3. ML inference
        risk_score, confidence, labels = ml_service.predict(metrics, age=age, rf_count=rf_count)
        feature_importances = ml_service.get_feature_importances(metrics, age, rf_count)

        # 4. Risk level classification
        risk_level = self._classify_risk(risk_score)

        # 5. Waveform annotations for chart overlay
        annotations = self._build_annotations(metrics)

        processing_ms = (time.time() - t0) * 1000

        ecg_id = str(uuid.uuid4())

        result = ECGAnalysisResult(
            ecg_id=ecg_id,
            patient_id=request.patient_id,
            metrics=metrics,
            risk_score=round(risk_score, 4),
            risk_level=risk_level,
            diagnosis_labels=labels,
            confidence=round(confidence, 4),
            feature_importances=feature_importances,
            waveform_annotations=annotations,
            analyzed_at=datetime.utcnow(),
            processing_ms=round(processing_ms, 1),
        )

        # Persist record
        _ecg_store.append({
            "id": ecg_id,
            "patient_id": request.patient_id,
            "result": result.dict(),
            "recorded_at": (request.recorded_at or datetime.utcnow()).isoformat(),
        })

        return result

    def _classify_risk(self, score: float) -> RiskLevel:
        if score >= 0.80:
            return RiskLevel.CRITICAL
        if score >= settings.RISK_THRESHOLD_HIGH:
            return RiskLevel.HIGH
        if score >= settings.RISK_THRESHOLD_MEDIUM:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _build_annotations(self, metrics: ECGMetrics) -> List[dict]:
        """Generate chart overlay annotations for clinician dashboard."""
        annotations = []
        if metrics.st_deviation_mv and abs(metrics.st_deviation_mv) > 0.1:
            annotations.append({
                "type": "ST_change",
                "label": f"ST {'↑' if metrics.st_deviation_mv > 0 else '↓'} {abs(metrics.st_deviation_mv):.2f}mV",
                "severity": "high" if abs(metrics.st_deviation_mv) > 0.2 else "medium",
            })
        if metrics.qtc_interval_ms and metrics.qtc_interval_ms > 450:
            annotations.append({
                "type": "QTc_prolonged",
                "label": f"QTc {metrics.qtc_interval_ms:.0f}ms",
                "severity": "high",
            })
        if metrics.qrs_duration_ms and metrics.qrs_duration_ms > 120:
            annotations.append({
                "type": "wide_QRS",
                "label": f"QRS {metrics.qrs_duration_ms:.0f}ms",
                "severity": "medium",
            })
        return annotations

    def get_patient_history(self, patient_id: str) -> List[dict]:
        records = [r for r in _ecg_store if r["patient_id"] == patient_id]
        return sorted(records, key=lambda x: x.get("recorded_at", ""), reverse=True)

    def get_all_records(self, limit: int = 100) -> List[dict]:
        return sorted(_ecg_store, key=lambda x: x.get("recorded_at", ""), reverse=True)[:limit]

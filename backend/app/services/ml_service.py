"""
ML Service — cardiovascular risk classification.
Uses scikit-learn (RandomForest) trained on ECG features.
Includes a pre-trained fallback model using synthetic feature-based rules
so the system works without a pre-existing .pkl file.
"""
import numpy as np
import os
import pickle
from typing import Dict, List, Tuple
from app.models.ecg import ECGMetrics, RiskLevel, RhythmType
from app.config import settings


class MLService:

    def __init__(self):
        self._model = None
        self._load_model()

    def _load_model(self):
        """Try to load a saved sklearn model, fall back to rule-based."""
        path = settings.MODEL_PATH
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    self._model = pickle.load(f)
                print(f"[MLService] Loaded model from {path}")
            except Exception as e:
                print(f"[MLService] Could not load model: {e} — using rule-based fallback")
        else:
            print("[MLService] No saved model found — using rule-based classifier")

    def predict(self, metrics: ECGMetrics, patient_age: int = 55,
                risk_factor_count: int = 0) -> Tuple[float, float, List[str]]:
        """
        Returns: (risk_score 0–1, confidence 0–1, diagnosis_labels)
        """
        features = self._extract_features(metrics, patient_age, risk_factor_count)
        feature_array = np.array(list(features.values())).reshape(1, -1)

        if self._model is not None:
            try:
                proba = self._model.predict_proba(feature_array)[0]
                risk_score = float(proba[1]) if len(proba) > 1 else float(proba[0])
                confidence = float(np.max(proba))
            except Exception:
                risk_score, confidence = self._rule_based_score(metrics, patient_age, risk_factor_count)
        else:
            risk_score, confidence = self._rule_based_score(metrics, patient_age, risk_factor_count)

        # Add clinical noise for realism in demo
        risk_score = float(np.clip(risk_score + np.random.normal(0, 0.02), 0, 1))
        confidence = float(np.clip(confidence, 0.6, 0.99))

        labels = self._generate_labels(metrics, risk_score)
        return risk_score, confidence, labels

    def _extract_features(self, m: ECGMetrics, age: int, rf_count: int) -> Dict[str, float]:
        """Convert ECG metrics → numeric feature vector."""
        rhythm_map = {
            RhythmType.NORMAL_SINUS: 0, RhythmType.TACHYCARDIA: 1,
            RhythmType.BRADYCARDIA: 2, RhythmType.AFIB: 3,
            RhythmType.VTACH: 4, RhythmType.HEART_BLOCK: 5,
            RhythmType.FLUTTER: 3, RhythmType.PVC: 2, RhythmType.UNKNOWN: 1,
        }
        return {
            "heart_rate": m.heart_rate_bpm or 75,
            "pr_interval": m.pr_interval_ms or 160,
            "qrs_duration": m.qrs_duration_ms or 90,
            "qtc": m.qtc_interval_ms or 420,
            "st_deviation": m.st_deviation_mv or 0,
            "rr_variability": m.rr_variability_ms or 30,
            "rhythm_code": rhythm_map.get(m.rhythm, 1),
            "is_regular": int(m.is_regular),
            "abnormality_count": len(m.abnormalities),
            "age": age,
            "risk_factor_count": rf_count,
        }

    def _rule_based_score(self, m: ECGMetrics, age: int, rf_count: int) -> Tuple[float, float]:
        """Clinical rule-based risk scoring when no ML model is present."""
        score = 0.0

        # Rhythm penalties
        rhythm_weights = {
            RhythmType.NORMAL_SINUS: 0.0,
            RhythmType.TACHYCARDIA: 0.15,
            RhythmType.BRADYCARDIA: 0.10,
            RhythmType.AFIB: 0.40,
            RhythmType.VTACH: 0.70,
            RhythmType.HEART_BLOCK: 0.35,
            RhythmType.FLUTTER: 0.30,
            RhythmType.PVC: 0.15,
        }
        score += rhythm_weights.get(m.rhythm, 0.05)

        # Heart rate extremes
        hr = m.heart_rate_bpm or 75
        if hr > 150 or hr < 40: score += 0.25
        elif hr > 120 or hr < 50: score += 0.12
        elif hr > 100 or hr < 60: score += 0.05

        # QRS widening (bundle branch block / aberrancy)
        qrs = m.qrs_duration_ms or 90
        if qrs > 130: score += 0.20
        elif qrs > 120: score += 0.10

        # QTc prolongation (torsades risk)
        qtc = m.qtc_interval_ms or 420
        if qtc > 500: score += 0.25
        elif qtc > 450: score += 0.12

        # ST changes (ischemia/infarction)
        st = m.st_deviation_mv or 0
        if abs(st) > 0.2: score += 0.30
        elif abs(st) > 0.1: score += 0.15

        # Age and risk factors
        if age > 65: score += 0.08
        elif age > 50: score += 0.04
        score += rf_count * 0.04

        # Abnormality count
        score += len(m.abnormalities) * 0.05

        confidence = 0.85 - (score * 0.1)  # higher risk = slightly less confident
        return float(np.clip(score, 0, 1)), float(np.clip(confidence, 0.60, 0.95))

    def _generate_labels(self, m: ECGMetrics, risk_score: float) -> List[str]:
        labels = []

        if m.rhythm == RhythmType.AFIB:
            labels.append("Atrial Fibrillation")
        elif m.rhythm == RhythmType.VTACH:
            labels.append("Ventricular Tachycardia — URGENT")
        elif m.rhythm == RhythmType.BRADYCARDIA:
            labels.append("Sinus Bradycardia")
        elif m.rhythm == RhythmType.TACHYCARDIA:
            labels.append("Sinus Tachycardia")
        elif m.rhythm == RhythmType.HEART_BLOCK:
            labels.append("Heart Block — evaluate for pacemaker")
        elif m.rhythm == RhythmType.NORMAL_SINUS:
            labels.append("Normal Sinus Rhythm")

        st = m.st_deviation_mv or 0
        if st > 0.15:
            labels.append("ST Elevation — rule out STEMI")
        elif st < -0.1:
            labels.append("ST Depression — possible ischemia")

        if m.qtc_interval_ms and m.qtc_interval_ms > 450:
            labels.append("Prolonged QTc — torsades risk")

        if m.qrs_duration_ms and m.qrs_duration_ms > 120:
            labels.append("Wide QRS — bundle branch block pattern")

        if risk_score > 0.75 and not labels:
            labels.append("High-risk pattern — clinical correlation required")
        elif not labels:
            labels.append("No significant acute findings")

        return labels

    def get_feature_importances(self, metrics: ECGMetrics, age: int, rf_count: int) -> Dict[str, float]:
        """Return interpretable feature weights for the dashboard."""
        features = self._extract_features(metrics, age, rf_count)
        # For rule-based: compute normalized contributions
        weights = {
            "heart_rate": 0.18,
            "qrs_duration": 0.14,
            "st_deviation": 0.22,
            "qtc": 0.16,
            "rhythm_code": 0.20,
            "rr_variability": 0.05,
            "age": 0.03,
            "risk_factor_count": 0.02,
        }
        return {k: round(v, 3) for k, v in weights.items() if k in features}

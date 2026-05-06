from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import random
import math
from app.services.risk_engine import RiskEngine

router = APIRouter()
risk_engine = RiskEngine()


@router.get("/risk-trend/{patient_id}", response_model=dict)
async def get_risk_trend(
    patient_id: str,
    days: int = Query(default=30, ge=7, le=365),
):
    """Return historical risk score trend for a patient (for dashboard line chart)."""
    history = risk_engine.get_patient_history(patient_id)

    if not history:
        # Generate synthetic trend for demo patients
        trend = _generate_synthetic_trend(patient_id, days)
    else:
        trend = [
            {
                "date": r.get("recorded_at", "")[:10],
                "risk_score": round(r["result"].get("risk_score", 0), 3),
                "risk_level": r["result"].get("risk_level", "low"),
                "heart_rate": r["result"]["metrics"].get("heart_rate_bpm", 75),
            }
            for r in history
        ]

    return {"patient_id": patient_id, "days": days, "trend": trend}


@router.get("/population-stats", response_model=dict)
async def get_population_stats():
    """Aggregate risk statistics across all patients — for main dashboard."""
    records = risk_engine.get_all_records(limit=1000)

    risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    rhythm_counts = {}
    scores = []

    for r in records:
        result = r.get("result", {})
        lvl = result.get("risk_level", "low")
        risk_counts[lvl] = risk_counts.get(lvl, 0) + 1

        rhythm = result.get("metrics", {}).get("rhythm", "Unknown")
        rhythm_counts[rhythm] = rhythm_counts.get(rhythm, 0) + 1

        s = result.get("risk_score")
        if s is not None:
            scores.append(s)

    avg_score = sum(scores) / len(scores) if scores else 0
    high_risk = risk_counts.get("high", 0) + risk_counts.get("critical", 0)

    # Synthetic population if no real records
    if not records:
        return _synthetic_population_stats()

    return {
        "total_analyses": len(records),
        "risk_distribution": risk_counts,
        "rhythm_distribution": rhythm_counts,
        "average_risk_score": round(avg_score, 3),
        "high_risk_count": high_risk,
        "high_risk_pct": round(high_risk / max(len(records), 1) * 100, 1),
    }


@router.get("/alerts", response_model=List[dict])
async def get_alerts(limit: int = Query(default=20, le=100)):
    """Return recent high/critical risk findings for alert panel."""
    records = risk_engine.get_all_records(limit=200)
    alerts = []
    for r in records:
        result = r.get("result", {})
        lvl = result.get("risk_level", "low")
        if lvl in ("high", "critical"):
            alerts.append({
                "ecg_id": r.get("id"),
                "patient_id": r.get("patient_id"),
                "risk_level": lvl,
                "risk_score": result.get("risk_score"),
                "labels": result.get("diagnosis_labels", []),
                "recorded_at": r.get("recorded_at"),
            })
    if not alerts:
        alerts = _synthetic_alerts()
    return alerts[:limit]


# ── Synthetic data generators for demo ────────────────────────────────────────

def _generate_synthetic_trend(patient_id: str, days: int) -> List[dict]:
    """Realistic-looking risk trend with some variation."""
    seed = sum(ord(c) for c in patient_id)
    random.seed(seed)

    base_risk = {"pt-001": 0.62, "pt-002": 0.38, "pt-003": 0.78, "pt-004": 0.15}.get(patient_id, 0.45)
    trend = []
    risk = base_risk

    for i in range(min(days, 30), 0, -1):
        date_str = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        # Realistic drift with clinical events
        drift = random.gauss(0, 0.04)
        risk = max(0.05, min(0.95, risk + drift))

        def lvl(s):
            if s >= 0.80: return "critical"
            if s >= 0.75: return "high"
            if s >= 0.45: return "medium"
            return "low"

        trend.append({
            "date": date_str,
            "risk_score": round(risk, 3),
            "risk_level": lvl(risk),
            "heart_rate": round(random.gauss(75, 10), 0),
        })
    return trend


def _synthetic_population_stats() -> dict:
    return {
        "total_analyses": 248,
        "risk_distribution": {"low": 112, "medium": 87, "high": 38, "critical": 11},
        "rhythm_distribution": {
            "Normal Sinus Rhythm": 163, "Atrial Fibrillation": 42,
            "Sinus Tachycardia": 28, "Bradycardia": 15,
        },
        "average_risk_score": 0.41,
        "high_risk_count": 49,
        "high_risk_pct": 19.8,
    }


def _synthetic_alerts() -> List[dict]:
    now = datetime.utcnow()
    return [
        {
            "ecg_id": "ecg-001", "patient_id": "pt-003",
            "risk_level": "critical", "risk_score": 0.88,
            "labels": ["Ventricular Tachycardia — URGENT"],
            "recorded_at": (now - timedelta(minutes=14)).isoformat(),
        },
        {
            "ecg_id": "ecg-002", "patient_id": "pt-001",
            "risk_level": "high", "risk_score": 0.76,
            "labels": ["Atrial Fibrillation", "ST Depression — possible ischemia"],
            "recorded_at": (now - timedelta(hours=2)).isoformat(),
        },
        {
            "ecg_id": "ecg-003", "patient_id": "pt-002",
            "risk_level": "high", "risk_score": 0.77,
            "labels": ["Prolonged QTc — torsades risk"],
            "recorded_at": (now - timedelta(hours=5)).isoformat(),
        },
    ]

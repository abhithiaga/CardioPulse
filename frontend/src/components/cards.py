from dash import html
import dash_bootstrap_components as dbc
from typing import Optional


def metric_card(label: str, value: str, unit: str = "", status: str = "normal", delta: Optional[str] = None):
    """Single ECG metric display card — styled like a monitor readout."""
    status_colors = {
        "normal": "#22C55E",
        "warning": "#F59E0B",
        "critical": "#EF4444",
        "info": "#00E5FF",
    }
    color = status_colors.get(status, "#88BB99")

    return html.Div([
        html.P(label, className="metric-label"),
        html.Div([
            html.Span(value, className="metric-value", style={"color": color}),
            html.Span(f" {unit}", className="metric-unit") if unit else None,
        ], className="metric-value-row"),
        html.P(delta, className="metric-delta") if delta else None,
    ], className="metric-card")


def alert_card(alert: dict):
    """Critical/high risk alert entry."""
    level = alert.get("risk_level", "medium")
    color_map = {"critical": "#7C3AED", "high": "#EF4444", "medium": "#F59E0B", "low": "#22C55E"}
    color = color_map.get(level, "#88BB99")
    labels = alert.get("labels", [])

    time_str = ""
    recorded = alert.get("recorded_at", "")
    if recorded:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(recorded.replace("Z", "+00:00"))
            now = datetime.utcnow()
            diff = now - dt.replace(tzinfo=None)
            mins = int(diff.total_seconds() / 60)
            time_str = f"{mins}m ago" if mins < 60 else f"{mins//60}h ago"
        except Exception:
            time_str = recorded[:10]

    return html.Div([
        html.Div([
            html.Span(level.upper(), className="alert-badge", style={"borderColor": color, "color": color}),
            html.Span(f"Patient {alert.get('patient_id','?')}", className="alert-patient"),
            html.Span(time_str, className="alert-time"),
        ], className="alert-header"),
        html.Div([
            html.Span(lbl, className="alert-label") for lbl in labels[:2]
        ], className="alert-labels"),
        html.Div([
            html.Span("Score: ", className="alert-score-label"),
            html.Span(f"{alert.get('risk_score', 0):.0%}", className="alert-score",
                      style={"color": color}),
        ], className="alert-score-row"),
    ], className="alert-card", style={"borderLeftColor": color})


def stat_banner(icon: str, label: str, value: str, sub: str = "", color: str = "#00FF7F"):
    return html.Div([
        html.Div(icon, className="stat-icon", style={"color": color}),
        html.Div([
            html.Div(value, className="stat-value", style={"color": color}),
            html.Div(label, className="stat-label"),
            html.Div(sub, className="stat-sub") if sub else None,
        ]),
    ], className="stat-banner")


def patient_row(patient: dict, on_select_id: str = ""):
    """Table row for patient list."""
    rf_count = len(patient.get("risk_factors", []))
    risk_colors = {0: "#22C55E", 1: "#86EFAC", 2: "#F59E0B", 3: "#EF4444"}
    rf_color = risk_colors.get(min(rf_count, 3), "#EF4444")

    return html.Tr([
        html.Td(patient.get("mrn", ""), className="td-mrn"),
        html.Td(f"{patient.get('first_name','')} {patient.get('last_name','')}", className="td-name"),
        html.Td([
            html.Span(str(rf_count), style={"color": rf_color}),
            html.Span(" risk factors", className="text-muted ms-1", style={"fontSize": "11px"}),
        ]),
        html.Td(patient.get("attending_physician", "—"), className="td-physician"),
    ], className="patient-row", id={"type": "patient-row", "index": patient.get("id", "")})

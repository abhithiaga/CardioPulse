import requests
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from src.components.ecg_chart import risk_timeline_chart, feature_importance_chart
from src.components.risk_gauge import risk_gauge

API = "http://localhost:8000/api"

PATIENTS = {
    "pt-001": "James Holloway",
    "pt-002": "Maria Santos",
    "pt-003": "David Park",
    "pt-004": "Aisha Patel",
}


def layout():
    return html.Div([
        html.Div([
            html.H1("Risk Reports", className="page-title"),
            html.P("Detailed cardiovascular risk analysis and longitudinal tracking", className="page-subtitle"),
        ], className="page-header"),

        # Patient selector
        html.Div([
            html.Label("Select Patient", className="form-label-mono"),
            dcc.Dropdown(
                id="risk-patient-select",
                options=[{"label": f"{v} ({k})", "value": k} for k, v in PATIENTS.items()],
                value="pt-003",
                clearable=False,
                className="dropdown-mono",
            ),
        ], className="control-panel mb-3"),

        # Outputs
        html.Div(id="risk-report-content"),
        dcc.Interval(id="risk-interval", interval=60_000, n_intervals=0),
    ], className="page-wrapper")


@callback(
    Output("risk-report-content", "children"),
    Input("risk-patient-select", "value"),
    Input("risk-interval", "n_intervals"),
)
def build_risk_report(patient_id, n):
    if not patient_id:
        return html.P("Select a patient above.", className="text-muted p-3")

    try:
        patient = requests.get(f"{API}/patients/{patient_id}", timeout=4).json()
        trend_resp = requests.get(f"{API}/predictions/risk-trend/{patient_id}?days=30", timeout=4).json()
        trend_data = trend_resp.get("trend", [])
    except Exception:
        patient = {"first_name": PATIENTS.get(patient_id, "Unknown").split()[0],
                   "last_name": PATIENTS.get(patient_id, "").split()[-1],
                   "mrn": patient_id, "sex": "—", "risk_factors": [],
                   "attending_physician": "—"}
        trend_data = []

    latest = trend_data[-1] if trend_data else {"risk_score": 0.5, "risk_level": "medium"}
    risk_score = latest.get("risk_score", 0.5)
    risk_level = latest.get("risk_level", "medium")
    name = f"{patient.get('first_name','')} {patient.get('last_name','')}"

    trend_fig = risk_timeline_chart(trend_data)
    gauge_fig = risk_gauge(risk_score, risk_level, title=f"Current Risk — {name}")

    # Trend analysis
    if len(trend_data) >= 7:
        first_week = [d["risk_score"] for d in trend_data[:7]]
        last_week = [d["risk_score"] for d in trend_data[-7:]]
        avg_first = sum(first_week) / len(first_week)
        avg_last = sum(last_week) / len(last_week)
        trend_direction = avg_last - avg_first
        trend_text = f"↑ +{trend_direction:.1%}" if trend_direction > 0.02 else \
                     f"↓ {trend_direction:.1%}" if trend_direction < -0.02 else "→ Stable"
        trend_color = "#EF4444" if trend_direction > 0.02 else "#22C55E" if trend_direction < -0.02 else "#F59E0B"
    else:
        trend_text = "Insufficient data"
        trend_color = "#88BB99"

    rf_list = patient.get("risk_factors", [])
    rf_score_contrib = len(rf_list) * 4  # percent per risk factor

    # Feature importances (same as model defaults)
    importances = {
        "ST deviation": 0.22,
        "Rhythm pattern": 0.20,
        "Heart rate": 0.18,
        "QTc interval": 0.16,
        "QRS duration": 0.14,
        "RR variability": 0.05,
        "Age factor": 0.03,
        "Risk factors": 0.02,
    }
    feat_fig = feature_importance_chart(importances)

    # Risk factors contributing to score
    risk_factor_items = []
    for rf in rf_list:
        label = rf.replace("_", " ").title()
        risk_factor_items.append(html.Div([
            html.Span("▪ ", style={"color": "#EF4444"}),
            html.Span(label, className="rf-report-item"),
        ]))

    return html.Div([
        dbc.Row([
            # Gauge
            dbc.Col([
                html.Div([
                    dcc.Graph(figure=gauge_fig, config={"displayModeBar": False}),
                    html.Div([
                        html.Span("30-day trend: ", className="trend-label"),
                        html.Span(trend_text, style={"color": trend_color, "fontWeight": "800"}),
                    ], className="trend-row mt-2"),
                ], className="panel"),
            ], md=4),

            # Risk factors
            dbc.Col([
                html.Div([
                    html.Span("◈ Clinical Risk Profile", className="panel-title"),
                    html.Div([
                        html.P("Documented Risk Factors", className="section-label mt-3"),
                        html.Div(risk_factor_items or [html.P("None documented", className="text-muted")]),
                        html.P(f"Estimated RF contribution: +{rf_score_contrib}% baseline risk",
                               className="rf-contrib mt-2"),
                        html.Hr(style={"borderColor": "#1A3320"}),
                        html.P("Attending Physician", className="section-label"),
                        html.P(patient.get("attending_physician", "—"), className="physician-text"),
                    ]),
                ], className="panel h-100"),
            ], md=4),

            # Feature importance
            dbc.Col([
                html.Div([
                    html.Span("AI Model Weights", className="panel-title"),
                    dcc.Graph(figure=feat_fig, config={"displayModeBar": False}),
                ], className="panel h-100"),
            ], md=4),
        ], className="g-3"),

        # Trend chart full width
        html.Div([
            html.Span("30-Day Risk Score Trend", className="panel-title"),
            dcc.Graph(figure=trend_fig, config={"displayModeBar": False}),
        ], className="panel mt-3"),

        # Summary text
        html.Div([
            html.Span("▣ Clinical Summary", className="panel-title"),
            html.Div([
                _summary_item("Current risk level", risk_level.upper(),
                              "#EF4444" if risk_level in ("high","critical") else "#22C55E"),
                _summary_item("Risk score", f"{risk_score:.1%}"),
                _summary_item("30-day trend", trend_text, trend_color),
                _summary_item("Active risk factors", str(len(rf_list))),
            ], className="summary-grid"),
        ], className="panel mt-3"),
    ])


def _summary_item(label, value, color="#88BB99"):
    return html.Div([
        html.P(label, className="summary-label"),
        html.P(value, className="summary-value", style={"color": color}),
    ], className="summary-item")

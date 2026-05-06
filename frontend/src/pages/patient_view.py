import requests
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from src.components.ecg_chart import risk_timeline_chart
from src.components.risk_gauge import risk_gauge
from src.components.cards import patient_row

API = "http://localhost:8000/api"


def layout():
    return html.Div([
        html.Div([
            html.H1("Patients", className="page-title"),
            html.P("Patient registry and cardiovascular risk profiles", className="page-subtitle"),
        ], className="page-header"),

        dbc.Row([
            # Patient list
            dbc.Col([
                html.Div([
                    html.Div([
                        html.Span("⊞ Patient Registry", className="panel-title"),
                        dbc.Input(id="pt-search", placeholder="Search MRN or name...",
                                  debounce=True, className="input-mono ms-auto", style={"width": "200px"}),
                    ], className="panel-header"),
                    html.Div(id="patient-list-table"),
                ], className="panel"),
            ], md=5),

            # Patient detail
            dbc.Col([
                html.Div(id="patient-detail-panel", children=[
                    html.Div([
                        html.P("Select a patient to view their profile", className="text-muted text-center mt-5"),
                    ]),
                ], className="panel"),
            ], md=7),
        ], className="g-3"),

        dcc.Store(id="selected-patient-id"),
        dcc.Interval(id="pt-interval", interval=60_000, n_intervals=0),
    ], className="page-wrapper")


@callback(
    Output("patient-list-table", "children"),
    Input("pt-search", "value"),
    Input("pt-interval", "n_intervals"),
)
def load_patients(search, n):
    try:
        url = f"{API}/patients/"
        if search:
            url += f"?search={search}"
        patients = requests.get(url, timeout=5).json()
    except Exception:
        patients = _demo_patients()

    if not patients:
        return html.P("No patients found.", className="text-muted p-3")

    rows = [patient_row(p) for p in patients]
    return dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("MRN"), html.Th("Name"), html.Th("Risk Factors"), html.Th("Physician"),
            ]), className="table-head"),
            html.Tbody(rows),
        ],
        bordered=False, hover=True, responsive=True, className="patient-table",
    )


@callback(
    Output("patient-detail-panel", "children"),
    Input("selected-patient-id", "data"),
)
def show_patient_detail(patient_id):
    if not patient_id:
        return html.P("Select a patient from the list", className="text-muted text-center mt-5")

    try:
        patient = requests.get(f"{API}/patients/{patient_id}", timeout=4).json()
        trend_resp = requests.get(f"{API}/predictions/risk-trend/{patient_id}?days=21", timeout=4).json()
        trend_data = trend_resp.get("trend", [])
    except Exception:
        patient = next((p for p in _demo_patients() if p["id"] == patient_id), None)
        trend_data = []
        if not patient:
            return html.P("Patient not found", className="text-muted p-3")

    latest_risk = trend_data[-1] if trend_data else {"risk_score": 0.3, "risk_level": "low"}
    risk_score = latest_risk.get("risk_score", 0.3)
    risk_level = latest_risk.get("risk_level", "low")

    dob = patient.get("date_of_birth", "")
    age = "—"
    if dob:
        try:
            from datetime import date
            bd = date.fromisoformat(str(dob))
            today = date.today()
            age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        except Exception:
            pass

    rf_list = patient.get("risk_factors", [])
    meds = patient.get("current_medications", [])

    trend_fig = risk_timeline_chart(trend_data)
    gauge_fig = risk_gauge(risk_score, risk_level, title="Current Risk")

    return html.Div([
        # Name + meta
        html.Div([
            html.Div([
                html.H4(f"{patient.get('first_name','')} {patient.get('last_name','')}", className="pt-name"),
                html.Span(patient.get("mrn", ""), className="pt-mrn"),
            ]),
            html.Div([
                html.Span(f"{age} yr", className="pt-tag"),
                html.Span(patient.get("sex", ""), className="pt-tag"),
            ], className="pt-tags"),
        ], className="pt-header"),

        html.P(f"Attending: {patient.get('attending_physician','—')}", className="pt-physician"),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=gauge_fig, config={"displayModeBar": False}), md=5),
            dbc.Col([
                html.Div([
                    html.P("Cardiovascular Risk Factors", className="section-label"),
                    html.Div([
                        html.Span(rf.replace("_", " ").title(), className="rf-chip")
                        for rf in rf_list
                    ] or [html.Span("None documented", className="text-muted")],
                    className="rf-chips"),
                ]),
                html.Div([
                    html.P("Current Medications", className="section-label mt-2"),
                    html.Div([
                        html.Span(m, className="med-chip") for m in meds
                    ] or [html.Span("None documented", className="text-muted")],
                    className="med-chips"),
                ]),
            ], md=7),
        ]),

        html.Div([
            html.Span("Risk Score History (21 days)", className="section-label"),
            dcc.Graph(figure=trend_fig, config={"displayModeBar": False}),
        ], className="mt-3"),
    ], className="pt-detail")


def _demo_patients():
    return [
        {"id": "pt-001", "mrn": "MRN-10001", "first_name": "James", "last_name": "Holloway",
         "date_of_birth": "1958-03-14", "sex": "M",
         "risk_factors": ["hypertension", "diabetes", "smoking"],
         "current_medications": ["Metoprolol", "Lisinopril"],
         "attending_physician": "Dr. Sarah Chen"},
        {"id": "pt-002", "mrn": "MRN-10002", "first_name": "Maria", "last_name": "Santos",
         "date_of_birth": "1965-07-22", "sex": "F",
         "risk_factors": ["hyperlipidemia", "family_history_cvd"],
         "current_medications": ["Atorvastatin"],
         "attending_physician": "Dr. Sarah Chen"},
        {"id": "pt-003", "mrn": "MRN-10003", "first_name": "David", "last_name": "Park",
         "date_of_birth": "1947-11-05", "sex": "M",
         "risk_factors": ["hypertension", "prior_mi", "heart_failure", "atrial_fibrillation"],
         "current_medications": ["Warfarin", "Furosemide", "Carvedilol"],
         "attending_physician": "Dr. Marcus Webb"},
        {"id": "pt-004", "mrn": "MRN-10004", "first_name": "Aisha", "last_name": "Patel",
         "date_of_birth": "1982-01-30", "sex": "F",
         "risk_factors": [],
         "current_medications": [],
         "attending_physician": "Dr. Marcus Webb"},
    ]

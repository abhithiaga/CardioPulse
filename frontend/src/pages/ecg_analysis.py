import requests
import json
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from src.components.ecg_chart import ecg_waveform_chart, feature_importance_chart
from src.components.risk_gauge import risk_gauge
from src.components.cards import metric_card

API = "http://localhost:8000/api"

STATUS_MAP = {
    "heart_rate_bpm": lambda v: "critical" if v > 150 or v < 40 else "warning" if v > 100 or v < 55 else "normal",
    "qrs_duration_ms": lambda v: "critical" if v and v > 130 else "warning" if v and v > 120 else "normal",
    "qtc_interval_ms": lambda v: "critical" if v and v > 500 else "warning" if v and v > 450 else "normal",
    "st_deviation_mv": lambda v: "critical" if v and abs(v) > 0.2 else "warning" if v and abs(v) > 0.1 else "normal",
}


def layout():
    return html.Div([
        html.Div([
            html.Div([
                html.H1("ECG Analysis", className="page-title"),
                html.P("AI-powered real-time electrocardiogram interpretation", className="page-subtitle"),
            ]),
        ], className="page-header"),

        # Controls
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Label("Patient ID", className="form-label-mono"),
                    dbc.Input(id="ecg-patient-id", value="pt-001", type="text",
                              placeholder="pt-001", className="input-mono"),
                ]),
            ], md=2),
            dbc.Col([
                html.Div([
                    html.Label("Simulated Heart Rate (bpm)", className="form-label-mono"),
                    dcc.Slider(id="ecg-hr-slider", min=30, max=200, step=5, value=75,
                               marks={30: "30", 60: "60", 100: "100", 150: "150", 200: "200"},
                               tooltip={"placement": "top", "always_visible": True}),
                ]),
            ], md=4),
            dbc.Col([
                html.Div([
                    html.Label("Signal Noise", className="form-label-mono"),
                    dcc.Slider(id="ecg-noise-slider", min=0.01, max=0.3, step=0.01, value=0.02,
                               marks={0.01: "Low", 0.15: "Med", 0.30: "High"},
                               tooltip={"placement": "top", "always_visible": True}),
                ]),
            ], md=3),
            dbc.Col([
                html.Div([
                    html.Label("", className="form-label-mono"),
                    dbc.Button(
                        "▶ Analyze ECG",
                        id="ecg-analyze-btn",
                        color="success",
                        className="analyze-btn w-100",
                    ),
                ]),
            ], md=3),
        ], className="control-panel g-3 mb-3"),

        # Main analysis panels
        dbc.Row([
            # Waveform
            dbc.Col([
                html.Div([
                    html.Div([
                        html.Span("♥ ECG Waveform", className="panel-title"),
                        html.Span(id="ecg-rhythm-badge", className="rhythm-badge"),
                    ], className="panel-header"),
                    dcc.Loading(
                        dcc.Graph(id="ecg-waveform-graph", config={"displayModeBar": True}),
                        color="#00FF7F",
                    ),
                ], className="panel"),
            ], md=8),

            # Risk gauge
            dbc.Col([
                html.Div([
                    html.Span("Risk Score", className="panel-title"),
                    dcc.Loading(
                        dcc.Graph(id="ecg-risk-gauge", config={"displayModeBar": False}),
                        color="#00FF7F",
                    ),
                    html.Div(id="ecg-diagnosis-labels"),
                ], className="panel"),
            ], md=4),
        ]),

        # Metrics row
        html.Div([
            html.Span("ECG Interval Metrics", className="panel-title mb-2"),
            html.Div(id="ecg-metrics-row", className="metrics-row"),
        ], className="panel mt-3"),

        # Abnormalities + Feature importances
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Span("◈ Clinical Findings", className="panel-title"),
                    html.Div(id="ecg-findings"),
                ], className="panel"),
            ], md=5),
            dbc.Col([
                html.Div([
                    html.Span("Model Interpretability", className="panel-title"),
                    dcc.Graph(id="ecg-feature-chart", config={"displayModeBar": False}),
                ], className="panel"),
            ], md=7),
        ], className="mt-3"),

        # Hidden result store
        dcc.Store(id="ecg-result-store"),
        dcc.Interval(id="ecg-interval", interval=999999, n_intervals=0),
    ], className="page-wrapper")


@callback(
    Output("ecg-result-store", "data"),
    Output("ecg-waveform-graph", "figure"),
    Output("ecg-risk-gauge", "figure"),
    Output("ecg-rhythm-badge", "children"),
    Output("ecg-metrics-row", "children"),
    Output("ecg-findings", "children"),
    Output("ecg-feature-chart", "figure"),
    Output("ecg-diagnosis-labels", "children"),
    Input("ecg-analyze-btn", "n_clicks"),
    State("ecg-patient-id", "value"),
    State("ecg-hr-slider", "value"),
    State("ecg-noise-slider", "value"),
    prevent_initial_call=False,
)
def run_analysis(n_clicks, patient_id, heart_rate, noise):
    pid = patient_id or "demo-patient"
    hr = heart_rate or 75

    try:
        # Get waveform
        wf = requests.get(
            f"{API}/ecg/waveform/synthetic?heart_rate={hr}&duration=8&noise={noise or 0.02}",
            timeout=5
        ).json()
        ecg_time = wf["time"]
        ecg_amp = wf["amplitude"]

        # Run full analysis
        result = requests.get(
            f"{API}/ecg/demo?patient_id={pid}&heart_rate={hr}&noise={noise or 0.02}",
            timeout=10
        ).json()
    except Exception as e:
        return _fallback_analysis(hr)

    metrics = result.get("metrics", {})
    risk_score = result.get("risk_score", 0.3)
    risk_level = result.get("risk_level", "low")
    labels = result.get("diagnosis_labels", [])
    importances = result.get("feature_importances", {})
    annotations = result.get("waveform_annotations", [])

    # Waveform figure
    ecg_fig = ecg_waveform_chart(
        ecg_time, ecg_amp,
        title=f"Lead II — Patient {pid} · {hr:.0f} bpm",
        annotations=annotations,
    )

    # Risk gauge
    gauge_fig = risk_gauge(risk_score, risk_level)

    # Rhythm badge
    rhythm = metrics.get("rhythm", "Unknown")
    badge_color = "#EF4444" if "Fibrillation" in rhythm or "Tachycardia" in rhythm else "#22C55E"
    rhythm_badge = html.Span(rhythm, style={"color": badge_color})

    # Metric cards
    def fmt(val, digits=1):
        return f"{val:.{digits}f}" if val is not None else "—"

    hr_val = metrics.get("heart_rate_bpm")
    metrics_cards = [
        metric_card("Heart Rate", fmt(hr_val), "bpm",
                    STATUS_MAP["heart_rate_bpm"](hr_val or 75)),
        metric_card("PR Interval", fmt(metrics.get("pr_interval_ms")), "ms", "normal"),
        metric_card("QRS Duration", fmt(metrics.get("qrs_duration_ms")), "ms",
                    STATUS_MAP["qrs_duration_ms"](metrics.get("qrs_duration_ms"))),
        metric_card("QTc Interval", fmt(metrics.get("qtc_interval_ms")), "ms",
                    STATUS_MAP["qtc_interval_ms"](metrics.get("qtc_interval_ms"))),
        metric_card("ST Deviation", fmt(metrics.get("st_deviation_mv"), 3), "mV",
                    STATUS_MAP["st_deviation_mv"](metrics.get("st_deviation_mv"))),
        metric_card("RR Variability", fmt(metrics.get("rr_variability_ms")), "ms", "info"),
    ]

    # Clinical findings
    abnormalities = metrics.get("abnormalities", [])
    if abnormalities:
        findings_list = html.Div([
            html.Div([
                html.Span("⚠", className="finding-icon"),
                html.Span(a, className="finding-text"),
            ], className="finding-item")
            for a in abnormalities
        ])
    else:
        findings_list = html.Div([
            html.Span("✓", className="finding-icon ok"),
            html.Span("No significant acute findings", className="finding-text ok"),
        ], className="finding-item")

    # Feature importance chart
    feat_fig = feature_importance_chart(importances) if importances else feature_importance_chart({
        "st_deviation": 0.22, "rhythm_code": 0.20, "heart_rate": 0.18,
        "qtc": 0.16, "qrs_duration": 0.14, "rr_variability": 0.05,
    })

    # Diagnosis labels
    label_els = html.Div([
        html.Div(lbl, className=f"diag-label {'diag-critical' if 'URGENT' in lbl else 'diag-normal'}")
        for lbl in labels
    ], className="diag-labels mt-2")

    return result, ecg_fig, gauge_fig, rhythm_badge, metrics_cards, findings_list, feat_fig, label_els


def _fallback_analysis(hr=75):
    """Return mock figures when backend is offline."""
    import numpy as np
    t = [i / 500 for i in range(4000)]
    amp = [0.0] * 4000  # zeros — shows flat line
    ecg_fig = ecg_waveform_chart(t, amp, title="ECG (Backend offline — demo mode)")
    g = risk_gauge(0.42, "medium")
    return {}, ecg_fig, g, "Sinus Rhythm (demo)", [], html.P("Backend offline", className="text-muted"), \
           feature_importance_chart({"st_deviation": 0.22, "rhythm_code": 0.20, "heart_rate": 0.18}), html.Div()

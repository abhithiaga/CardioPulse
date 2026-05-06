import requests
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from src.components.ecg_chart import ecg_waveform_chart, population_risk_donut, risk_timeline_chart
from src.components.cards import stat_banner, alert_card

API = "http://localhost:8000/api"
DEMO_PATIENT = "pt-003"   # David Park — highest risk for dramatic demo


def layout():
    return html.Div([
        # Page header
        html.Div([
            html.Div([
                html.H1("Clinical Overview", className="page-title"),
                html.P("Real-time cardiovascular surveillance dashboard", className="page-subtitle"),
            ]),
            html.Div([
                html.Span("● LIVE", className="live-badge"),
                html.Span("Auto-refresh 30s", className="refresh-label"),
            ], className="header-right"),
        ], className="page-header"),

        # Stat banners row
        html.Div(id="dashboard-stats"),

        # Main grid
        dbc.Row([
            # Left: Live ECG strip
            dbc.Col([
                html.Div([
                    html.Div([
                        html.Span("♥ Live ECG Monitor", className="panel-title"),
                        html.Span("pt-003 · David Park", className="panel-meta"),
                    ], className="panel-header"),
                    dcc.Graph(id="live-ecg", config={"displayModeBar": False}),
                ], className="panel"),
            ], md=8),

            # Right: Risk distribution + alerts
            dbc.Col([
                html.Div([
                    html.Span("Risk Distribution", className="panel-title"),
                    dcc.Graph(id="risk-donut", config={"displayModeBar": False}),
                ], className="panel"),
            ], md=4),
        ], className="mt-3"),

        # Bottom grid: trend + alerts
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Span("◈ High Risk Alerts", className="panel-title"),
                    html.Div(id="alerts-panel"),
                ], className="panel"),
            ], md=5),
            dbc.Col([
                html.Div([
                    html.Span("Risk Trend — Patient pt-003", className="panel-title"),
                    dcc.Graph(id="risk-trend", config={"displayModeBar": False}),
                ], className="panel"),
            ], md=7),
        ], className="mt-3"),

        dcc.Interval(id="dashboard-interval", interval=30_000, n_intervals=0),
    ], className="page-wrapper")


@callback(
    Output("dashboard-stats", "children"),
    Output("live-ecg", "figure"),
    Output("risk-donut", "figure"),
    Output("alerts-panel", "children"),
    Output("risk-trend", "figure"),
    Input("dashboard-interval", "n_intervals"),
)
def refresh_dashboard(n):
    # Population stats
    try:
        stats = requests.get(f"{API}/predictions/population-stats", timeout=4).json()
    except Exception:
        stats = {
            "total_analyses": 248, "average_risk_score": 0.41, "high_risk_count": 49,
            "risk_distribution": {"low": 112, "medium": 87, "high": 38, "critical": 11},
        }

    # Live ECG waveform
    try:
        wf = requests.get(f"{API}/ecg/waveform/synthetic?heart_rate=72&duration=6&noise=0.025", timeout=4).json()
        ecg_time, ecg_amp = wf["time"], wf["amplitude"]
    except Exception:
        import numpy as np
        ecg_time = [i / 500 for i in range(3000)]
        ecg_amp = [0.0] * 3000  # fallback flat line

    ecg_fig = ecg_waveform_chart(ecg_time, ecg_amp, title="Lead II — Real-time")

    # Risk donut
    dist = stats.get("risk_distribution", {})
    donut_fig = population_risk_donut(dist)

    # Alerts
    try:
        alerts_data = requests.get(f"{API}/predictions/alerts?limit=5", timeout=4).json()
    except Exception:
        alerts_data = []

    alert_cards = [alert_card(a) for a in alerts_data[:5]] if alerts_data else [
        html.P("No active alerts", className="text-muted p-3")
    ]

    # Risk trend
    try:
        trend_resp = requests.get(f"{API}/predictions/risk-trend/{DEMO_PATIENT}?days=21", timeout=4).json()
        trend_data = trend_resp.get("trend", [])
    except Exception:
        trend_data = []

    trend_fig = risk_timeline_chart(trend_data)

    # Stat banners
    total = stats.get("total_analyses", 0)
    avg = stats.get("average_risk_score", 0)
    high = stats.get("high_risk_count", 0)

    stat_row = dbc.Row([
        dbc.Col(stat_banner("⊞", "Total ECG Analyses", str(total), "All time"), md=3),
        dbc.Col(stat_banner("◎", "Avg Risk Score", f"{avg:.0%}", "Platform-wide", color="#00E5FF"), md=3),
        dbc.Col(stat_banner("⚠", "High/Critical Cases", str(high), "Require review", color="#EF4444"), md=3),
        dbc.Col(stat_banner("▣", "Patients Monitored", str(len(dist)), "Active programs", color="#F59E0B"), md=3),
    ], className="stats-row g-3 mb-3")

    return stat_row, ecg_fig, donut_fig, alert_cards, trend_fig

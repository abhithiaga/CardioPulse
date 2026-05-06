"""
ECG waveform chart — Plotly graph styled like a clinical monitor.
Green trace on near-black background with grid lines matching real ECG paper.
"""
import plotly.graph_objects as go
import plotly.subplots as sp
import numpy as np
from typing import List, Optional, Dict

# Clinical ECG color palette — ICU monitor inspired
COLORS = {
    "ecg_green": "#00FF7F",      # bright phosphor green
    "ecg_red": "#FF4444",
    "ecg_yellow": "#FFD700",
    "ecg_cyan": "#00E5FF",
    "bg": "#030A06",             # near-black with green tint
    "paper": "#060E08",
    "grid_major": "#1A3320",     # ECG paper major grid
    "grid_minor": "#0D1A10",     # ECG paper minor grid
    "annotation": "#FF6B35",
    "text": "#88BB99",
    "risk_low": "#22C55E",
    "risk_medium": "#F59E0B",
    "risk_high": "#EF4444",
    "risk_critical": "#7C3AED",
}

ECG_LAYOUT = dict(
    paper_bgcolor=COLORS["paper"],
    plot_bgcolor=COLORS["bg"],
    font=dict(color=COLORS["text"], family="JetBrains Mono, monospace", size=11),
    margin=dict(l=50, r=20, t=30, b=40),
    xaxis=dict(
        gridcolor=COLORS["grid_major"],
        gridwidth=0.5,
        minor=dict(gridcolor=COLORS["grid_minor"], gridwidth=0.3, nticks=5),
        showline=True, linecolor=COLORS["grid_major"],
        title=dict(text="Time (s)", font=dict(size=10)),
        zeroline=False,
    ),
    yaxis=dict(
        gridcolor=COLORS["grid_major"],
        gridwidth=0.5,
        showline=True, linecolor=COLORS["grid_major"],
        title=dict(text="Amplitude (mV)", font=dict(size=10)),
        zeroline=True, zerolinecolor=COLORS["grid_major"],
    ),
    showlegend=False,
)


def ecg_waveform_chart(
    time: List[float],
    amplitude: List[float],
    title: str = "ECG Waveform — Lead II",
    annotations: Optional[List[Dict]] = None,
    show_beats: bool = False,
    r_peaks: Optional[List[int]] = None,
) -> go.Figure:
    """Primary ECG strip chart."""
    fig = go.Figure()

    # Main ECG trace
    fig.add_trace(go.Scatter(
        x=time, y=amplitude,
        mode="lines",
        line=dict(color=COLORS["ecg_green"], width=1.5),
        name="ECG",
        hovertemplate="t=%{x:.3f}s<br>%{y:.3f}mV<extra></extra>",
    ))

    # R-peak markers
    if r_peaks and show_beats:
        r_x = [time[i] for i in r_peaks if i < len(time)]
        r_y = [amplitude[i] for i in r_peaks if i < len(amplitude)]
        fig.add_trace(go.Scatter(
            x=r_x, y=r_y, mode="markers",
            marker=dict(symbol="triangle-down", color=COLORS["ecg_yellow"], size=8),
            name="R Peak",
            hovertemplate="R Peak<br>t=%{x:.3f}s<extra></extra>",
        ))

    # Clinical annotations (ST changes, etc.)
    if annotations:
        for ann in annotations:
            fig.add_annotation(
                x=time[len(time) // 2] if time else 5,
                y=max(amplitude) * 0.85 if amplitude else 0.8,
                text=ann.get("label", ""),
                showarrow=False,
                font=dict(color=COLORS["annotation"], size=11, family="JetBrains Mono"),
                bgcolor="rgba(3,10,6,0.8)",
                bordercolor=COLORS["annotation"],
                borderwidth=1,
            )

    layout = {**ECG_LAYOUT, "title": dict(text=title, font=dict(color=COLORS["text"], size=13))}
    fig.update_layout(**layout)
    return fig


def ecg_multi_lead_chart(leads_data: Dict[str, List[float]], sample_rate: int = 500) -> go.Figure:
    """12-lead ECG display (3-column layout, 4 rows)."""
    lead_names = list(leads_data.keys())[:12]
    n_leads = len(lead_names)
    rows = (n_leads + 2) // 3
    cols = min(3, n_leads)

    fig = sp.make_subplots(
        rows=rows, cols=cols,
        shared_xaxes=False,
        vertical_spacing=0.04,
        horizontal_spacing=0.04,
        subplot_titles=lead_names,
    )

    for idx, name in enumerate(lead_names):
        row = idx // 3 + 1
        col = idx % 3 + 1
        amp = leads_data[name]
        t = [i / sample_rate for i in range(len(amp))]

        fig.add_trace(
            go.Scatter(x=t, y=amp, mode="lines",
                       line=dict(color=COLORS["ecg_green"], width=1),
                       showlegend=False,
                       hovertemplate=f"{name}<br>%{{y:.3f}}mV<extra></extra>"),
            row=row, col=col,
        )

    fig.update_layout(
        paper_bgcolor=COLORS["paper"],
        plot_bgcolor=COLORS["bg"],
        font=dict(color=COLORS["text"], family="JetBrains Mono", size=9),
        margin=dict(l=30, r=10, t=40, b=20),
        height=60 + rows * 140,
    )
    fig.update_xaxes(gridcolor=COLORS["grid_major"], showticklabels=False)
    fig.update_yaxes(gridcolor=COLORS["grid_major"], showticklabels=False)
    return fig


def risk_timeline_chart(trend_data: List[Dict]) -> go.Figure:
    """Risk score over time for a patient."""
    if not trend_data:
        return go.Figure()

    dates = [d["date"] for d in trend_data]
    scores = [d["risk_score"] for d in trend_data]
    levels = [d.get("risk_level", "low") for d in trend_data]
    colors = [COLORS.get(f"risk_{l}", COLORS["risk_low"]) for l in levels]

    fig = go.Figure()

    # Shaded risk zones
    fig.add_hrect(y0=0.75, y1=1.0, fillcolor="rgba(124,58,237,0.06)", line_width=0, annotation_text="Critical", annotation_font_color="#7C3AED")
    fig.add_hrect(y0=0.45, y1=0.75, fillcolor="rgba(239,68,68,0.05)", line_width=0, annotation_text="High", annotation_font_color="#EF4444")
    fig.add_hrect(y0=0.0, y1=0.45, fillcolor="rgba(34,197,94,0.03)", line_width=0)

    fig.add_trace(go.Scatter(
        x=dates, y=scores,
        mode="lines+markers",
        line=dict(color=COLORS["ecg_cyan"], width=2),
        marker=dict(color=colors, size=8, line=dict(color="#030A06", width=1)),
        fill="tozeroy",
        fillcolor="rgba(0,229,255,0.05)",
        hovertemplate="Date: %{x}<br>Risk: %{y:.1%}<extra></extra>",
    ))

    layout = {**ECG_LAYOUT,
              "title": "Risk Score Trend",
              "yaxis": {**ECG_LAYOUT["yaxis"], "range": [0, 1], "tickformat": ".0%"},
              "xaxis": {**ECG_LAYOUT["xaxis"], "title": "Date"}}
    fig.update_layout(**layout)
    return fig


def feature_importance_chart(importances: Dict[str, float]) -> go.Figure:
    """Horizontal bar chart — model feature weights."""
    labels = list(importances.keys())
    values = list(importances.values())
    colors_list = [COLORS["ecg_green"] if v > 0.15 else COLORS["ecg_cyan"] for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=colors_list,
        text=[f"{v:.1%}" for v in values],
        textposition="outside",
        textfont=dict(color=COLORS["text"], size=10),
    ))

    layout = {**ECG_LAYOUT, "title": "Model Feature Importances",
              "xaxis": {**ECG_LAYOUT["xaxis"], "range": [0, max(values) * 1.3],
                        "tickformat": ".0%", "title": "Importance"},
              "yaxis": {**ECG_LAYOUT["yaxis"], "title": ""}}
    fig.update_layout(**layout, margin=dict(l=130, r=50, t=40, b=30))
    return fig


def population_risk_donut(distribution: Dict[str, int]) -> go.Figure:
    """Risk distribution donut chart across all patients."""
    labels = list(distribution.keys())
    values = list(distribution.values())
    color_map = {
        "low": COLORS["risk_low"], "medium": COLORS["risk_medium"],
        "high": COLORS["risk_high"], "critical": COLORS["risk_critical"],
    }
    colors_list = [color_map.get(l, "#666") for l in labels]

    fig = go.Figure(go.Pie(
        labels=[l.upper() for l in labels],
        values=values,
        hole=0.65,
        marker=dict(colors=colors_list, line=dict(color=COLORS["bg"], width=2)),
        textfont=dict(color=COLORS["text"], family="JetBrains Mono"),
        hovertemplate="%{label}: %{value} patients<extra></extra>",
    ))

    fig.update_layout(
        paper_bgcolor=COLORS["paper"],
        plot_bgcolor=COLORS["bg"],
        font=dict(color=COLORS["text"], family="JetBrains Mono", size=11),
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=True,
        legend=dict(font=dict(color=COLORS["text"])),
        title=dict(text="Risk Distribution", font=dict(color=COLORS["text"], size=13)),
    )
    return fig

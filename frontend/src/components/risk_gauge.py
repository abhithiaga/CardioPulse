import plotly.graph_objects as go

COLORS = {
    "bg": "#060E08", "paper": "#060E08",
    "text": "#88BB99", "green": "#00FF7F",
    "low": "#22C55E", "medium": "#F59E0B",
    "high": "#EF4444", "critical": "#7C3AED",
}


def risk_gauge(score: float, risk_level: str, title: str = "Cardiovascular Risk") -> go.Figure:
    """Circular gauge — the centerpiece of any patient risk view."""
    color_map = {
        "low": COLORS["low"], "medium": COLORS["medium"],
        "high": COLORS["high"], "critical": COLORS["critical"],
    }
    bar_color = color_map.get(risk_level, COLORS["medium"])
    pct = round(score * 100, 1)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number=dict(suffix="%", font=dict(size=44, color=bar_color, family="JetBrains Mono")),
        title=dict(text=f"{title}<br><span style='font-size:14px;color:#88BB99'>{risk_level.upper()} RISK</span>",
                   font=dict(size=14, color=COLORS["text"], family="Syne")),
        gauge=dict(
            axis=dict(
                range=[0, 100],
                tickwidth=1,
                tickcolor=COLORS["text"],
                tickvals=[0, 25, 45, 75, 100],
                ticktext=["0", "25", "45", "75", "100"],
                tickfont=dict(color=COLORS["text"], size=9),
            ),
            bar=dict(color=bar_color, thickness=0.25),
            bgcolor=COLORS["bg"],
            borderwidth=1,
            bordercolor="#1A3320",
            steps=[
                dict(range=[0, 45], color="rgba(34,197,94,0.08)"),
                dict(range=[45, 75], color="rgba(239,68,68,0.08)"),
                dict(range=[75, 100], color="rgba(124,58,237,0.12)"),
            ],
            threshold=dict(
                line=dict(color=bar_color, width=3),
                thickness=0.75,
                value=pct,
            ),
        ),
    ))

    fig.update_layout(
        paper_bgcolor=COLORS["paper"],
        font=dict(color=COLORS["text"], family="JetBrains Mono"),
        margin=dict(l=20, r=20, t=60, b=10),
        height=260,
    )
    return fig


def mini_risk_bar(score: float, risk_level: str) -> go.Figure:
    """Compact horizontal risk bar for list views."""
    color_map = {
        "low": "#22C55E", "medium": "#F59E0B",
        "high": "#EF4444", "critical": "#7C3AED",
    }
    color = color_map.get(risk_level, "#888")

    fig = go.Figure()
    # Background track
    fig.add_trace(go.Bar(x=[1], y=["risk"], orientation="h",
                         marker_color="#1A3320", showlegend=False,
                         hoverinfo="none"))
    # Score fill
    fig.add_trace(go.Bar(x=[score], y=["risk"], orientation="h",
                         marker_color=color, showlegend=False,
                         hovertemplate=f"Risk: {score:.1%}<extra></extra>"))

    fig.update_layout(
        barmode="overlay",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=24,
        xaxis=dict(range=[0, 1], visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig

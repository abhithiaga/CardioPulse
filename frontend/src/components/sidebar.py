from dash import html
import dash_bootstrap_components as dbc


NAV_ITEMS = [
    {"label": "Overview",    "icon": "▣",  "href": "/dashboard"},
    {"label": "ECG Analysis","icon": "♥",  "href": "/ecg"},
    {"label": "Patients",    "icon": "⊞",  "href": "/patients"},
    {"label": "Risk Reports","icon": "◈",  "href": "/risk"},
]


def sidebar():
    links = [
        dbc.NavLink(
            [
                html.Span(item["icon"], className="nav-icon"),
                html.Span(item["label"], className="nav-label"),
            ],
            href=item["href"],
            active="exact",
            className="sidebar-link",
        )
        for item in NAV_ITEMS
    ]

    return html.Div(
        [
            # Logo
            html.Div([
                html.Div("♥", className="logo-pulse"),
                html.Div([
                    html.Span("Cardio", className="logo-cardio"),
                    html.Span("AI", className="logo-ai"),
                ], className="logo-text-row"),
            ], className="sidebar-logo"),

            html.Div(className="sidebar-divider"),

            # Nav
            dbc.Nav(links, vertical=True, pills=True, className="sidebar-nav"),

            # System status
            html.Div([
                html.Div(className="sidebar-divider"),
                html.Div([
                    html.Div([
                        html.Span("●", className="status-dot"),
                        html.Span("System Online", className="status-text"),
                    ], className="status-row"),
                    html.Div([
                        html.Span("■ AWS Lambda", className="infra-tag"),
                        html.Span("■ API Gateway", className="infra-tag"),
                    ], className="infra-row"),
                ], className="sidebar-status"),
                html.P("v1.0.0 · Secure", className="sidebar-version"),
            ], className="sidebar-footer"),
        ],
        className="sidebar",
    )

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
from src.components.sidebar import sidebar

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.CYBORG,
        "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;700&family=Syne:wght@400;700;800&display=swap",
    ],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    title="CardioAI | Cardiovascular Diagnostics",
)
server = app.server  # for gunicorn / AWS

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="auth-store", storage_type="session"),
        dcc.Store(id="patient-store", storage_type="memory"),
        dbc.Row(
            [
                dbc.Col(sidebar(), width=2, className="p-0"),
                dbc.Col(
                    html.Div(id="page-content", className="page-content"),
                    width=10,
                ),
            ],
            className="g-0",
            style={"minHeight": "100vh"},
        ),
    ],
    className="app-root",
)


@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def route(pathname):
    from src.pages import dashboard, ecg_analysis, patient_view, risk_report
    if pathname in ("/", "/dashboard"):
        return dashboard.layout()
    elif pathname == "/ecg":
        return ecg_analysis.layout()
    elif pathname == "/patients":
        return patient_view.layout()
    elif pathname == "/risk":
        return risk_report.layout()
    return html.Div([
        html.H2("404"),
        html.P(f"Page not found: {pathname}")
    ], className="p-4 text-white")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

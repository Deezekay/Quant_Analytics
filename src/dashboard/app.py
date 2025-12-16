"""
Plotly Dash dashboard for crypto analytics visualization.

Provides interactive charts and controls for real-time analytics.
"""

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime

from ..config import FLASK_HOST, FLASK_PORT, DASHBOARD_UPDATE_INTERVAL

# Initialize Dash app with dark theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True
)

# Flask API base URL
API_BASE = f"http://{FLASK_HOST}:{FLASK_PORT}/api"

# ============================================================================
# LAYOUT COMPONENTS
# ============================================================================

def create_header():
    """Create compact application header."""
    return dbc.Row([
        dbc.Col([
            html.Div([
                # Icon
                html.Span("⚡", style={
                    'fontSize': '24px',
                    'marginRight': '12px'
                }),
                # Title - Simplified
                html.H4("QUANT ANALYSIS", style={
                    'background': 'linear-gradient(135deg, #00d4ff 0%, #00ff88 100%)',
                    'WebkitBackgroundClip': 'text',
                    'WebkitTextFillColor': 'transparent',
                    'fontWeight': '800',
                    'letterSpacing': '2px',
                    'margin': '0',
                    'fontSize': '20px'
                })
            ], style={
                'display': 'flex',
                'alignItems': 'center'
            })
        ], width=8),
        
        # Status indicator
        dbc.Col([
            html.Div([
                html.Span("●", id="status-indicator", style={
                    'fontSize': '12px',
                    'marginRight': '6px',
                    'color': '#00ff88'
                }),
                html.Span(id="status-text", children="Initializing", style={
                    'fontSize': '11px',
                    'fontWeight': '700',
                    'letterSpacing': '1px'
                }, className="text-success")
            ], style={
                'display': 'flex',
                'alignItems': 'center',
                'justifyContent': 'flex-end'
            })
        ], width=4)
    ], style={
        'padding': '12px 0',  # Reduced from 24px
        'marginBottom': '12px',  # Reduced from 24px
        'borderBottom': '1px solid rgba(0, 212, 255, 0.2)'
    })


def create_controls_sidebar():
    """Create control panel sidebar."""
    return dbc.Card([
        dbc.CardHeader(
            html.H4("⚙️ CONTROL PANEL", style={
                'margin': '0',
                'fontSize': '14px',
                'fontWeight': '700',
                'letterSpacing': '1px',
                'color': '#00d4ff'
            }),
            style={
                'backgroundColor': 'rgba(0, 212, 255, 0.05)',
                'borderBottom': '2px solid rgba(0, 212, 255, 0.3)',
                'padding': '16px'
            }
        ),
        dbc.CardBody([
            # Symbol X Selection
            html.Label("SYMBOL X", style={
                'fontSize': '11px',
                'fontWeight': '700',
                'letterSpacing': '1px',
                'color': '#00d4ff',
                'marginTop': '12px',
                'marginBottom': '8px',
                'display': 'block'
            }),
            dcc.Dropdown(
               id='symbol-x-dropdown',
                options=[
                    {'label': '🪙 BTC/USDT', 'value': 'BTCUSDT'},
                    {'label': '💎 ETH/USDT', 'value': 'ETHUSDT'},
                ],
                value='BTCUSDT',
                clearable=False,
                style={
                    'marginBottom': '16px',
                    'fontSize': '13px'
                }
            ),
            
            # Symbol Y Selection
            html.Label("SYMBOL Y", style={
                'fontSize': '11px',
                'fontWeight': '700',
                'letterSpacing': '1px',
                'color': '#00d4ff',
                'marginBottom': '8px',
                'display': 'block'
            }),
            dcc.Dropdown(
                id='symbol-y-dropdown',
                options=[
                    {'label': '💎 ETH/USDT', 'value': 'ETHUSDT'},
                    {'label': '🪙 BTC/USDT', 'value': 'BTCUSDT'},
                ],
                value='ETHUSDT',
                clearable=False,
                style={
                    'marginBottom': '16px',
                    'fontSize': '13px'
                }
            ),
            
            # Timeframe Selection
            html.Label("TIMEFRAME", style={
                'fontSize': '11px',
                'fontWeight': '700',
                'letterSpacing': '1px',
                'color': '#00d4ff',
                'marginBottom': '8px',
                'display': 'block'
            }),
            dcc.Dropdown(
                id='interval-dropdown',
                options=[
                    {'label': '⚡ 1 Second', 'value': '1s'},
                    {'label': '📊 1 Minute', 'value': '1m'},
                    {'label': '📈 5 Minutes', 'value': '5m'},
                ],
                value='1m',
                clearable=False,
                style={
                    'marginBottom': '16px',
                    'fontSize': '13px'
                }
            ),
            
            # Rolling Window Slider
            html.Label("ROLLING WINDOW", style={
                'fontSize': '11px',
                'fontWeight': '700',
                'letterSpacing': '1px',
                'color': '#00d4ff',
                'marginBottom': '12px',
                'display': 'block'
            }),
            dcc.Slider(
                id='window-slider',
                min=10,
                max=500,
                step=10,
                value=60,
                marks={10: '10', 60: '60', 100: '100', 200: '200', 500: '500'},
                tooltip={"placement": "bottom", "always_visible": True},
                className="mb-4"
            ),
            
            # Regression Type
            html.Label("REGRESSION TYPE", style={
                'fontSize': '11px',
                'fontWeight': '700',
                'letterSpacing': '1px',
                'color': '#00d4ff',
                'marginBottom': '8px',
                'display': 'block'
            }),
            dcc.RadioItems(
                id='regression-type',
                options=[
                    {'label': '  OLS (Ordinary Least Squares)', 'value': 'ols'},
                ],
                value='ols',
                style={'marginBottom': '20px', 'fontSize': '13px'}
            ),
            
            # Action Buttons
            html.Div([
                dbc.Button("🔄 REFRESH", id="refresh-btn", style={
                    'width': '48%',
                    'backgroundColor': 'rgba(0, 212, 255, 0.2)',
                    'border': '1px solid #00d4ff',
                    'color': '#00d4ff',
                    'fontWeight': '700',
                    'fontSize': '11px',
                    'letterSpacing': '1px'
                }),
                dbc.Button("📥 EXPORT", id="export-btn", style={
                    'width': '48%',
                    'backgroundColor': 'rgba(0, 255, 136, 0.2)',
                    'border': '1px solid #00ff88',
                    'color': '#00ff88',
                    'fontWeight': '700',
                    'fontSize': '11px',
                    'letterSpacing': '1px'
                }),
            ], style={'display': 'flex', 'gap': '4%', 'marginBottom': '12px'}),
            
            dbc.Button("🧪 RUN ADF TEST", id="adf-btn", style={
                'width': '100%',
                'backgroundColor': 'rgba(255, 193, 7, 0.2)',
                'border': '1px solid #ffc107',
                'color': '#ffc107',
                'fontWeight': '700',
                'fontSize': '11px',
                'letterSpacing': '1px',
                'marginBottom': '12px'
            }),
            
            # Upload OHLC Data
            html.Hr(style={'borderColor': 'rgba(0, 212, 255, 0.2)', 'margin': '16px 0'}),
            html.Label("UPLOAD HISTORICAL DATA", style={
                'fontSize': '10px',
                'fontWeight': '700',
                'letterSpacing': '1px',
                'color': '#a855f7',
                'marginBottom': '8px',
                'display': 'block'
            }),
            dcc.Upload(
                id='upload-ohlc',
                children=html.Div([
                    html.Div('📤', style={'fontSize': '20px', 'marginBottom': '4px'}),
                    html.Div('DRAG & DROP', style={'fontSize': '10px', 'fontWeight': '700'}),
                    html.Div('or click to browse', style={'fontSize': '9px', 'color': '#6c757d'})
                ], style={'textAlign': 'center', 'padding': '20px'}),
                style={
                    'width': '100%',
                    'border': '2px dashed rgba(168, 85, 247, 0.4)',
                    'borderRadius': '8px',
                    'backgroundColor': 'rgba(168, 85, 247, 0.05)',
                    'cursor': 'pointer',
                    'transition': 'all 0.3s'
                },
                multiple=False,
                accept='.csv'
            ),
            html.Div(id='upload-status', style={'marginTop': '8px', 'fontSize': '11px'}),
            
            # Download component (hidden)
            dcc.Download(id="download-csv"),
        ], style={'padding': '20px'})
    ], style={
        'height': '100%',
        'backgroundColor': 'rgba(13, 17, 23, 0.7)',
        'border': '1px solid rgba(0, 212, 255, 0.2)',
        'borderRadius': '12px',
        'backdropFilter': 'blur(10px)'
    })


def create_stats_cards():
    """Create compact summary statistics cards (Status Badges)."""
    # Compact style for all cards
    card_style = {
        'backgroundColor': 'rgba(13, 17, 23, 0.7)',
        'border': '1px solid rgba(255, 255, 255, 0.1)',
        'borderRadius': '8px',
        'backdropFilter': 'blur(10px)',
        'height': '100%',
        'padding': '0',
        'overflow': 'hidden',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.2)'
    }
    
    header_style = {
        'fontSize': '10px',
        'fontWeight': '700',
        'letterSpacing': '1px',
        'padding': '6px 10px',  # Reduced padding
        'margin': '0',
        'textTransform': 'uppercase',
        'borderBottom': '1px solid rgba(255, 255, 255, 0.05)'
    }
    
    body_style = {
        'padding': '8px 10px',  # Compact padding
        'display': 'flex',
        'flexDirection': 'column',
        'justifyContent': 'center',
        'minHeight': '50px'     # Fixed minimal height
    }

    return dbc.Row([
        # Price Stats
        dbc.Col(dbc.Card([
            html.Div("📊 Price Stats", style={**header_style, 'color': '#00d4ff', 'backgroundColor': 'rgba(0, 212, 255, 0.05)'}),
            html.Div(id="price-stats-card", children="Loading...", style=body_style)
        ], style=card_style), width=3),
        
        # Regression
        dbc.Col(dbc.Card([
            html.Div("📈 Regression", style={**header_style, 'color': '#00ff88', 'backgroundColor': 'rgba(0, 255, 136, 0.05)'}),
            html.Div(id="regression-stats-card", children="Loading...", style=body_style)
        ], style=card_style), width=3),
        
        # Stationarity
        dbc.Col(dbc.Card([
            html.Div("🔬 Stationarity", style={**header_style, 'color': '#a855f7', 'backgroundColor': 'rgba(168, 85, 247, 0.05)'}),
            html.Div(id="stationarity-card", children="Loading...", style=body_style)
        ], style=card_style), width=3),
        
        # Alerts (with compact Z-Score input inside)
        dbc.Col(dbc.Card([
            html.Div("⚠️ Alerts", style={**header_style, 'color': '#ffc107', 'backgroundColor': 'rgba(255, 193, 7, 0.05)'}),
            html.Div([
                # Compact Z-Score threshold input
                html.Div([
                    dcc.Input(
                        id="zscore-threshold",
                        type="number",
                        value=2.0,
                        step=0.1,
                        placeholder="Threshold",
                        style={
                            'width': '60px',
                            'padding': '3px 6px',
                            'backgroundColor': 'rgba(255, 193, 7, 0.1)',
                            'border': '1px solid rgba(255, 193, 7, 0.3)',
                            'borderRadius': '4px',
                            'color': '#ffc107',
                            'fontSize': '11px',
                            'fontWeight': '700'
                        }
                    ),
                    html.Span(" σ", style={'fontSize': '10px', 'color': '#6c757d', 'marginLeft': '4px'})
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '6px'}),
                # Alerts list
                html.Div(id="alert-log", children="No alerts", style={'overflowY': 'auto', 'maxHeight': '60px', 'fontSize': '10px'})
            ], style=body_style)
        ], style=card_style), width=3),
        
    ], className="g-2", style={'marginBottom': '12px'})  # g-2 for tight gutter, minimal bottom margin


def create_charts_tabs():
    """Create tabbed chart interface."""
    return dbc.Card([
        dbc.CardHeader(
            dbc.Tabs(
                id="chart-tabs",
                active_tab="tab-price",
                children=[
                    dbc.Tab(label="📈 PRICE", tab_id="tab-price", style={'fontSize': '12px', 'fontWeight': '700'}),
                    dbc.Tab(label="📊 SPREAD", tab_id="tab-spread", style={'fontSize': '12px', 'fontWeight': '700'}),
                    dbc.Tab(label="🔗 CORRELATION", tab_id="tab-correlation", style={'fontSize': '12px', 'fontWeight': '700'}),
                    dbc.Tab(label="🗺️ HEATMAP", tab_id="tab-heatmap", style={'fontSize': '12px', 'fontWeight': '700'}),
                ]
            ),
            style={
                'backgroundColor': 'rgba(13, 17, 23, 0.5)',
                'border': 'none',
                'padding': '12px 16px'
            }
        ),
        dbc.CardBody(
            html.Div(id="tab-content", style={"minHeight": "500px"})
        )
    ], style={
        'backgroundColor': 'rgba(13, 17, 23, 0.7)',
        'border': '1px solid rgba(0, 212, 255, 0.2)',
        'borderRadius': '12px',
        'backdropFilter': 'blur(10px)',
        'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.3)'
    })


# ============================================================================
# MAIN LAYOUT
# ============================================================================

app.layout = dbc.Container([
    # Header
    create_header(),
    
    # Live Status Info Banner (Trust Layer)
    dbc.Row([
        dbc.Col([
            html.Div(id='status-info-banner', children=[
                html.Span("⏳ Initializing...", style={'color': '#6c757d', 'fontSize': '13px'})
            ], style={
                'padding': '12px 20px',
                'backgroundColor': 'rgba(0, 212, 255, 0.05)',
                'border': '1px solid rgba(0, 212, 255, 0.2)',
                'borderRadius': '8px',
                'marginBottom': '20px',
                'display': 'flex',
                'alignItems': 'center',
                'gap': '20px',
                'flexWrap': 'wrap'
            })
        ])
    ]),
    
    # Main Content Row
    dbc.Row([
        # Control Panel (Sidebar)
        dbc.Col(create_controls_sidebar(), width=3),
        
        # Charts Area
        dbc.Col([
            # Stats Cards
            create_stats_cards(),
            
            # Charts Tabs
            create_charts_tabs()
        ], width=9)
    ]),
    
    # Auto-refresh interval
    dcc.Interval(
        id='interval-component',
        interval=DASHBOARD_UPDATE_INTERVAL,
        n_intervals=0
    ),
    
    # Store for alerts
    dcc.Store(id='alerts-store', data=[])
    
], fluid=True, style={
    'padding': '24px',
    'backgroundColor': '#0d1117',
    'minHeight': '100vh'
})


# ============================================================================
# CALLBACKS
# ============================================================================

@app.callback(
    [Output('price-stats-card', 'children'),
     Output('regression-stats-card', 'children'),
     Output('stationarity-card', 'children'),
     Output('alert-log', 'children'),
     Output('status-text', 'children'),
     Output('status-text', 'className'),
     Output('alerts-store', 'data'),
     Output('status-info-banner', 'children')],  # NEW: Status info banner
    [Input('interval-component', 'n_intervals'),
     Input('refresh-btn', 'n_clicks'),
     Input('symbol-x-dropdown', 'value'),
     Input('symbol-y-dropdown', 'value'),
     Input('interval-dropdown', 'value'),
     Input('window-slider', 'value'),
     Input('zscore-threshold', 'value')],
    [State('alerts-store', 'data')]
)
def update_stats(n_intervals, n_clicks, symbol_x, symbol_y, interval, window, threshold, alerts):
    """Update all statistics cards."""
    
    # Helper function to create status banner
    def create_status_banner(last_update_str=None, status_class="warning"):
        """Create the status info banner with timestamp and settings."""
        if not last_update_str:
            return [html.Span("⏳ Waiting for data...", style={'color': '#ffc107', 'fontSize': '13px'})]
        
        # Parse timestamp
        try:
            last_update_dt = datetime.fromisoformat(last_update_str.replace('Z', '+00:00'))
            time_str = last_update_dt.strftime("%H:%M:%S")
            date_str = last_update_dt.strftime("%Y-%m-%d")
        except:
            time_str = "N/A"
            date_str = ""
        
        # Status color based on freshness
        if status_class == "success":
            status_color = "#00ff88"
            status_bg = "rgba(0, 255, 136, 0.1)"
            status_border = "rgba(0, 255, 136, 0.3)"
        else:
            status_color = "#ffc107"
            status_bg = "rgba(255, 193, 7, 0.1)"
            status_border = "rgba(255, 193, 7, 0.3)"
        
        return [
            # Live indicator
            html.Div([
                html.Span("●", style={'color': status_color, 'fontSize': '16px', 'marginRight': '8px'}),
                html.Span("LIVE DATA", style={
                    'color': status_color,
                    'fontSize': '11px',
                    'fontWeight': '700',
                    'letterSpacing': '1px'
                })
            ], style={
                'display': 'flex',
                'alignItems': 'center',
                'padding': '6px 14px',
                'backgroundColor': status_bg,
                'border': f'1px solid {status_border}',
                'borderRadius': '20px'
            }),
            
            # Last update
            html.Div([
                html.Span("🕒 ", style={'marginRight': '6px'}),
                html.Span("LAST UPDATE: ", style={
                    'color': '#6c757d',
                    'fontSize': '11px',
                    'fontWeight': '700',
                    'marginRight': '6px'
                }),
                html.Span(f"{time_str}", style={
                    'color': '#00d4ff',
                    'fontSize': '13px',
                    'fontWeight': '700',
                    'marginRight': '4px'
                }),
                html.Span(f"({date_str})", style={
                    'color': '#6c757d',
                    'fontSize': '10px'
                }) if date_str else None
            ], style={'display': 'flex', 'alignItems': 'center'}),
            
            # Timeframe
            html.Div([
                html.Span("⏱️ ", style={'marginRight': '6px'}),
                html.Span("TIMEFRAME: ", style={
                    'color': '#6c757d',
                    'fontSize': '11px',
                    'fontWeight': '700',
                    'marginRight': '6px'
                }),
                html.Span(interval.upper(), style={
                    'color': '#00d4ff',
                    'fontSize': '13px',
                    'fontWeight': '700'
                })
            ], style={'display': 'flex', 'alignItems': 'center'}),
            
            # Rolling Window
            html.Div([
                html.Span("📊 ", style={'marginRight': '6px'}),
                html.Span("WINDOW: ", style={
                    'color': '#6c757d',
                    'fontSize': '11px',
                    'fontWeight': '700',
                    'marginRight': '6px'
                }),
                html.Span(f"{window} periods", style={
                    'color': '#00d4ff',
                    'fontSize': '13px',
                    'fontWeight': '700'
                })
            ], style={'display': 'flex', 'alignItems': 'center'})
        ]
    
    try:
        # Fetch pairs analytics
        response = requests.get(
            f"{API_BASE}/pairs",
            params={
                'symbol_x': symbol_x,
                'symbol_y': symbol_y,
                'interval': interval,
                'window': window
            },
            timeout=10
        )
        
        if response.status_code == 404:
            # Not enough data yet
            status_banner = create_status_banner(None, "warning")
            return [
                html.P("⏳ Collecting data...", className="text-warning"),
                html.P("⏳ Collecting data...", className="text-warning"),
                html.P("⏳ Collecting data...", className="text-warning"),
                [html.P("No alerts yet", className="text-muted small")],
                "Waiting for data",
                "text-warning",
                alerts if alerts else [],
                status_banner
            ]
        
        if response.status_code != 200:
            status_banner = create_status_banner(None, "warning")
            return [
                html.Div([
                    html.P("❌ API Error", className="text-danger"),
                    html.P(f"Status: {response.status_code}", className="small text-muted")
                ]),
                html.P(f"Status {response.status_code}", className="text-danger"),
                html.P(f"Status {response.status_code}", className="text-danger"),
                [],
                "API Error",
                "text-danger",
                alerts if alerts else [],
                status_banner
            ]
        
        data = response.json()
        
        # Check if we have required data
        if 'regression' not in data:
            status_banner = create_status_banner(None, "warning")
            return [
                html.P("⏳ Computing analytics...", className="text-warning"),
                html.P("⏳ Computing analytics...", className="text-warning"),
                html.P("⏳ Computing analytics...", className="text-warning"),
                [html.P("Waiting for sufficient data", className="text-muted small")],
                "Computing",
                "text-warning",
                alerts if alerts else [],
                status_banner
            ]
        
        # Price stats card - COMPACT
        price_card = html.Div([
            html.Div([
                html.Span("Beta (β):", className="text-muted", style={'fontSize': '10px'}),
                html.Span(f"{data['regression']['hedge_ratio']:.4f}", style={'fontWeight': '700', 'marginLeft': 'auto'})
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px'}),
            html.Div([
                html.Span("R²:", className="text-muted", style={'fontSize': '10px'}),
                html.Span(f"{data['regression']['r_squared']:.4f}", style={'fontWeight': '700', 'marginLeft': 'auto'})
            ], style={'display': 'flex', 'alignItems': 'center'}),
        ])
        
        # Regression card - COMPACT
        z_score_latest = data.get('z_score', {}).get('latest', 0)
        reg_card = html.Div([
            html.Div([
                html.Span("Intercept:", className="text-muted", style={'fontSize': '10px'}),
                html.Span(f"{data['regression']['intercept']:.5f}", style={'fontWeight': '700', 'marginLeft': 'auto'})
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px'}),
            html.Div([
                html.Span("Z-Score:", className="text-muted", style={'fontSize': '10px'}),
                html.Span(f"{z_score_latest:.2f}", style={'fontWeight': '700', 'marginLeft': 'auto', 'color': '#00d4ff'})
            ], style={'display': 'flex', 'alignItems': 'center'})
        ])
        
        # Stationarity card - COMPACT
        adf = data.get('stationarity', {})
        p_value = adf.get('p_value', 1)
        is_stationary = adf.get('is_stationary', False)
        
        stat_card = html.Div([
            html.Div([
                html.Span("Status:", className="text-muted", style={'fontSize': '10px'}),
                html.Span(
                    "✅ STATIONARY" if is_stationary else "❌ NON-STAT", 
                    style={
                        'fontWeight': '700', 
                        'marginLeft': 'auto', 
                        'fontSize': '10px',
                        'color': '#00ff88' if is_stationary else '#ff4444'
                    }
                )
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px'}),
            html.Div([
                html.Span("p-value:", className="text-muted", style={'fontSize': '10px'}),
                html.Span(f"{p_value:.4f}", style={'fontWeight': '700', 'marginLeft': 'auto'})
            ], style={'display': 'flex', 'alignItems': 'center'})
        ]) if adf else html.Div("Loading...", style={'fontSize': '10px'})
        
        # Check for alerts
        if alerts is None:
            alerts = []
        
        z_score_data = data.get('z_score', {})
        latest_z = z_score_data.get('latest')
        if latest_z and not str(latest_z) == 'nan' and threshold and abs(latest_z) > threshold:
            timestamp = datetime.now().strftime("%H:%M")
            # Compact alert message
            alert_msg = f"[{timestamp}] Z:{latest_z:.2f} > {threshold}"
            alerts.insert(0, alert_msg)
            alerts = alerts[:20]  # Keep last 20
        
        # Compact Alerts List
        alert_items = [
            html.Div(alert, style={
                'fontSize': '10px', 
                'padding': '2px 0', 
                'borderBottom': '1px solid rgba(255,255,255,0.05)',
                'color': '#ffc107',
                'whiteSpace': 'nowrap',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis'
            }) for alert in alerts
        ] if alerts else [html.Div("No active alerts", style={'fontSize': '10px', 'color': '#6c757d'})]
        
        # Create status banner with successful data
        last_update_timestamp = data.get('last_update')
        status_banner = create_status_banner(last_update_timestamp, "success")
        
        return [price_card, reg_card, stat_card, alert_items, "Connected", "text-success", alerts, status_banner]
        
    except requests.Timeout:
        status_banner = create_status_banner(None, "warning")
        error_content = html.Div("⏱️ Timeout", style={'fontSize': '11px', 'color': '#ffc107'})
        return [error_content, error_content, error_content, [], "Timeout", "text-warning", alerts if alerts else [], status_banner]
    except requests.ConnectionError:
        status_banner = create_status_banner(None, "warning")
        error_content = html.Div("🔌 Error", style={'fontSize': '11px', 'color': '#ff4444'})
        return [error_content, error_content, error_content, [], "Connection Error", "text-danger", alerts if alerts else [], status_banner]
    except Exception as e:
        status_banner = create_status_banner(None, "warning")
        error_details = str(e)[:100]
        return [
            html.Div([
                html.P("❌ Error", className="text-danger"),
                html.P(error_details, className="small text-muted")
            ]),
            html.P(f"Error: {error_details}", className="text-danger small"),
            html.P("See console for details", className="text-danger small"),
            [],
            "Error",
            "text-danger",
            alerts if alerts else [],
            status_banner
        ]


@app.callback(
    Output('tab-content', 'children'),
    [Input('chart-tabs', 'active_tab'),
     Input('interval-component', 'n_intervals'),
     Input('symbol-x-dropdown', 'value'),
     Input('symbol-y-dropdown', 'value'),
     Input('interval-dropdown', 'value'),
     Input('window-slider', 'value')]
)
def render_tab_content(active_tab, n_intervals, symbol_x, symbol_y, interval, window):
    """Render the selected tab's chart."""
    
    if active_tab == "tab-price":
        return create_price_chart(symbol_x, symbol_y, interval)
    elif active_tab == "tab-spread":
        return create_spread_chart(symbol_x, symbol_y, interval, window)
    elif active_tab == "tab-correlation":
        return create_correlation_chart(symbol_x, symbol_y, interval, window)
    elif active_tab == "tab-heatmap":
        return create_heatmap_chart(interval, window)
    
    return html.P("Select a tab", className="text-muted")


def create_price_chart(symbol_x, symbol_y, interval):
    """Create price comparison chart."""
    try:
        # Fetch OHLC data for both symbols
        resp_x = requests.get(f"{API_BASE}/ohlc/{symbol_x}", params={'interval': interval, 'limit': 100}, timeout=5)
        resp_y = requests.get(f"{API_BASE}/ohlc/{symbol_y}", params={'interval': interval, 'limit': 100}, timeout=5)
        
        # Check response status
        if resp_x.status_code != 200 or resp_y.status_code != 200:
            return html.Div([
                html.P("⏳ Waiting for data...", className="text-warning text-center mt-5"),
                html.P("Please wait 60 seconds for initial data collection", className="text-muted text-center")
            ])
        
        data_x = resp_x.json()
        data_y = resp_y.json()
        
        # Check if bars exist and have data
        if 'bars' not in data_x or not data_x['bars']:
            return html.Div([
                html.P(f"⏳ No data yet for {symbol_x}", className="text-warning text-center mt-5"),
                html.P("Collecting data... Please wait", className="text-muted text-center")
            ])
        
        if 'bars' not in data_y or not data_y['bars']:
            return html.Div([
                html.P(f"⏳ No data yet for {symbol_y}", className="text-warning text-center mt-5"),
                html.P("Collecting data... Please wait", className="text-muted text-center")
            ])
        
        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add traces
        fig.add_trace(
            go.Scatter(
                x=[b['timestamp'] for b in data_x['bars']],
                y=[b['close'] for b in data_x['bars']],
                name=symbol_x,
                line=dict(color='#3b82f6', width=2),
                mode='lines'
            ),
            secondary_y=False
        )
        
        fig.add_trace(
            go.Scatter(
                x=[b['timestamp'] for b in data_y['bars']],
                y=[b['close'] for b in data_y['bars']],
                name=symbol_y,
                line=dict(color='#10b981', width=2),
                mode='lines'
            ),
            secondary_y=True
        )
        
        # Update layout
        fig.update_layout(
            title=f"Price Comparison ({interval}) - {len(data_x['bars'])} bars",
            hovermode='x unified',
            height=500,
            template='plotly_dark',
            showlegend=True,
            legend=dict(x=0, y=1)
        )
        
        fig.update_xaxes(title_text="Time")
        fig.update_yaxes(title_text=symbol_x, secondary_y=False)
        fig.update_yaxes(title_text=symbol_y, secondary_y=True)
        
        return dcc.Graph(figure=fig, config={'displayModeBar': True})
        
    except requests.Timeout:
        return html.P("⏱️ Request timeout - API may be starting up", className="text-warning text-center mt-5")
    except KeyError as e:
        return html.Div([
            html.P(f"⏳ Data structure error: {str(e)}", className="text-warning text-center mt-5"),
            html.P("This usually means data hasn't been collected yet. Please wait 60 seconds.", className="text-muted text-center")
        ])
    except Exception as e:
        return html.Div([
            html.P(f"❌ Error loading chart: {str(e)}", className="text-danger text-center mt-5"),
            html.P("Check that Flask API is running on port 5000", className="text-muted text-center small")
        ])


def create_spread_chart(symbol_x, symbol_y, interval, window):
    """Create spread & z-score chart."""
    try:
        response = requests.get(
            f"{API_BASE}/pairs",
            params={'symbol_x': symbol_x, 'symbol_y': symbol_y, 'interval': interval, 'window': window},
            timeout=5
        )
        
        if response.status_code != 200:
            return html.Div([
                html.P("⏳ Waiting for pairs analytics...", className="text-warning text-center mt-5"),
                html.P(f"Need at least 30 aligned {interval} bars for {symbol_x} and {symbol_y}", className="text-muted text-center")
            ])
        
        data = response.json()
        
        # Check if we have spread data
        if 'spread' not in data or not data['spread'].get('values'):
            return html.Div([
                html.P("⏳ Computing spread analytics...", className="text-warning text-center mt-5"),
                html.P("Please wait for data accumulation", className="text-muted text-center")
            ])
        
        # Create figure
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Spread trace
        indices = list(range(len(data['spread']['values'])))
        fig.add_trace(
            go.Scatter(
                x=indices,
                y=data['spread']['values'],
                name='Spread',
                line=dict(color='#8b5cf6', width=2),
                mode='lines'
            ),
            secondary_y=False
        )
        
        # Z-score trace
        if 'z_score' in data and data['z_score'].get('values'):
            fig.add_trace(
                go.Scatter(
                    x=indices,
                    y=data['z_score']['values'],
                    name='Z-Score',
                    line=dict(color='#f59e0b', width=2),
                    mode='lines'
                ),
                secondary_y=True
            )
            
            # Threshold lines
            fig.add_hline(y=2, line_dash="dash", line_color="red", secondary_y=True, annotation_text="+2σ")
            fig.add_hline(y=-2, line_dash="dash", line_color="red", secondary_y=True, annotation_text="-2σ")
            fig.add_hline(y=0, line_dash="dot", line_color="gray", secondary_y=True)
        
        fig.update_layout(
            title=f"Spread & Z-Score Analysis - {len(data['spread']['values'])} points",
            hovermode='x unified',
            height=500,
            template='plotly_dark',
            showlegend=True
        )
        
        fig.update_xaxes(title_text="Time Index")
        fig.update_yaxes(title_text="Spread ($)", secondary_y=False)
        fig.update_yaxes(title_text="Z-Score", secondary_y=True)
        
        return dcc.Graph(figure=fig, config={'displayModeBar': True})
        
    except requests.Timeout:
        return html.P("⏱️ Request timeout - please wait", className="text-warning text-center mt-5")
    except Exception as e:
        return html.Div([
            html.P(f"❌ Error: {str(e)}", className="text-danger text-center mt-5"),
            html.P("Pairs analytics require sufficient aligned data", className="text-muted text-center small")
        ])


def create_correlation_chart(symbol_x, symbol_y, interval, window):
    """Create rolling correlation chart."""
    try:
        response = requests.get(
            f"{API_BASE}/pairs",
            params={'symbol_x': symbol_x, 'symbol_y': symbol_y, 'interval': interval, 'window': window}
        )
        data = response.json()
        
        corr_data = data.get('correlation', {})
        if not corr_data:
            return html.P("No correlation data available", className="text-muted")
        
        history = corr_data.get('history', [])
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=[h['timestamp'] for h in history],
            y=[h['value'] for h in history],
            name='Correlation',
            line=dict(color='#06b6d4', width=2),
            mode='lines+markers',
            marker=dict(size=4)
        ))
        
        # Reference lines
        fig.add_hline(y=0, line_dash="dot", line_color="gray")
        fig.add_hline(y=0.5, line_dash="dash", line_color="green", annotation_text="Strong +")
        fig.add_hline(y=-0.5, line_dash="dash", line_color="red", annotation_text="Strong -")
        
        fig.update_layout(
            title=f"Rolling Correlation ({window} period)",
            hovermode='x',
            height=500,
            template='plotly_dark',
            yaxis=dict(range=[-1, 1])
        )
        
        fig.update_xaxes(title_text="Time")
        fig.update_yaxes(title_text="Correlation Coefficient")
        
        return dcc.Graph(figure=fig, config={'displayModeBar': True})
        
    except Exception as e:
        return html.P(f"Error loading chart: {str(e)}", className="text-danger")


def create_heatmap_chart(interval, window):
    """Create correlation heatmap (placeholder - would need multi-symbol support)."""
    return html.Div([
        html.P("Correlation Heatmap", className="text-center text-muted"),
        html.P("Multi-symbol correlation matrix coming soon...", className="text-center text-muted small")
    ])


@app.callback(
    Output('download-csv', 'data'),
    Input('export-btn', 'n_clicks'),
    [State('symbol-x-dropdown', 'value'),
     State('symbol-y-dropdown', 'value'),
     State('interval-dropdown', 'value')],
    prevent_initial_call=True
)
def export_csv(n_clicks, symbol_x, symbol_y, interval):
    """Trigger CSV download."""
    if n_clicks:
        url = f"{API_BASE}/export/csv/{symbol_x}/{symbol_y}?interval={interval}"
        return dcc.send_data_frame(None, filename="analytics.csv", url=url)




@app.callback(
    Output('upload-status', 'children'),
    Input('upload-ohlc', 'contents'),
    State('upload-ohlc', 'filename'),
    prevent_initial_call=True
)
def handle_upload(contents, filename):
    """Handle OHLC CSV file upload."""
    if not contents:
        return ""
    
    try:
        # Parse uploaded file
        content_type, content_string = contents.split(',')
        import base64
        decoded = base64.b64decode(content_string)
        
        # Send to Flask API
        files = {'file': (filename, decoded, 'text/csv')}
        response = requests.post(f"{API_BASE}/upload/ohlc", files=files, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            summary = data.get('summary', {})
            
            return html.Div([
                html.Div("✅ Upload Successful!", style={'color': '#00ff88', 'fontWeight': '700', 'marginBottom': '4px'}),
                html.Div(f"Bars: {summary.get('total_bars', 0)}", style={'color': '#6c757d', 'fontSize': '10px'}),
                html.Div(f"Symbols: {', '.join(summary.get('symbols', []))}", style={'color': '#6c757d', 'fontSize': '10px'}),
            ])
        else:
            error = response.json().get('error', 'Unknown error')
            return html.Div([
                html.Div("❌ Upload Failed", style={'color': '#ff4444', 'fontWeight': '700', 'marginBottom': '4px'}),
                html.Div(error, style={'color': '#ff4444', 'fontSize': '10px'})
            ])
            
    except Exception as e:
        return html.Div([
            html.Div("❌ Upload Error", style={'color': '#ff4444', 'fontWeight': '700', 'marginBottom': '4px'}),
            html.Div(str(e)[:50], style={'color': '#ff4444', 'fontSize': '10px'})
        ])


if __name__ == '__main__':
    from ..config import DASH_HOST, DASH_PORT
    
    app.run_server(
        host=DASH_HOST,
        port=DASH_PORT,
        debug=True
    )

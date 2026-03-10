import dash
from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import io
import base64

app = dash.Dash(__name__)

# --- STYLING ---
COLORS = {
    'background': '#f4f7f9',
    'panel': '#ffffff',
    'text': '#1a2a6c',
    'accent': '#006699'
}

app.layout = html.Div(style={'fontFamily': 'Segoe UI, sans-serif', 'padding': '20px', 'backgroundColor': COLORS['background']}, children=[
    html.H1("Vessel Performance Dashboard", style={'textAlign': 'center', 'color': COLORS['text'], 'fontWeight': 'bold'}),
    
    # 1. Upload Section
    dcc.Upload(
        id='upload-data',
        children=html.Div(['Drag and Drop or ', html.B('Select File')]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '10px',
            'textAlign': 'center', 'backgroundColor': COLORS['panel'], 'marginBottom': '10px'
        },
        multiple=False
    ),

    # 2. Metadata Information Bar
    html.Div(id='vessel-info-bar', style={
        'backgroundColor': '#e1e8ed', 'padding': '15px', 'borderRadius': '10px', 
        'marginBottom': '20px', 'fontSize': '0.95em', 'color': '#333', 'display': 'flex', 'justifyContent': 'space-around', 'flexWrap': 'wrap'
    }),

    # 3. Main Content
    html.Div(id='dashboard-content', children=[
        # Top: Sankey Diagram
        html.Div([
            html.H3("Average Fuel Distribution (L/h)", style={'padding': '15px 0 0 20px', 'color': COLORS['text']}),
            dcc.Graph(id='sankey-graph', style={'height': '400px'})
        ], style={'backgroundColor': COLORS['panel'], 'borderRadius': '15px', 'boxShadow': '0 4px 10px rgba(0,0,0,0.05)', 'marginBottom': '20px'}),
        
        # Bottom: Trend Chart & Stats Table
        html.Div([
            html.H3("Trend Analysis & Statistics", style={'padding': '15px 0 0 20px', 'color': COLORS['text']}),
            
            html.Div([
                # Selection & Table
                html.Div([
                    html.Label("Select Measurement:", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(id='column-dropdown', placeholder="Choose a sensor...", style={'marginBottom': '20px'}),
                    
                    html.B("Sensor Statistics:"),
                    html.Div(id='stats-table-container', style={'marginTop': '10px'})
                ], style={'width': '25%', 'padding': '20px', 'display': 'inline-block', 'verticalAlign': 'top'}),
                
                # The Graph
                html.Div([
                    dcc.Graph(id='time-series-graph', style={'height': '500px'})
                ], style={'width': '70%', 'display': 'inline-block', 'padding': '10px'})
            ], style={'display': 'flex'})
            
        ], style={'backgroundColor': COLORS['panel'], 'borderRadius': '15px', 'boxShadow': '0 4px 10px rgba(0,0,0,0.05)'})
    ]),

    # Hidden Data Stores
    dcc.Store(id='stored-df-json'),
    dcc.Store(id='stored-averages'),
    dcc.Store(id='stored-metadata')
])

# --- DATA PROCESSING ---
def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    df = None
    for encoding in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
        try:
            decoded_str = decoded.decode(encoding)
            df = pd.read_csv(io.StringIO(decoded_str), sep='\t', engine='python')
            if len(df.columns) > 1: break
        except: continue
            
    if df is None: return None, None, None

    df.columns = [str(c).replace('"', '').strip() for c in df.columns]
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    df = df.dropna(subset=[time_col]).sort_values(time_col)

    # Calculate Time Metadata
    start_dt = df[time_col].min().strftime('%Y-%m-%d %H:%M')
    end_dt = df[time_col].max().strftime('%Y-%m-%d %H:%M')
    
    # Calculate interval (time step)
    diffs = df[time_col].diff().dt.total_seconds().dropna()
    if not diffs.empty:
        median_diff = diffs.median()
        if median_diff >= 60:
            interval = f"{int(median_diff / 60)} minute(s)"
        else:
            interval = f"{int(median_diff)} second(s)"
    else:
        interval = "Unknown"

    metadata = {
        'vessel_name': df['Name'].iloc[0] if 'Name' in df.columns else "Unknown",
        'metric_id': df['Metric'].iloc[0] if 'Metric' in df.columns else "N/A",
        'start_time': start_dt,
        'end_time': end_dt,
        'interval': interval
    }

    for col in df.columns:
        if col not in ['Time', 'Metric', 'Name']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if 'Fuel Rate' in col:
                q95 = df[col].quantile(0.95)
                if pd.notnull(q95) and q95 > 0:
                    df.loc[df[col] > q95 * 50, col] = 0 

    fuel_cols = [c for c in df.columns if 'Fuel Rate' in c]
    averages = df[fuel_cols].mean().to_dict()
    
    return df.to_json(date_format='iso', orient='split'), averages, metadata

# --- CALLBACKS ---

@app.callback(
    [Output('stored-df-json', 'data'), 
     Output('stored-averages', 'data'), 
     Output('stored-metadata', 'data'),
     Output('column-dropdown', 'options'),
     Output('vessel-info-bar', 'children')],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def update_store(contents, filename):
    if contents is None: return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    json_df, averages, meta = parse_contents(contents, filename)
    if json_df is None: return None, None, None, [], "Error loading file."
    
    df_temp = pd.read_json(json_df, orient='split')
    excluded = ['Time', 'Metric', 'Name']
    numeric_cols = [c for c in df_temp.columns if c not in excluded]
    options = [{'label': c, 'value': c} for c in numeric_cols]
    
    # Create Info Bar UI
    info_bar = [
        html.Div([html.B("Vessel: "), meta['vessel_name']], style={'margin': '5px 20px'}),
        html.Div([html.B("Period: "), f"{meta['start_time']} to {meta['end_time']}"], style={'margin': '5px 20px'}),
        html.Div([html.B("Interval: "), meta['interval']], style={'margin': '5px 20px'}),
        html.Div([html.B("Metric ID: "), meta['metric_id']], style={'margin': '5px 20px'})
    ]
    
    return json_df, averages, meta, options, info_bar

@app.callback(
    [Output('time-series-graph', 'figure'),
     Output('stats-table-container', 'children')],
    [Input('stored-df-json', 'data'), Input('column-dropdown', 'value')]
)
def update_graph_and_table(json_df, selected_col):
    if not json_df or not selected_col: 
        return go.Figure().update_layout(title="Select a sensor"), ""
    
    df = pd.read_json(json_df, orient='split')
    
    # Calculate Stats
    val_min = df[selected_col].min()
    val_max = df[selected_col].max()
    val_avg = df[selected_col].mean()
    
    stats_data = [
        {'Metric': 'Minimum', 'Value': f"{val_min:.2f}"},
        {'Metric': 'Maximum', 'Value': f"{val_max:.2f}"},
        {'Metric': 'Average', 'Value': f"{val_avg:.2f}"}
    ]
    
    table = dash_table.DataTable(
        data=stats_data,
        columns=[{'name': i, 'id': i} for i in ['Metric', 'Value']],
        style_cell={'textAlign': 'left', 'padding': '10px', 'fontFamily': 'Segoe UI'},
        style_header={'backgroundColor': '#f1f1f1', 'fontWeight': 'bold'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'}]
    )
    
    # Create Graph
    fig = px.line(df, x=df.columns[0], y=selected_col)
    fig.update_layout(template="plotly_white", xaxis_title="Time", yaxis_title=f"{selected_col}")
    fig.update_traces(line_color=COLORS['accent'])
    
    return fig, table

@app.callback(
    Output('sankey-graph', 'figure'),
    Input('stored-averages', 'data')
)
def update_sankey(averages):
    if not averages: return go.Figure()
    filtered_avg = {k: v for k, v in averages.items() if v > 0.05}
    labels = ["TOTAL FUEL CONSUMPTION"] + list(filtered_avg.keys())
    sources = [0] * len(filtered_avg)
    targets = list(range(1, len(filtered_avg) + 1))
    values = list(filtered_avg.values())
    total_val = sum(values)

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20, thickness=30,
            label=[f"{label}\n({val:.1f} L/h)" if i>0 else f"{label}\n({total_val:.1f} L/h)" 
                   for i, (label, val) in enumerate(zip(labels, [total_val] + values))],
            color=COLORS['accent']
        ),
        link=dict(source=sources, target=targets, value=values, color="rgba(0, 102, 153, 0.2)")
    )])
    fig.update_layout(title_text=f"Energy Balance (Mean flow)", font_size=12, margin=dict(l=20, r=20, t=50, b=20))
    return fig

if __name__ == '__main__':
    app.run(debug=True)
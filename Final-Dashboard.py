import dash
from dash import dcc, html, Input, Output
import plotly.graph_objs as go
import yfinance as yf
import pandas as pd
import numpy as np


# Function to calculate volatility metrics
def calculate_volatility(tickers, start_date, end_date):
    # Fetch data
    data = yf.download(tickers, start=start_date, end=end_date, progress=False)['Adj Close']
    returns = data.pct_change().dropna()
    
    # Calculate standard deviation
    std_dev = returns.std()
    
    return std_dev

# Function to get EMA crossover signals
def ema_crossover_signals(ticker, start_date, end_date):
    # Fetch historical data
    data = yf.download(ticker, start=start_date, end=end_date, progress=False)
    
    # Calculate EMA
    data['EMA_short'] = data['Close'].ewm(span=50, adjust=False).mean()
    data['EMA_long'] = data['Close'].ewm(span=150, adjust=False).mean()
    
    # Create signals
    data['Signal'] = 0
    data.loc[data.index[1:], 'Signal'] = np.where(data['EMA_short'][1:] > data['EMA_long'][1:], 1, 0)
    data['Position'] = data['Signal'].diff()
    
    # Create Plotly figure for EMA crossover
    fig_ema = go.Figure()
    fig_ema.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='Close Price'))
    fig_ema.add_trace(go.Scatter(x=data.index, y=data['EMA_short'], mode='lines', name='EMA Short'))
    fig_ema.add_trace(go.Scatter(x=data.index, y=data['EMA_long'], mode='lines', name='EMA Long'))
    
    # Plot Buy and Sell signals
    fig_ema.add_trace(go.Scatter(x=data[data['Position'] == 1].index, y=data[data['Position'] == 1]['Close'], 
                             mode='markers', name='Buy Signal', marker=dict(symbol='triangle-up', size=10, color='green')))
    fig_ema.add_trace(go.Scatter(x=data[data['Position'] == -1].index, y=data[data['Position'] == -1]['Close'], 
                             mode='markers', name='Sell Signal', marker=dict(symbol='triangle-down', size=10, color='red')))
    
    fig_ema.update_layout(title=f'EMA Crossover Signals for {ticker}', xaxis_title='Date', yaxis_title='Price')

    # Create Plotly figure for closing price
    fig_close = go.Figure()
    fig_close.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='Close Price'))
    fig_close.update_layout(title=f'Closing Price for {ticker}', xaxis_title='Date', yaxis_title='Price')

    return fig_ema, fig_close

# List of ticker symbols
ticker_df = pd.read_csv('Tickers.csv')
ticker_symbols = ticker_df['Tickers'].tolist()

# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Define the layout of the dashboard
app.layout = html.Div([
    html.H1("Stock Analysis Dashboard"),
    dcc.Tabs(id='tabs', value='tab-price-comparison', children=[
        dcc.Tab(label='Price Comparison', value='tab-price-comparison'),
        dcc.Tab(label='EMA Crossover Strategy and Closing Price', value='tab-ema-crossover'),
        dcc.Tab(label='Volatility Metrics', value='tab-volatility-metrics')  # New tab for volatility metrics
    ]),
    html.Div(id='tabs-content')
])

# Define callback to switch tabs
@app.callback(
    Output('tabs-content', 'children'),
    [Input('tabs', 'value')]
)
def render_content(tab):
    if tab == 'tab-price-comparison':
        return html.Div([
            html.Label("Select the first stock symbol:"),
            dcc.Dropdown(id='stock1-dropdown', options=[{'label': symbol, 'value': symbol} for symbol in ticker_symbols], value='MSFT'),
            html.Label("Select the second stock symbol:"),
            dcc.Dropdown(id='stock2-dropdown', options=[{'label': symbol, 'value': symbol} for symbol in ticker_symbols], value='INTC'),
             html.Label('Select Start Date:'),
            dcc.DatePickerSingle(id='start-date-picker', date='2000-01-01'),
            html.Label('Select End Date:'),
            dcc.DatePickerSingle(id='end-date-picker', date='2024-04-01'),
           html.Div(id='price-comparison-output')
        ])
    elif tab == 'tab-ema-crossover':
        return html.Div([
            html.Label('Select Ticker:'),
            dcc.Dropdown(id='ticker-dropdown', options=[{'label': ticker, 'value': ticker} for ticker in ticker_symbols], value='MSFT'),
            html.Label('Select Start Date:'),
            dcc.DatePickerSingle(id='start-date-picker', date='2000-01-01'),
            html.Label('Select End Date:'),
            dcc.DatePickerSingle(id='end-date-picker', date='2024-04-01'),
            html.Div(id='ema-crossover-plot')
        ])
    elif tab == 'tab-volatility-metrics':
        return html.Div([
            html.Label('Select Start Date:'),
            dcc.DatePickerSingle(id='volatility-start-date-picker', date='2000-01-01'),
            html.Label('Select End Date:'),
            dcc.DatePickerSingle(id='volatility-end-date-picker', date='2024-04-01'),
            dcc.Graph(id='volatility-metrics-plot')
        ])

# Define callback to update plot for EMA crossover strategy
@app.callback(
    Output('ema-crossover-plot', 'children'),
    [Input('ticker-dropdown', 'value'),
     Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date')]
)
def update_ema_crossover_plot(ticker, start_date, end_date):
    fig_ema, fig_close = ema_crossover_signals(ticker, start_date, end_date)
    return [
        dcc.Graph(figure=fig_ema),
        dcc.Graph(figure=fig_close)
    ]

# Define callback to update plot for volatility metrics
@app.callback(
    Output('volatility-metrics-plot', 'figure'),
    [Input('volatility-start-date-picker', 'date'),
     Input('volatility-end-date-picker', 'date')]
)
def update_volatility_metrics_plot(start_date, end_date):
    selected_tickers = ticker_symbols  # Use all tickers
    std_dev_data = calculate_volatility(selected_tickers, start_date, end_date)
    
    # If std_dev_data is a single float64 value, create a DataFrame manually
    if isinstance(std_dev_data, np.float64):
        df = pd.DataFrame({'Ticker': [selected_tickers], 'Standard_Deviation': [std_dev_data]})
    else:
        df = pd.DataFrame({'Ticker': std_dev_data.index, 'Standard_Deviation': std_dev_data.values})
    
    # Plotting the bar graph
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['Ticker'], y=df['Standard_Deviation'], name='Standard Deviation'))
    fig.update_layout(title='Volatility Metrics', xaxis_title='Ticker', yaxis_title='Standard Deviation')
    return fig

# Define callback to update the graph based on user input for price comparison

@app.callback(
    Output('price-comparison-output', 'children'),
    [Input('stock1-dropdown', 'value'),
     Input('stock2-dropdown', 'value'),
     Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date')]
)
def update_price_comparison(stock1, stock2, start_date, end_date):
    data = yf.download([stock1, stock2], start=start_date, end=end_date)["Adj Close"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data[stock1], mode='lines', name=stock1))
    fig.add_trace(go.Scatter(x=data.index, y=data[stock2], mode='lines', name=stock2))
    fig.update_layout(title='Stock Comparison', xaxis_title='Date', yaxis_title='Price (USD)', showlegend=True, hovermode='x')
    return dcc.Graph(figure=fig)

if __name__ == '__main__':
    app.run_server(debug=True)

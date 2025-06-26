import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import re
import os
from typing import Dict, List, Tuple

# Page configuration
st.set_page_config(
    page_title="Crypto Portfolio Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)


def parse_currency(value):
    """Parse currency string to float"""
    if pd.isna(value) or value == "None":
        return 0.0
    # Remove currency symbols and commas
    cleaned = re.sub(r'[$,]', '', str(value))
    try:
        return float(cleaned)
    except:
        return 0.0


def parse_amount(value):
    """Parse amount string to float"""
    if pd.isna(value) or value == "None":
        return 0.0
    try:
        return float(value)
    except:
        return 0.0


def parse_timestamp(timestamp_str):
    """Parse timestamp from filename format"""
    try:
        # Remove .csv extension if present
        timestamp_str = timestamp_str.replace('.csv', '')
        # Parse DD-MM-YYYY_HH-MM-SS format
        return pd.to_datetime(timestamp_str, format='%d-%m-%Y_%H-%M-%S')
    except:
        try:
            # Try alternative format
            return pd.to_datetime(timestamp_str)
        except:
            return pd.NaT


def load_and_process_data(uploaded_file):
    """Load and process the portfolio CSV data"""
    try:
        df = pd.read_csv(uploaded_file)

        # Parse numeric columns
        df['usd_value_numeric'] = df['usd_value'].apply(parse_currency)
        df['price_numeric'] = df['price'].apply(parse_currency)
        df['amount_numeric'] = df['amount'].apply(parse_amount)

        # Filter out zero value positions
        df = df[df['usd_value_numeric'] > 0]

        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None


def load_historical_data(file_path=None):
    """Load historical portfolio data"""
    try:
        if file_path is None:
            file_path = "portfolio_data/ALL_PORTFOLIOS_HISTORY.csv"

        if not os.path.exists(file_path):
            return None

        df = pd.read_csv(file_path)

        # Parse numeric columns
        df['usd_value_numeric'] = df['usd_value'].apply(parse_currency)
        df['price_numeric'] = df['price'].apply(parse_currency)
        df['amount_numeric'] = df['amount'].apply(parse_amount)

        # Parse timestamps
        df['timestamp'] = df['source_file_timestamp'].apply(parse_timestamp)
        df = df.dropna(subset=['timestamp'])

        # Filter out zero value positions
        df = df[df['usd_value_numeric'] > 0]

        # Sort by timestamp
        df = df.sort_values('timestamp')

        return df
    except Exception as e:
        st.error(f"Error loading historical data: {e}")
        return None


def calculate_portfolio_timeline(df):
    """Calculate total portfolio value over time"""
    timeline = df.groupby(['timestamp']).agg({
        'usd_value_numeric': 'sum'
    }).reset_index()

    timeline = timeline.sort_values('timestamp')
    return timeline


def calculate_wallet_timeline(df):
    """Calculate wallet values over time"""
    wallet_timeline = df.groupby(['timestamp', 'wallet_label']).agg({
        'usd_value_numeric': 'sum'
    }).reset_index()

    return wallet_timeline


def calculate_token_timeline(df):
    """Calculate individual token values over time"""
    token_timeline = df.groupby(['timestamp', 'coin']).agg({
        'usd_value_numeric': 'sum',
        'amount_numeric': 'sum',
        'price_numeric': 'mean'
    }).reset_index()

    return token_timeline


def calculate_apy(start_value, end_value, days):
    """Calculate APY given start/end values and time period"""
    if start_value <= 0 or days <= 0:
        return 0

    years = days / 365.25
    if years <= 0:
        return 0

    try:
        apy = ((end_value / start_value) ** (1 / years)) - 1
        return apy * 100  # Convert to percentage
    except:
        return 0


def calculate_volatility(values):
    """Calculate volatility (standard deviation of returns)"""
    if len(values) < 2:
        return 0
    
    returns = []
    for i in range(1, len(values)):
        if values[i-1] > 0:
            returns.append((values[i] - values[i-1]) / values[i-1])
    
    if len(returns) == 0:
        return 0
    
    return np.std(returns) * 100  # Convert to percentage


def calculate_max_drawdown(values):
    """Calculate maximum drawdown"""
    if len(values) < 2:
        return 0
    
    peak = values[0]
    max_drawdown = 0
    
    for value in values:
        if value > peak:
            peak = value
        
        drawdown = (peak - value) / peak if peak > 0 else 0
        max_drawdown = max(max_drawdown, drawdown)
    
    return max_drawdown * 100  # Convert to percentage


def calculate_sharpe_ratio(values, risk_free_rate=0.02):
    """Calculate Sharpe ratio (simplified version)"""
    if len(values) < 2:
        return 0
    
    returns = []
    for i in range(1, len(values)):
        if values[i-1] > 0:
            returns.append((values[i] - values[i-1]) / values[i-1])
    
    if len(returns) == 0:
        return 0
    
    avg_return = np.mean(returns) * 365  # Annualized
    volatility = np.std(returns) * np.sqrt(365)  # Annualized
    
    if volatility == 0:
        return 0
    
    return (avg_return - risk_free_rate) / volatility


def get_performance_metrics(timeline_df):
    """Calculate various performance metrics"""
    if len(timeline_df) < 2:
        return {}

    timeline_df = timeline_df.sort_values('timestamp')
    current_value = timeline_df['usd_value_numeric'].iloc[-1]

    metrics = {}

    # Current timestamp
    current_time = timeline_df['timestamp'].iloc[-1]

    # 1 Day performance
    one_day_ago = current_time - timedelta(days=1)
    day_data = timeline_df[timeline_df['timestamp'] >= one_day_ago]
    if len(day_data) >= 2:
        day_start = day_data['usd_value_numeric'].iloc[0]
        metrics['1d_return'] = ((current_value - day_start) / day_start * 100) if day_start > 0 else 0
        metrics['1d_apy'] = calculate_apy(day_start, current_value, 1)

    # 7 Day performance
    week_ago = current_time - timedelta(days=7)
    week_data = timeline_df[timeline_df['timestamp'] >= week_ago]
    if len(week_data) >= 2:
        week_start = week_data['usd_value_numeric'].iloc[0]
        days_diff = (current_time - week_data['timestamp'].iloc[0]).days
        metrics['7d_return'] = ((current_value - week_start) / week_start * 100) if week_start > 0 else 0
        metrics['7d_apy'] = calculate_apy(week_start, current_value, days_diff)

    # 30 Day performance
    month_ago = current_time - timedelta(days=30)
    month_data = timeline_df[timeline_df['timestamp'] >= month_ago]
    if len(month_data) >= 2:
        month_start = month_data['usd_value_numeric'].iloc[0]
        days_diff = (current_time - month_data['timestamp'].iloc[0]).days
        metrics['30d_return'] = ((current_value - month_start) / month_start * 100) if month_start > 0 else 0
        metrics['30d_apy'] = calculate_apy(month_start, current_value, days_diff)

    # All time performance
    start_value = timeline_df['usd_value_numeric'].iloc[0]
    total_days = (current_time - timeline_df['timestamp'].iloc[0]).days
    metrics['all_time_return'] = ((current_value - start_value) / start_value * 100) if start_value > 0 else 0
    metrics['all_time_apy'] = calculate_apy(start_value, current_value, total_days)

    # Risk metrics
    values = timeline_df['usd_value_numeric'].values
    metrics['volatility'] = calculate_volatility(values)
    metrics['max_drawdown'] = calculate_max_drawdown(values)
    metrics['sharpe_ratio'] = calculate_sharpe_ratio(values)
    
    # Additional metrics
    metrics['max_value'] = timeline_df['usd_value_numeric'].max()
    metrics['min_value'] = timeline_df['usd_value_numeric'].min()
    metrics['current_drawdown'] = ((current_value - metrics['max_value']) / metrics['max_value'] * 100) if metrics['max_value'] > 0 else 0

    return metrics


def create_overview_metrics(df):
    """Create overview metrics cards"""
    total_value = df['usd_value_numeric'].sum()
    total_wallets = df['wallet_label'].nunique()
    total_tokens = df['coin'].nunique()
    total_protocols = df['protocol'].nunique()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Portfolio Value",
            value=f"${total_value:,.2f}",
            delta=None
        )

    with col2:
        st.metric(
            label="Number of Wallets",
            value=f"{total_wallets}",
            delta=None
        )

    with col3:
        st.metric(
            label="Unique Tokens",
            value=f"{total_tokens}",
            delta=None
        )

    with col4:
        st.metric(
            label="Protocols/Platforms",
            value=f"{total_protocols}",
            delta=None
        )


def create_wallet_breakdown_chart(df):
    """Create wallet breakdown pie chart"""
    wallet_totals = df.groupby('wallet_label')['usd_value_numeric'].sum().reset_index()
    wallet_totals = wallet_totals.sort_values('usd_value_numeric', ascending=False)

    fig = px.pie(
        wallet_totals,
        values='usd_value_numeric',
        names='wallet_label',
        title="Portfolio Distribution by Wallet",
        hover_data=['usd_value_numeric'],
        labels={'usd_value_numeric': 'USD Value'}
    )

    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>'
    )

    return fig


def create_blockchain_breakdown_chart(df):
    """Create blockchain breakdown chart"""
    blockchain_totals = df.groupby('blockchain')['usd_value_numeric'].sum().reset_index()
    blockchain_totals = blockchain_totals.sort_values('usd_value_numeric', ascending=False)

    fig = px.bar(
        blockchain_totals,
        x='blockchain',
        y='usd_value_numeric',
        title="Asset Distribution by Blockchain",
        labels={'usd_value_numeric': 'USD Value', 'blockchain': 'Blockchain'},
        color='usd_value_numeric',
        color_continuous_scale='viridis'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False
    )

    return fig


def create_top_holdings_chart(df, top_n=10):
    """Create top holdings chart"""
    token_totals = df.groupby(['coin', 'token_name'])['usd_value_numeric'].sum().reset_index()
    token_totals = token_totals.sort_values('usd_value_numeric', ascending=False).head(top_n)

    # Create display name combining symbol and name
    token_totals['display_name'] = token_totals['coin'] + ' (' + token_totals['token_name'] + ')'

    fig = px.bar(
        token_totals,
        x='usd_value_numeric',
        y='display_name',
        orientation='h',
        title=f"Top {top_n} Token Holdings by Value",
        labels={'usd_value_numeric': 'USD Value', 'display_name': 'Token'},
        color='usd_value_numeric',
        color_continuous_scale='plasma'
    )

    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        showlegend=False
    )

    return fig


def create_protocol_breakdown_chart(df):
    """Create protocol breakdown chart"""
    protocol_totals = df.groupby('protocol')['usd_value_numeric'].sum().reset_index()
    protocol_totals = protocol_totals.sort_values('usd_value_numeric', ascending=False).head(15)

    fig = px.treemap(
        protocol_totals,
        path=['protocol'],
        values='usd_value_numeric',
        title="Asset Distribution by Protocol/Platform",
        color='usd_value_numeric',
        color_continuous_scale='blues'
    )

    return fig


def create_wallet_comparison_chart(df):
    """Create wallet comparison chart showing top tokens per wallet"""
    # Get top 5 tokens per wallet by value
    wallet_tokens = []
    for wallet in df['wallet_label'].unique():
        wallet_data = df[df['wallet_label'] == wallet]
        top_tokens = wallet_data.groupby('coin')['usd_value_numeric'].sum().reset_index()
        top_tokens = top_tokens.sort_values('usd_value_numeric', ascending=False).head(5)
        top_tokens['wallet_label'] = wallet
        wallet_tokens.append(top_tokens)

    combined_data = pd.concat(wallet_tokens, ignore_index=True)

    fig = px.bar(
        combined_data,
        x='wallet_label',
        y='usd_value_numeric',
        color='coin',
        title="Top Token Holdings by Wallet",
        labels={'usd_value_numeric': 'USD Value', 'wallet_label': 'Wallet'},
        barmode='stack'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def create_detailed_table(df):
    """Create detailed holdings table with search and filter"""
    st.subheader("📋 Detailed Holdings")

    # Create filters
    col1, col2, col3 = st.columns(3)

    with col1:
        wallet_filter = st.selectbox(
            "Filter by Wallet",
            options=['All'] + list(df['wallet_label'].unique()),
            key="wallet_filter"
        )

    with col2:
        blockchain_filter = st.selectbox(
            "Filter by Blockchain",
            options=['All'] + list(df['blockchain'].unique()),
            key="blockchain_filter"
        )

    with col3:
        min_value = st.number_input(
            "Minimum USD Value",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="min_value_filter"
        )

    # Apply filters
    filtered_df = df.copy()

    if wallet_filter != 'All':
        filtered_df = filtered_df[filtered_df['wallet_label'] == wallet_filter]

    if blockchain_filter != 'All':
        filtered_df = filtered_df[filtered_df['blockchain'] == blockchain_filter]

    filtered_df = filtered_df[filtered_df['usd_value_numeric'] >= min_value]

    # Sort by USD value descending
    filtered_df = filtered_df.sort_values('usd_value_numeric', ascending=False)

    # Display table with selected columns
    display_columns = [
        'wallet_label', 'blockchain', 'coin', 'token_name',
        'protocol', 'amount', 'price', 'usd_value'
    ]

    st.dataframe(
        filtered_df[display_columns],
        use_container_width=True,
        hide_index=True
    )

    # Show summary of filtered data
    st.info(f"Showing {len(filtered_df)} positions with total value: ${filtered_df['usd_value_numeric'].sum():,.2f}")


# Performance Analysis Functions

def create_portfolio_performance_chart(timeline_df):
    """Create comprehensive portfolio performance chart"""
    if len(timeline_df) < 2:
        return None
    
    timeline_df = timeline_df.sort_values('timestamp')
    
    # Calculate cumulative returns
    initial_value = timeline_df['usd_value_numeric'].iloc[0]
    timeline_df['cumulative_return'] = ((timeline_df['usd_value_numeric'] / initial_value) - 1) * 100
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Portfolio Value Over Time', 'Cumulative Return (%)'),
        vertical_spacing=0.1,
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
    )
    
    # Portfolio value
    fig.add_trace(
        go.Scatter(
            x=timeline_df['timestamp'],
            y=timeline_df['usd_value_numeric'],
            mode='lines',
            name='Portfolio Value',
            line=dict(color='#00d4aa', width=2),
            hovertemplate='<b>$%{y:,.2f}</b><br>%{x}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Cumulative return
    fig.add_trace(
        go.Scatter(
            x=timeline_df['timestamp'],
            y=timeline_df['cumulative_return'],
            mode='lines',
            name='Cumulative Return',
            line=dict(color='#ff6b6b', width=2),
            hovertemplate='<b>%{y:.2f}%</b><br>%{x}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Add zero line for returns
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)
    
    fig.update_layout(
        title="Portfolio Performance Analysis",
        height=600,
        showlegend=False,
        hovermode='x unified'
    )
    
    return fig


def create_asset_performance_comparison(df, selected_assets=None, period_days=30):
    """Create asset performance comparison chart"""
    if selected_assets is None or len(selected_assets) == 0:
        return None
    
    current_time = df['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    
    filtered_df = df[df['timestamp'] >= period_start]
    
    performance_data = []
    
    for asset in selected_assets:
        asset_data = filtered_df[filtered_df['coin'] == asset]
        if len(asset_data) == 0:
            continue
            
        asset_timeline = asset_data.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
        asset_timeline = asset_timeline.sort_values('timestamp')
        
        if len(asset_timeline) >= 2:
            initial_value = asset_timeline['usd_value_numeric'].iloc[0]
            
            for _, row in asset_timeline.iterrows():
                cumulative_return = ((row['usd_value_numeric'] / initial_value) - 1) * 100 if initial_value > 0 else 0
                performance_data.append({
                    'timestamp': row['timestamp'],
                    'asset': asset,
                    'cumulative_return': cumulative_return
                })
    
    if not performance_data:
        return None
    
    perf_df = pd.DataFrame(performance_data)
    
    fig = px.line(
        perf_df,
        x='timestamp',
        y='cumulative_return',
        color='asset',
        title=f"Asset Performance Comparison (Last {period_days} Days)",
        labels={'cumulative_return': 'Cumulative Return (%)', 'timestamp': 'Date'}
    )
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    
    fig.update_layout(
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


def create_performance_metrics_dashboard(timeline_df):
    """Create comprehensive performance metrics dashboard"""
    metrics = get_performance_metrics(timeline_df)
    
    if not metrics:
        return None
    
    # Create metrics cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "1D Return",
            f"{metrics.get('1d_return', 0):.2f}%",
            delta=f"APY: {metrics.get('1d_apy', 0):.1f}%"
        )
    
    with col2:
        st.metric(
            "7D Return", 
            f"{metrics.get('7d_return', 0):.2f}%",
            delta=f"APY: {metrics.get('7d_apy', 0):.1f}%"
        )
    
    with col3:
        st.metric(
            "30D Return",
            f"{metrics.get('30d_return', 0):.2f}%", 
            delta=f"APY: {metrics.get('30d_apy', 0):.1f}%"
        )
    
    with col4:
        st.metric(
            "All Time Return",
            f"{metrics.get('all_time_return', 0):.2f}%",
            delta=f"APY: {metrics.get('all_time_apy', 0):.1f}%"
        )
    
    # Risk metrics
    st.markdown("---")
    st.subheader("📊 Risk Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Volatility",
            f"{metrics.get('volatility', 0):.2f}%",
            help="Standard deviation of daily returns"
        )
    
    with col2:
        st.metric(
            "Max Drawdown",
            f"{metrics.get('max_drawdown', 0):.2f}%",
            help="Maximum peak-to-trough decline"
        )
    
    with col3:
        st.metric(
            "Current Drawdown",
            f"{metrics.get('current_drawdown', 0):.2f}%",
            help="Current decline from all-time high"
        )
    
    with col4:
        st.metric(
            "Sharpe Ratio",
            f"{metrics.get('sharpe_ratio', 0):.2f}",
            help="Risk-adjusted return metric"
        )


def create_asset_performance_table(df, period_days=30):
    """Create detailed asset performance table"""
    current_time = df['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    
    asset_performances = []
    
    for asset in df['coin'].unique():
        asset_data = df[df['coin'] == asset]
        
        # Current data
        current_data = asset_data[asset_data['timestamp'] == current_time]
        if len(current_data) == 0:
            continue
            
        current_value = current_data['usd_value_numeric'].sum()
        current_price = current_data['price_numeric'].mean()
        current_amount = current_data['amount_numeric'].sum()
        
        # Period data
        period_data = asset_data[asset_data['timestamp'] >= period_start]
        
        if len(period_data) >= 2:
            period_timeline = period_data.groupby('timestamp').agg({
                'usd_value_numeric': 'sum',
                'price_numeric': 'mean',
                'amount_numeric': 'sum'
            }).reset_index()
            period_timeline = period_timeline.sort_values('timestamp')
            
            start_value = period_timeline['usd_value_numeric'].iloc[0]
            start_price = period_timeline['price_numeric'].iloc[0]
            
            # Calculate metrics
            value_return = ((current_value - start_value) / start_value * 100) if start_value > 0 else 0
            price_return = ((current_price - start_price) / start_price * 100) if start_price > 0 else 0
            
            values = period_timeline['usd_value_numeric'].values
            volatility = calculate_volatility(values)
            max_drawdown = calculate_max_drawdown(values)
            
            days_diff = (current_time - period_timeline['timestamp'].iloc[0]).days
            apy = calculate_apy(start_value, current_value, days_diff)
            
            asset_performances.append({
                'Asset': asset,
                'Current Value': f"${current_value:,.2f}",
                'Current Price': f"${current_price:,.4f}",
                'Amount': f"{current_amount:,.4f}",
                f'{period_days}D Value Return (%)': f"{value_return:.2f}%",
                f'{period_days}D Price Return (%)': f"{price_return:.2f}%",
                'APY (%)': f"{apy:.2f}%",
                'Volatility (%)': f"{volatility:.2f}%",
                'Max Drawdown (%)': f"{max_drawdown:.2f}%"
            })
    
    if asset_performances:
        return pd.DataFrame(asset_performances)
    else:
        return None


def create_correlation_heatmap(df, selected_assets=None, period_days=30):
    """Create asset correlation heatmap"""
    if selected_assets is None or len(selected_assets) < 2:
        return None
    
    current_time = df['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    
    filtered_df = df[df['timestamp'] >= period_start]
    
    # Create returns matrix
    returns_data = {}
    
    for asset in selected_assets:
        asset_data = filtered_df[filtered_df['coin'] == asset]
        asset_timeline = asset_data.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
        asset_timeline = asset_timeline.sort_values('timestamp')
        
        if len(asset_timeline) >= 2:
            returns = []
            values = asset_timeline['usd_value_numeric'].values
            for i in range(1, len(values)):
                if values[i-1] > 0:
                    returns.append((values[i] - values[i-1]) / values[i-1])
            
            if len(returns) > 0:
                returns_data[asset] = returns
    
    if len(returns_data) < 2:
        return None
    
    # Calculate correlation matrix
    min_length = min(len(returns) for returns in returns_data.values())
    
    correlation_matrix = []
    assets = list(returns_data.keys())
    
    for asset1 in assets:
        row = []
        for asset2 in assets:
            if asset1 == asset2:
                correlation = 1.0
            else:
                returns1 = returns_data[asset1][:min_length]
                returns2 = returns_data[asset2][:min_length]
                correlation = np.corrcoef(returns1, returns2)[0, 1]
                if np.isnan(correlation):
                    correlation = 0.0
            row.append(correlation)
        correlation_matrix.append(row)
    
    fig = px.imshow(
        correlation_matrix,
        x=assets,
        y=assets,
        color_continuous_scale='RdBu',
        aspect="auto",
        title=f"Asset Correlation Matrix (Last {period_days} Days)",
        labels=dict(color="Correlation")
    )
    
    # Add correlation values as text
    for i in range(len(assets)):
        for j in range(len(assets)):
            fig.add_annotation(
                x=j, y=i,
                text=f"{correlation_matrix[i][j]:.2f}",
                showarrow=False,
                font=dict(color="white" if abs(correlation_matrix[i][j]) > 0.5 else "black")
            )
    
    return fig


def performance_analysis_page():
    """Dedicated performance analysis page"""
    st.title("📈 Performance Analysis")
    st.markdown("---")

    # Load historical data
    historical_df = load_historical_data()

    if historical_df is None:
        st.warning("⚠️ Historical data file not found. Please run the master portfolio tracker first.")
        st.info("Expected file location: `portfolio_data/ALL_PORTFOLIOS_HISTORY.csv`")

        # Option to upload file manually
        uploaded_historical = st.file_uploader(
            "Or upload historical data file manually",
            type=['csv'],
            key="performance_historical_upload"
        )

        if uploaded_historical:
            historical_df = load_and_process_data(uploaded_historical)
            if historical_df is not None and 'source_file_timestamp' in historical_df.columns:
                historical_df['timestamp'] = historical_df['source_file_timestamp'].apply(parse_timestamp)
                historical_df = historical_df.dropna(subset=['timestamp'])
                historical_df = historical_df.sort_values('timestamp')

        if historical_df is None:
            return

    # Calculate timeline
    portfolio_timeline = calculate_portfolio_timeline(historical_df)

    if len(portfolio_timeline) < 2:
        st.error("Insufficient data for performance analysis. Need at least 2 data points.")
        return

    # Performance overview
    st.header("🎯 Portfolio Performance Overview")
    create_performance_metrics_dashboard(portfolio_timeline)

    # Portfolio performance chart
    st.markdown("---")
    st.header("📊 Portfolio Performance Charts")
    
    portfolio_perf_chart = create_portfolio_performance_chart(portfolio_timeline)
    if portfolio_perf_chart:
        st.plotly_chart(portfolio_perf_chart, use_container_width=True)

    # Time period selector for detailed analysis
    st.markdown("---")
    st.header("🔍 Detailed Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        analysis_period = st.selectbox(
            "Select Analysis Period",
            options=[7, 14, 30, 60, 90, 180, 365],
            index=2,  # Default to 30 days
            format_func=lambda x: f"{x} days",
            key="analysis_period"
        )
    
    with col2:
        available_assets = sorted(historical_df['coin'].unique())
        selected_assets = st.multiselect(
            "Select Assets for Comparison",
            options=available_assets,
            default=available_assets[:5] if len(available_assets) >= 5 else available_assets,
            key="selected_assets"
        )

    # Asset performance comparison
    if selected_assets:
        st.subheader(f"📈 Asset Performance Comparison ({analysis_period} Days)")
        
        asset_comparison_chart = create_asset_performance_comparison(
            historical_df, selected_assets, analysis_period
        )
        if asset_comparison_chart:
            st.plotly_chart(asset_comparison_chart, use_container_width=True)

        # Asset performance table
        st.subheader(f"📊 Asset Performance Metrics ({analysis_period} Days)")
        asset_perf_table = create_asset_performance_table(historical_df, analysis_period)
        if asset_perf_table is not None:
            st.dataframe(asset_perf_table, use_container_width=True, hide_index=True)

        # Correlation analysis
        if len(selected_assets) >= 2:
            st.subheader(f"🔗 Asset Correlation Analysis ({analysis_period} Days)")
            correlation_chart = create_correlation_heatmap(
                historical_df, selected_assets, analysis_period
            )
            if correlation_chart:
                st.plotly_chart(correlation_chart, use_container_width=True)
                
                st.info("""
                **Correlation Interpretation:**
                - **1.0**: Perfect positive correlation (assets move together)
                - **0.0**: No correlation (assets move independently)
                - **-1.0**: Perfect negative correlation (assets move opposite)
                - **>0.7**: Strong positive correlation
                - **<-0.7**: Strong negative correlation
                """)

    # Individual asset deep dive
    st.markdown("---")
    st.header("🎯 Individual Asset Analysis")
    
    selected_asset = st.selectbox(
        "Select an asset for detailed analysis:",
        options=available_assets,
        key="individual_asset_selector"
    )

    if selected_asset:
        asset_data = historical_df[historical_df['coin'] == selected_asset]
        asset_timeline = calculate_token_timeline(asset_data)

        if len(asset_timeline) >= 2:
            # Asset metrics
            current_time = asset_timeline['timestamp'].max()
            current_value = asset_timeline[asset_timeline['timestamp'] == current_time]['usd_value_numeric'].iloc[0]
            current_price = asset_timeline[asset_timeline['timestamp'] == current_time]['price_numeric'].iloc[0]
            current_amount = asset_timeline[asset_timeline['timestamp'] == current_time]['amount_numeric'].iloc[0]

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(f"{selected_asset} Portfolio Value", f"${current_value:,.2f}")

            with col2:
                st.metric(f"{selected_asset} Price", f"${current_price:,.6f}")

            with col3:
                st.metric(f"{selected_asset} Amount", f"{current_amount:,.4f}")

            # Asset timeline chart with multiple metrics
            fig_asset = make_subplots(
                rows=3, cols=1,
                subplot_titles=(
                    f'{selected_asset} Portfolio Value',
                    f'{selected_asset} Price',
                    f'{selected_asset} Amount'
                ),
                vertical_spacing=0.08
            )

            # Portfolio value
            fig_asset.add_trace(
                go.Scatter(
                    x=asset_timeline['timestamp'],
                    y=asset_timeline['usd_value_numeric'],
                    mode='lines+markers',
                    name='Portfolio Value',
                    line=dict(color='#00d4aa', width=2)
                ),
                row=1, col=1
            )

            # Price
            fig_asset.add_trace(
                go.Scatter(
                    x=asset_timeline['timestamp'],
                    y=asset_timeline['price_numeric'],
                    mode='lines+markers',
                    name='Price',
                    line=dict(color='#ff6b6b', width=2)
                ),
                row=2, col=1
            )

            # Amount
            fig_asset.add_trace(
                go.Scatter(
                    x=asset_timeline['timestamp'],
                    y=asset_timeline['amount_numeric'],
                    mode='lines+markers',
                    name='Amount',
                    line=dict(color='#4ECDC4', width=2)
                ),
                row=3, col=1
            )

            fig_asset.update_layout(
                title=f"{selected_asset} Detailed Performance",
                height=800,
                showlegend=False,
                hovermode='x unified'
            )

            st.plotly_chart(fig_asset, use_container_width=True)

            # Asset-specific performance metrics
            asset_metrics = get_performance_metrics(asset_timeline.rename(columns={'usd_value_numeric': 'usd_value_numeric'}))
            
            if asset_metrics:
                st.subheader(f"📊 {selected_asset} Performance Metrics")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("30D Return", f"{asset_metrics.get('30d_return', 0):.2f}%")
                
                with col2:
                    st.metric("Volatility", f"{asset_metrics.get('volatility', 0):.2f}%")
                
                with col3:
                    st.metric("Max Drawdown", f"{asset_metrics.get('max_drawdown', 0):.2f}%")
                
                with col4:
                    st.metric("Sharpe Ratio", f"{asset_metrics.get('sharpe_ratio', 0):.2f}")


def historical_analysis_page():
    """Historical analysis page"""
    st.title("📈 Historical Portfolio Analysis")
    st.markdown("---")

    # Load historical data
    historical_df = load_historical_data()

    if historical_df is None:
        st.warning("⚠️ Historical data file not found. Please run the master portfolio tracker first.")
        st.info("Expected file location: `portfolio_data/ALL_PORTFOLIOS_HISTORY.csv`")

        # Option to upload file manually
        uploaded_historical = st.file_uploader(
            "Or upload historical data file manually",
            type=['csv'],
            key="historical_upload"
        )

        if uploaded_historical:
            historical_df = load_and_process_data(uploaded_historical)
            if historical_df is not None and 'source_file_timestamp' in historical_df.columns:
                historical_df['timestamp'] = historical_df['source_file_timestamp'].apply(parse_timestamp)
                historical_df = historical_df.dropna(subset=['timestamp'])
                historical_df = historical_df.sort_values('timestamp')

        if historical_df is None:
            return

    # Calculate timelines
    portfolio_timeline = calculate_portfolio_timeline(historical_df)
    wallet_timeline = calculate_wallet_timeline(historical_df)

    # Overview metrics
    st.header("📊 Performance Overview")

    if len(portfolio_timeline) >= 2:
        # Performance metrics table
        metrics_df = create_performance_metrics_table(portfolio_timeline)
        if metrics_df is not None:
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("🎯 Performance Metrics")
                st.dataframe(metrics_df, use_container_width=True, hide_index=True)

            with col2:
                # Current portfolio value
                current_value = portfolio_timeline['usd_value_numeric'].iloc[-1]
                start_value = portfolio_timeline['usd_value_numeric'].iloc[0]
                total_return = ((current_value - start_value) / start_value * 100) if start_value > 0 else 0

                st.metric(
                    "Current Portfolio Value",
                    f"${current_value:,.2f}",
                    f"{total_return:+.2f}%"
                )

                # Data range
                start_date = portfolio_timeline['timestamp'].min().strftime('%Y-%m-%d')
                end_date = portfolio_timeline['timestamp'].max().strftime('%Y-%m-%d')
                st.metric(
                    "Data Range",
                    f"{start_date}",
                    f"to {end_date}"
                )

    st.markdown("---")

    # Charts section
    st.header("📈 Historical Analysis")

    # Portfolio value over time
    if len(portfolio_timeline) >= 2:
        portfolio_fig = create_portfolio_value_chart(portfolio_timeline)
        st.plotly_chart(portfolio_fig, use_container_width=True)

    # Two column layout for additional charts
    col1, col2 = st.columns(2)

    with col1:
        # Wallet performance
        if len(wallet_timeline) >= 2:
            wallet_fig = create_wallet_performance_chart(wallet_timeline)
            st.plotly_chart(wallet_fig, use_container_width=True)

    with col2:
        # Top performers
        performers_fig = create_top_performers_chart(historical_df, period_days=30)
        if performers_fig:
            st.plotly_chart(performers_fig, use_container_width=True)

    # Allocation evolution
    if len(historical_df) >= 2:
        allocation_fig = create_allocation_evolution_chart(historical_df)
        st.plotly_chart(allocation_fig, use_container_width=True)

    st.markdown("---")

    # Asset-specific analysis
    st.header("🔍 Asset-Specific Analysis")

    # Asset selector
    available_tokens = sorted(historical_df['coin'].unique())
    selected_token = st.selectbox(
        "Select an asset for detailed analysis:",
        options=available_tokens,
        key="asset_selector"
    )

    if selected_token:
        token_data = historical_df[historical_df['coin'] == selected_token]
        token_timeline = calculate_token_timeline(token_data)

        if len(token_timeline) >= 2:
            col1, col2, col3 = st.columns(3)

            # Token metrics
            current_token_value = token_timeline['usd_value_numeric'].iloc[-1]
            start_token_value = token_timeline['usd_value_numeric'].iloc[0]
            token_return = ((
                                        current_token_value - start_token_value) / start_token_value * 100) if start_token_value > 0 else 0

            with col1:
                st.metric(
                    f"{selected_token} Value",
                    f"${current_token_value:,.2f}",
                    f"{token_return:+.2f}%"
                )

            with col2:
                current_price = token_timeline['price_numeric'].iloc[-1]
                start_price = token_timeline['price_numeric'].iloc[0]
                price_change = ((current_price - start_price) / start_price * 100) if start_price > 0 else 0

                st.metric(
                    f"{selected_token} Price",
                    f"${current_price:,.4f}",
                    f"{price_change:+.2f}%"
                )

            with col3:
                current_amount = token_timeline['amount_numeric'].iloc[-1]
                start_amount = token_timeline['amount_numeric'].iloc[0]
                amount_change = ((current_amount - start_amount) / start_amount * 100) if start_amount > 0 else 0

                st.metric(
                    f"{selected_token} Amount",
                    f"{current_amount:,.4f}",
                    f"{amount_change:+.2f}%"
                )

            # Token timeline chart
            fig_token = go.Figure()

            # Add value line
            fig_token.add_trace(go.Scatter(
                x=token_timeline['timestamp'],
                y=token_timeline['usd_value_numeric'],
                mode='lines+markers',
                name='USD Value',
                yaxis='y',
                line=dict(color='#00d4aa', width=2)
            ))

            # Add price line on secondary y-axis
            fig_token.add_trace(go.Scatter(
                x=token_timeline['timestamp'],
                y=token_timeline['price_numeric'],
                mode='lines+markers',
                name='Price',
                yaxis='y2',
                line=dict(color='#ff6b6b', width=2)
            ))

            fig_token.update_layout(
                title=f"{selected_token} Performance Over Time",
                xaxis_title="Date",
                yaxis=dict(title="USD Value", side="left"),
                yaxis2=dict(title="Price (USD)", side="right", overlaying="y"),
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig_token, use_container_width=True)

    # Summary statistics
    st.markdown("---")
    st.header("📊 Summary Statistics")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Dataset Information")
        st.write(f"**Total Records:** {len(historical_df):,}")
        st.write(f"**Unique Timestamps:** {historical_df['timestamp'].nunique():,}")
        st.write(
            f"**Date Range:** {historical_df['timestamp'].min().strftime('%Y-%m-%d')} to {historical_df['timestamp'].max().strftime('%Y-%m-%d')}")
        st.write(f"**Tracked Wallets:** {historical_df['wallet_label'].nunique()}")
        st.write(f"**Tracked Assets:** {historical_df['coin'].nunique()}")
        st.write(f"**Tracked Protocols:** {historical_df['protocol'].nunique()}")

    with col2:
        st.subheader("Value Distribution")
        total_current_value = historical_df[historical_df['timestamp'] == historical_df['timestamp'].max()][
            'usd_value_numeric'].sum()

        # Top wallets by current value
        latest_data = historical_df[historical_df['timestamp'] == historical_df['timestamp'].max()]
        top_wallets = latest_data.groupby('wallet_label')['usd_value_numeric'].sum().sort_values(ascending=False)

        st.write("**Top Wallets by Value:**")
        for wallet, value in top_wallets.head(5).items():
            percentage = (value / total_current_value * 100) if total_current_value > 0 else 0
            st.write(f"  {wallet}: ${value:,.2f} ({percentage:.1f}%)")


# Helper functions for portfolio value chart and performance metrics table
def create_portfolio_value_chart(timeline_df):
    """Create portfolio value over time chart"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=timeline_df['timestamp'],
        y=timeline_df['usd_value_numeric'],
        mode='lines+markers',
        name='Portfolio Value',
        line=dict(color='#00d4aa', width=3),
        marker=dict(size=6),
        hovertemplate='<b>%{y:$,.2f}</b><br>%{x}<extra></extra>'
    ))

    fig.update_layout(
        title="Portfolio Value Over Time",
        xaxis_title="Date",
        yaxis_title="USD Value",
        hovermode='x unified',
        showlegend=False
    )

    return fig


def create_wallet_performance_chart(wallet_timeline_df):
    """Create wallet performance over time chart"""
    fig = px.line(
        wallet_timeline_df,
        x='timestamp',
        y='usd_value_numeric',
        color='wallet_label',
        title="Wallet Performance Over Time",
        labels={'usd_value_numeric': 'USD Value', 'timestamp': 'Date'}
    )

    fig.update_layout(
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def create_top_performers_chart(df, period_days=30):
    """Create top performing assets chart"""
    current_time = df['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)

    # Get tokens that exist in both periods
    recent_data = df[df['timestamp'] >= period_start]

    if len(recent_data) == 0:
        return None

    # Calculate performance for each token
    performances = []

    for coin in recent_data['coin'].unique():
        coin_data = recent_data[recent_data['coin'] == coin]
        coin_timeline = coin_data.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
        coin_timeline = coin_timeline.sort_values('timestamp')

        if len(coin_timeline) >= 2:
            start_value = coin_timeline['usd_value_numeric'].iloc[0]
            end_value = coin_timeline['usd_value_numeric'].iloc[-1]

            if start_value > 0:
                performance = ((end_value - start_value) / start_value) * 100
                performances.append({
                    'coin': coin,
                    'performance': performance,
                    'start_value': start_value,
                    'end_value': end_value
                })

    if not performances:
        return None

    perf_df = pd.DataFrame(performances)
    perf_df = perf_df.sort_values('performance', ascending=False).head(10)

    # Create color scale based on performance
    colors = ['green' if x >= 0 else 'red' for x in perf_df['performance']]

    fig = px.bar(
        perf_df,
        x='coin',
        y='performance',
        title=f"Top Performing Assets (Last {period_days} Days)",
        labels={'performance': 'Performance (%)', 'coin': 'Token'},
        color='performance',
        color_continuous_scale='RdYlGn'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False
    )

    return fig


def create_allocation_evolution_chart(df):
    """Create allocation evolution over time"""
    # Get top 10 tokens by current value
    latest_data = df[df['timestamp'] == df['timestamp'].max()]
    top_tokens = latest_data.groupby('coin')['usd_value_numeric'].sum().nlargest(10).index

    # Filter data for top tokens only
    filtered_df = df[df['coin'].isin(top_tokens)]

    # Calculate allocation percentages over time
    timeline_allocations = []

    for timestamp in filtered_df['timestamp'].unique():
        timestamp_data = filtered_df[filtered_df['timestamp'] == timestamp]
        total_value = timestamp_data['usd_value_numeric'].sum()

        for coin in top_tokens:
            coin_value = timestamp_data[timestamp_data['coin'] == coin]['usd_value_numeric'].sum()
            allocation = (coin_value / total_value * 100) if total_value > 0 else 0

            timeline_allocations.append({
                'timestamp': timestamp,
                'coin': coin,
                'allocation': allocation
            })

    alloc_df = pd.DataFrame(timeline_allocations)

    fig = px.area(
        alloc_df,
        x='timestamp',
        y='allocation',
        color='coin',
        title="Portfolio Allocation Evolution Over Time",
        labels={'allocation': 'Allocation (%)', 'timestamp': 'Date'}
    )

    fig.update_layout(
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def create_performance_metrics_table(timeline_df):
    """Create performance metrics table"""
    metrics = get_performance_metrics(timeline_df)

    if not metrics:
        return None

    metrics_data = []

    periods = [
        ('1 Day', '1d'),
        ('7 Days', '7d'),
        ('30 Days', '30d'),
        ('All Time', 'all_time')
    ]

    for period_name, period_key in periods:
        return_key = f'{period_key}_return'
        apy_key = f'{period_key}_apy'

        if return_key in metrics and apy_key in metrics:
            metrics_data.append({
                'Period': period_name,
                'Return (%)': f"{metrics[return_key]:.2f}%",
                'APY (%)': f"{metrics[apy_key]:.2f}%"
            })

    # Add additional metrics
    if 'max_value' in metrics:
        metrics_data.append({
            'Period': 'Max Portfolio Value',
            'Return (%)': f"${metrics['max_value']:,.2f}",
            'APY (%)': '-'
        })

    if 'max_drawdown' in metrics:
        metrics_data.append({
            'Period': 'Max Drawdown',
            'Return (%)': f"{metrics['max_drawdown']:.2f}%",
            'APY (%)': '-'
        })

    return pd.DataFrame(metrics_data)


def main():
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Choose a page:",
        ["📊 Current Portfolio", "📈 Historical Analysis", "🎯 Performance Analysis"],
        key="page_selector"
    )

    if page == "📊 Current Portfolio":
        # Original portfolio analysis page
        st.title("💰 Crypto Portfolio Dashboard")
        st.markdown("---")

        # Sidebar for file upload
        st.sidebar.header("📂 Data Upload")
        uploaded_file = st.sidebar.file_uploader(
            "Upload your portfolio CSV file",
            type=['csv'],
            help="Upload the ALL_WALLETS_COMBINED CSV file",
            key="current_portfolio_upload"
        )

        if uploaded_file is not None:
            # Load and process data
            df = load_and_process_data(uploaded_file)

            if df is not None:
                st.success(f"✅ Successfully loaded {len(df)} portfolio positions")

                # Overview metrics
                st.header("📊 Portfolio Overview")
                create_overview_metrics(df)
                st.markdown("---")

                # Charts section
                st.header("📈 Portfolio Analysis")

                # Row 1: Wallet and Blockchain breakdown
                col1, col2 = st.columns(2)

                with col1:
                    wallet_fig = create_wallet_breakdown_chart(df)
                    st.plotly_chart(wallet_fig, use_container_width=True)

                with col2:
                    blockchain_fig = create_blockchain_breakdown_chart(df)
                    st.plotly_chart(blockchain_fig, use_container_width=True)

                # Row 2: Top holdings and Protocol breakdown
                col1, col2 = st.columns(2)

                with col1:
                    holdings_fig = create_top_holdings_chart(df)
                    st.plotly_chart(holdings_fig, use_container_width=True)

                with col2:
                    protocol_fig = create_protocol_breakdown_chart(df)
                    st.plotly_chart(protocol_fig, use_container_width=True)

                # Row 3: Wallet comparison
                st.subheader("🔍 Wallet Comparison")
                wallet_comparison_fig = create_wallet_comparison_chart(df)
                st.plotly_chart(wallet_comparison_fig, use_container_width=True)

                st.markdown("---")

                # Detailed table
                create_detailed_table(df)

                # Additional insights in sidebar
                st.sidebar.markdown("---")
                st.sidebar.header("📈 Quick Insights")

                # Top wallet by value
                top_wallet = df.groupby('wallet_label')['usd_value_numeric'].sum().idxmax()
                top_wallet_value = df.groupby('wallet_label')['usd_value_numeric'].sum().max()
                st.sidebar.metric(
                    "Top Wallet",
                    top_wallet,
                    f"${top_wallet_value:,.2f}"
                )

                # Most valuable token
                top_token = df.groupby('coin')['usd_value_numeric'].sum().idxmax()
                top_token_value = df.groupby('coin')['usd_value_numeric'].sum().max()
                st.sidebar.metric(
                    "Top Token",
                    top_token,
                    f"${top_token_value:,.2f}"
                )

                # Most used blockchain
                top_blockchain = df.groupby('blockchain')['usd_value_numeric'].sum().idxmax()
                top_blockchain_value = df.groupby('blockchain')['usd_value_numeric'].sum().max()
                st.sidebar.metric(
                    "Top Blockchain",
                    top_blockchain,
                    f"${top_blockchain_value:,.2f}"
                )

        else:
            st.info("👆 Please upload your portfolio CSV file using the sidebar to get started!")

            # Show example of expected file format
            st.subheader("📋 Expected File Format")
            st.write("Your CSV file should contain the following columns:")

            example_data = {
                'wallet_label': ['Main_Wallet', 'DeFi_Wallet'],
                'address': ['0x1234...', '0x5678...'],
                'blockchain': ['ETHEREUM', 'POLYGON'],
                'coin': ['ETH', 'MATIC'],
                'protocol': ['Wallet', 'Uniswap V3'],
                'price': ['$2,500.00', '$0.85'],
                'amount': ['1.5000', '1000.0000'],
                'usd_value': ['$3,750.00', '$850.00'],
                'token_name': ['Ethereum', 'Polygon'],
                'is_verified': ['True', 'True'],
                'logo_url': ['https://...', 'https://...']
            }

            example_df = pd.DataFrame(example_data)
            st.dataframe(example_df, use_container_width=True)

    elif page == "📈 Historical Analysis":
        historical_analysis_page()
    
    elif page == "🎯 Performance Analysis":
        performance_analysis_page()


if __name__ == "__main__":
    main()
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

    # Additional metrics
    metrics['max_value'] = timeline_df['usd_value_numeric'].max()
    metrics['min_value'] = timeline_df['usd_value_numeric'].min()
    metrics['max_drawdown'] = ((current_value - metrics['max_value']) / metrics['max_value'] * 100) if metrics[
                                                                                                           'max_value'] > 0 else 0

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


# Historical Analysis Functions

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


def historical_analysis_page():
    """Historical analysis page"""
    st.title("📈 Historical Portfolio Analysis")
    st.markdown("---")

    # Load historical data
    historical_df = load_historical_data()

    if historical_df is None:
        st.warning("⚠️ Historical data file not found. Please run the master portfolio tracker first.")
        st.info("Expected file location: `./portfolio_data/ALL_PORTFOLIOS_HISTORY.csv`")

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


def main():
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Choose a page:",
        ["📊 Current Portfolio", "📈 Historical Analysis"],
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


if __name__ == "__main__":
    main()
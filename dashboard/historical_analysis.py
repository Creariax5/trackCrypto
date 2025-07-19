import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta, datetime
import numpy as np
from utils import (
    load_historical_data, 
    load_and_process_data, 
    parse_timestamp,
    calculate_portfolio_timeline,
    calculate_wallet_timeline,
    calculate_token_timeline,
    get_performance_metrics
)


def format_asset_name(coin, protocol):
    """Format asset name with protocol if available"""
    if pd.isna(protocol) or protocol == '' or protocol.lower() == 'wallet':
        return coin
    return f"{coin} ({protocol})"


def calculate_apy(start_value, end_value, days):
    """Calculate APY from start and end values over a period"""
    if start_value <= 0 or days <= 0:
        return 0
    
    # APY = (End/Start)^(365/days) - 1
    return ((end_value / start_value) ** (365 / days) - 1) * 100


def create_portfolio_value_chart(timeline_df):
    """Create portfolio value over time chart with trend analysis"""
    fig = go.Figure()

    # Main portfolio line
    fig.add_trace(go.Scatter(
        x=timeline_df['timestamp'],
        y=timeline_df['usd_value_numeric'],
        mode='lines+markers',
        name='Portfolio Value',
        line=dict(color='#00d4aa', width=3),
        marker=dict(size=6),
        hovertemplate='<b>%{y:$,.2f}</b><br>%{x}<extra></extra>'
    ))

    # Add trend line
    if len(timeline_df) > 1:
        # Simple linear trend
        x_numeric = pd.to_numeric(timeline_df['timestamp'])
        z = np.polyfit(x_numeric, timeline_df['usd_value_numeric'], 1)
        p = np.poly1d(z)
        
        fig.add_trace(go.Scatter(
            x=timeline_df['timestamp'],
            y=p(x_numeric),
            mode='lines',
            name='Trend',
            line=dict(color='#ff6b6b', width=2, dash='dash'),
            opacity=0.7
        ))

    fig.update_layout(
        title="Portfolio Value Over Time",
        xaxis_title="Date",
        yaxis_title="USD Value",
        hovermode='x unified',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig

def create_protocol_allocation_chart(df):
    """Create protocol allocation pie chart"""
    latest_data = df[df['timestamp'] == df['timestamp'].max()]
    
    # Group by protocol
    protocol_values = latest_data.groupby('protocol')['usd_value_numeric'].sum().sort_values(ascending=False)
    
    # Combine smaller protocols
    total_value = protocol_values.sum()
    threshold = total_value * 0.02  # 2% threshold
    
    major_protocols = protocol_values[protocol_values >= threshold]
    others_value = protocol_values[protocol_values < threshold].sum()
    
    if others_value > 0:
        major_protocols['Others'] = others_value
    
    fig = px.pie(
        values=major_protocols.values,
        names=major_protocols.index,
        title="Portfolio Allocation by Protocol",
        hover_data=[major_protocols.values]
    )
    
    fig.update_traces(
        hovertemplate='<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>'
    )
    
    return fig


def create_performance_metrics_table(timeline_df):
    """Create enhanced performance metrics table"""
    if len(timeline_df) < 2:
        return None
        
    current_value = timeline_df['usd_value_numeric'].iloc[-1]
    
    metrics_data = []
    periods = [
        ('1 Day', 1),
        ('7 Days', 7),
        ('30 Days', 30),
        ('90 Days', 90),
        ('1 Year', 365),
        ('All Time', None)
    ]
    
    current_time = timeline_df['timestamp'].max()
    
    for period_name, days in periods:
        if days is None:
            # All time
            start_value = timeline_df['usd_value_numeric'].iloc[0]
            end_value = current_value
            actual_days = (current_time - timeline_df['timestamp'].min()).days
        else:
            period_start = current_time - timedelta(days=days)
            period_data = timeline_df[timeline_df['timestamp'] >= period_start]
            
            if len(period_data) == 0:
                continue
                
            start_value = period_data['usd_value_numeric'].iloc[0]
            end_value = current_value
            actual_days = days
        
        if start_value > 0:
            return_pct = ((end_value - start_value) / start_value) * 100
            apy = calculate_apy(start_value, end_value, actual_days) if actual_days > 0 else 0
            
            metrics_data.append({
                'Period': period_name,
                'Return (%)': f"{return_pct:+.2f}%",
                'APY (%)': f"{apy:+.2f}%",
                'Start Value': f"${start_value:,.2f}",
                'Current Value': f"${end_value:,.2f}"
            })
    
    # Add risk metrics
    if len(timeline_df) > 1:
        returns = timeline_df['usd_value_numeric'].pct_change().dropna()
        if len(returns) > 0:
            volatility = returns.std() * np.sqrt(365) * 100  # Annualized volatility
            max_value = timeline_df['usd_value_numeric'].max()
            max_drawdown = ((current_value - max_value) / max_value) * 100
            
            metrics_data.extend([
                {
                    'Period': 'Volatility (Ann.)',
                    'Return (%)': f"{volatility:.2f}%",
                    'APY (%)': '-',
                    'Start Value': '-',
                    'Current Value': '-'
                },
                {
                    'Period': 'Max Drawdown',
                    'Return (%)': f"{max_drawdown:.2f}%",
                    'APY (%)': '-',
                    'Start Value': f"${max_value:,.2f}",
                    'Current Value': f"${current_value:,.2f}"
                }
            ])
    
    return pd.DataFrame(metrics_data)


def create_wallet_performance_chart(wallet_timeline_df):
    """Create enhanced wallet performance chart"""
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

def historical_analysis_page():
    """Enhanced historical analysis page"""
    st.title("📈 Historical Portfolio Analysis")
    st.markdown("Comprehensive analysis of your portfolio performance over time")
    st.markdown("---")

    # Load historical data
    historical_df = load_historical_data()

    if historical_df is None:
        st.warning("⚠️ Historical data file not found. Please run the master portfolio tracker first.")
        st.info("Expected file location: `portfolio_data/ALL_PORTFOLIOS_HISTORY.csv`")

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

    # Data validation
    if len(historical_df) == 0:
        st.error("No data available for analysis.")
        return

    # Calculate timelines
    portfolio_timeline = calculate_portfolio_timeline(historical_df)
    wallet_timeline = calculate_wallet_timeline(historical_df)

    # Performance Overview
    st.header("📊 Performance Overview")

    if len(portfolio_timeline) >= 2:
        col1, col2, col3, col4 = st.columns(4)
        
        current_value = portfolio_timeline['usd_value_numeric'].iloc[-1]
        start_value = portfolio_timeline['usd_value_numeric'].iloc[0]
        total_return = ((current_value - start_value) / start_value * 100) if start_value > 0 else 0
        
        days_tracked = (portfolio_timeline['timestamp'].max() - portfolio_timeline['timestamp'].min()).days
        apy = calculate_apy(start_value, current_value, days_tracked) if days_tracked > 0 else 0
        
        with col1:
            st.metric(
                "Portfolio Value",
                f"${current_value:,.2f}",
                f"{total_return:+.2f}%"
            )
        
        with col2:
            st.metric(
                "APY",
                f"{apy:+.2f}%",
                f"{days_tracked} days"
            )
        
        with col3:
            max_value = portfolio_timeline['usd_value_numeric'].max()
            drawdown = ((current_value - max_value) / max_value * 100) if max_value > 0 else 0
            st.metric(
                "From ATH",
                f"${max_value:,.2f}",
                f"{drawdown:+.2f}%"
            )
        
        with col4:
            asset_count = historical_df[historical_df['timestamp'] == historical_df['timestamp'].max()]['coin'].nunique()
            protocol_count = historical_df[historical_df['timestamp'] == historical_df['timestamp'].max()]['protocol'].nunique()
            st.metric(
                "Assets/Protocols",
                f"{asset_count}",
                f"{protocol_count} protocols"
            )

        # Performance metrics table
        st.subheader("🎯 Detailed Performance Metrics")
        metrics_df = create_performance_metrics_table(portfolio_timeline)
        if metrics_df is not None:
            st.dataframe(metrics_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Charts Section
    st.header("📈 Portfolio Analysis")

    # Portfolio value chart
    if len(portfolio_timeline) >= 2:
        portfolio_fig = create_portfolio_value_chart(portfolio_timeline)
        st.plotly_chart(portfolio_fig, use_container_width=True)

    # Two-column layout for protocol and wallet analysis
    col1, col2 = st.columns(2)

    with col1:
        # Protocol allocation
        protocol_fig = create_protocol_allocation_chart(historical_df)
        st.plotly_chart(protocol_fig, use_container_width=True)

    with col2:
        # Wallet performance
        if len(wallet_timeline) >= 2:
            wallet_fig = create_wallet_performance_chart(wallet_timeline)
            st.plotly_chart(wallet_fig, use_container_width=True)

    st.markdown("---")

    # Summary Statistics
    st.markdown("---")
    st.header("📊 Summary Statistics")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Dataset Information")
        total_records = len(historical_df)
        unique_timestamps = historical_df['timestamp'].nunique()
        date_range_start = historical_df['timestamp'].min().strftime('%Y-%m-%d')
        date_range_end = historical_df['timestamp'].max().strftime('%Y-%m-%d')
        tracked_wallets = historical_df['wallet_label'].nunique()
        tracked_assets = historical_df['coin'].nunique()
        tracked_protocols = historical_df['protocol'].nunique()
        
        st.write(f"**Total Records:** {total_records:,}")
        st.write(f"**Unique Timestamps:** {unique_timestamps:,}")
        st.write(f"**Date Range:** {date_range_start} to {date_range_end}")
        st.write(f"**Tracked Wallets:** {tracked_wallets}")
        st.write(f"**Tracked Assets:** {tracked_assets}")
        st.write(f"**Tracked Protocols:** {tracked_protocols}")

    with col2:
        st.subheader("💰 Current Value Distribution")
        latest_data = historical_df[historical_df['timestamp'] == historical_df['timestamp'].max()]
        total_current_value = latest_data['usd_value_numeric'].sum()

        # Top wallets
        top_wallets = latest_data.groupby('wallet_label')['usd_value_numeric'].sum().sort_values(ascending=False)
        st.write("**Top Wallets:**")
        for wallet, value in top_wallets.head(5).items():
            percentage = (value / total_current_value * 100) if total_current_value > 0 else 0
            st.write(f"  {wallet}: ${value:,.2f} ({percentage:.1f}%)")

        # Top protocols
        st.write("**Top Protocols:**")
        top_protocols = latest_data.groupby('protocol')['usd_value_numeric'].sum().sort_values(ascending=False)
        for protocol, value in top_protocols.head(5).items():
            percentage = (value / total_current_value * 100) if total_current_value > 0 else 0
            st.write(f"  {protocol}: ${value:,.2f} ({percentage:.1f}%)")

if __name__ == "__main__":
    historical_analysis_page()
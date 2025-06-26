import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import timedelta
from utils import (
    load_historical_data, 
    load_and_process_data, 
    parse_timestamp,
    calculate_portfolio_timeline,
    calculate_token_timeline,
    get_performance_metrics,
    calculate_apy,
    calculate_volatility,
    calculate_max_drawdown
)


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
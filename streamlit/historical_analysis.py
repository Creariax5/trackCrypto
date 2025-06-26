import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from utils import (
    load_historical_data, 
    load_and_process_data, 
    parse_timestamp,
    calculate_portfolio_timeline,
    calculate_wallet_timeline,
    calculate_token_timeline,
    get_performance_metrics
)


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
            token_return = ((current_token_value - start_token_value) / start_token_value * 100) if start_token_value > 0 else 0

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
        st.write(f"**Date Range:** {historical_df['timestamp'].min().strftime('%Y-%m-%d')} to {historical_df['timestamp'].max().strftime('%Y-%m-%d')}")
        st.write(f"**Tracked Wallets:** {historical_df['wallet_label'].nunique()}")
        st.write(f"**Tracked Assets:** {historical_df['coin'].nunique()}")
        st.write(f"**Tracked Protocols:** {historical_df['protocol'].nunique()}")

    with col2:
        st.subheader("Value Distribution")
        total_current_value = historical_df[historical_df['timestamp'] == historical_df['timestamp'].max()]['usd_value_numeric'].sum()

        # Top wallets by current value
        latest_data = historical_df[historical_df['timestamp'] == historical_df['timestamp'].max()]
        top_wallets = latest_data.groupby('wallet_label')['usd_value_numeric'].sum().sort_values(ascending=False)

        st.write("**Top Wallets by Value:**")
        for wallet, value in top_wallets.head(5).items():
            percentage = (value / total_current_value * 100) if total_current_value > 0 else 0
            st.write(f"  {wallet}: ${value:,.2f} ({percentage:.1f}%)")
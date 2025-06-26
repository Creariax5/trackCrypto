"""
Crypto Portfolio Dashboard - Main Streamlit Application

A comprehensive dashboard for analyzing cryptocurrency portfolio data by date.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
import os

# Import custom components
from utils.data_processing import (
    load_historical_data,
    get_portfolio_for_date,
    get_available_dates,
    calculate_portfolio_summary,
    get_top_holdings,
    get_wallet_breakdown,
    get_blockchain_breakdown,
    get_protocol_breakdown
)

from components.metrics import (
    display_overview_metrics,
    create_summary_cards,
    calculate_concentration_metrics,
    display_concentration_metrics,
    display_risk_assessment
)

from components.charts import (
    create_wallet_pie_chart,
    create_blockchain_bar_chart,
    create_top_holdings_chart,
    create_protocol_treemap,
    create_wallet_comparison_chart,
    create_value_distribution_donut
)

from components.tables import (
    create_detailed_holdings_table,
    create_wallet_summary_table,
    create_blockchain_summary_table,
    create_token_summary_table,
    create_export_section
)

# Page configuration
st.set_page_config(
    page_title="Crypto Portfolio Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)


def load_custom_css():
    """Load custom CSS for better styling."""
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }

    .sidebar-info {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)


def main():
    """Main application function."""
    load_custom_css()

    # Title
    st.markdown('<h1 class="main-header">💰 Crypto Portfolio Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("---")

    # Load historical data
    with st.spinner("Loading portfolio data..."):
        historical_df = load_historical_data()

    if historical_df is None:
        st.error("❌ Could not load historical data. Please ensure the file `../portfolio_data/ALL_PORTFOLIOS_HISTORY.csv` exists.")
        st.info("""
        **Expected file location:** `./portfolio_data/ALL_PORTFOLIOS_HISTORY.csv`

        Please make sure:
        1. The file exists in the correct location
        2. The file contains the required columns
        3. The file is not corrupted or empty
        """)
        return

    # Sidebar controls
    st.sidebar.header("📅 Date Selection")

    available_dates = get_available_dates(historical_df)

    if not available_dates:
        st.error("❌ No valid dates found in the historical data.")
        return

    # Date selector
    selected_date = st.sidebar.selectbox(
        "Select a date to analyze:",
        options=available_dates,
        format_func=lambda x: x.strftime("%Y-%m-%d"),
        help="Choose a date to view your portfolio snapshot"
    )

    # Info about selected date
    st.sidebar.markdown(f"""
    <div class="sidebar-info">
    <h4>📊 Selected Date</h4>
    <p><strong>{selected_date.strftime("%B %d, %Y")}</strong></p>
    <p>Showing the latest data from this date</p>
    </div>
    """, unsafe_allow_html=True)

    # Load portfolio data for selected date
    portfolio_df = get_portfolio_for_date(historical_df, selected_date)

    if len(portfolio_df) == 0:
        st.warning(f"⚠️ No portfolio data found for {selected_date.strftime('%Y-%m-%d')}")
        st.info("Please select a different date from the sidebar.")
        return

    # Calculate summary metrics
    summary = calculate_portfolio_summary(portfolio_df)

    # Display success message
    timestamp = portfolio_df['timestamp'].iloc[0]
    st.success(
        f"✅ Loaded portfolio data from {timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({len(portfolio_df)} positions)")

    # Overview metrics
    st.header("📊 Portfolio Overview")
    display_overview_metrics(summary)

    # Summary cards
    create_summary_cards(portfolio_df)

    st.markdown("---")

    # Charts section
    st.header("📈 Portfolio Analysis")

    # Get data for charts
    wallet_data = get_wallet_breakdown(portfolio_df)
    blockchain_data = get_blockchain_breakdown(portfolio_df)
    holdings_data = get_top_holdings(portfolio_df, top_n=10)
    protocol_data = get_protocol_breakdown(portfolio_df)

    # First row of charts
    col1, col2 = st.columns(2)

    with col1:
        if len(wallet_data) > 0:
            wallet_fig = create_wallet_pie_chart(wallet_data)
            st.plotly_chart(wallet_fig, use_container_width=True)

    with col2:
        if len(blockchain_data) > 0:
            blockchain_fig = create_blockchain_bar_chart(blockchain_data)
            st.plotly_chart(blockchain_fig, use_container_width=True)

    # Second row of charts
    col1, col2 = st.columns(2)

    with col1:
        if len(holdings_data) > 0:
            holdings_fig = create_top_holdings_chart(holdings_data)
            st.plotly_chart(holdings_fig, use_container_width=True)

    with col2:
        if len(protocol_data) > 0:
            protocol_fig = create_protocol_treemap(protocol_data)
            st.plotly_chart(protocol_fig, use_container_width=True)

    # Wallet comparison chart
    if len(portfolio_df) > 0:
        st.subheader("🔍 Wallet Token Distribution")
        wallet_comparison_fig = create_wallet_comparison_chart(portfolio_df)
        st.plotly_chart(wallet_comparison_fig, use_container_width=True)

    st.markdown("---")

    # Risk and concentration analysis
    st.header("⚖️ Risk Analysis")
    concentration_metrics = calculate_concentration_metrics(portfolio_df)

    col1, col2 = st.columns([2, 1])

    with col1:
        display_concentration_metrics(concentration_metrics)

    with col2:
        display_risk_assessment(concentration_metrics)

    st.markdown("---")

    # Tables section
    st.header("📋 Detailed Analysis")

    # Create tabs for different table views
    tab1, tab2, tab3, tab4 = st.tabs(["💎 All Holdings", "👛 Wallets", "⛓️ Blockchains", "🪙 Tokens"])

    with tab1:
        create_detailed_holdings_table(portfolio_df)

    with tab2:
        create_wallet_summary_table(portfolio_df)

    with tab3:
        create_blockchain_summary_table(portfolio_df)

    with tab4:
        create_token_summary_table(portfolio_df)

    st.markdown("---")

    # Export section
    create_export_section(portfolio_df, selected_date.strftime("%Y-%m-%d"))

    # Sidebar additional info
    st.sidebar.markdown("---")
    st.sidebar.header("📈 Quick Stats")

    if summary:
        st.sidebar.metric(
            "💰 Total Value",
            f"${summary['total_value']:,.2f}"
        )

        st.sidebar.metric(
            "👛 Wallets",
            f"{summary['total_wallets']}"
        )

        st.sidebar.metric(
            "🪙 Tokens",
            f"{summary['total_tokens']}"
        )

        st.sidebar.metric(
            "⛓️ Blockchains",
            f"{summary['total_blockchains']}"
        )

    # Data info
    st.sidebar.markdown("---")
    st.sidebar.header("ℹ️ Data Information")
    st.sidebar.info(f"""
    **Data Source:** ALL_PORTFOLIOS_HISTORY.csv

    **Available Dates:** {len(available_dates)}

    **Date Range:** 
    {min(available_dates).strftime('%Y-%m-%d')} to 
    {max(available_dates).strftime('%Y-%m-%d')}

    **Current Selection:** {selected_date.strftime('%Y-%m-%d')}
    """)


if __name__ == "__main__":
    main()
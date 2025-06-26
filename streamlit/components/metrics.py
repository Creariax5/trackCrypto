"""
Metrics calculation and display components for the crypto portfolio dashboard.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any


def display_overview_metrics(summary: Dict[str, Any]) -> None:
    """Display overview metrics in a 4-column layout."""
    if not summary:
        st.warning("No data available for metrics calculation.")
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="💰 Total Portfolio Value",
            value=f"${summary.get('total_value', 0):,.2f}"
        )

    with col2:
        st.metric(
            label="👛 Number of Wallets",
            value=f"{summary.get('total_wallets', 0)}"
        )

    with col3:
        st.metric(
            label="🪙 Unique Tokens",
            value=f"{summary.get('total_tokens', 0)}"
        )

    with col4:
        st.metric(
            label="🔗 Blockchains",
            value=f"{summary.get('total_blockchains', 0)}"
        )


def display_top_performers(df: pd.DataFrame, metric_name: str = "Top Holdings") -> None:
    """Display top performing assets or categories."""
    if len(df) == 0:
        return

    st.subheader(f"🏆 {metric_name}")

    for idx, row in df.head(5).iterrows():
        if 'coin' in row:
            label = f"{row.get('coin', 'Unknown')} ({row.get('token_name', 'Unknown')})"
        elif 'wallet_label' in row:
            label = row.get('wallet_label', 'Unknown')
        elif 'blockchain' in row:
            label = row.get('blockchain', 'Unknown')
        elif 'protocol' in row:
            label = row.get('protocol', 'Unknown')
        else:
            label = str(row.iloc[0])

        value = row.get('usd_value_numeric', 0)
        st.metric(
            label=label,
            value=f"${value:,.2f}"
        )


def create_summary_cards(df: pd.DataFrame) -> None:
    """Create summary information cards."""
    if len(df) == 0:
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(f"""
        **💎 Largest Single Holding**

        {df.loc[df['usd_value_numeric'].idxmax(), 'coin']} 

        ${df['usd_value_numeric'].max():,.2f}
        """)

    with col2:
        wallet_counts = df.groupby('wallet_label')['coin'].nunique()
        most_diverse_wallet = wallet_counts.idxmax()
        st.info(f"""
        **🌟 Most Diverse Wallet**

        {most_diverse_wallet}

        {wallet_counts.max()} different tokens
        """)

    with col3:
        blockchain_counts = df['blockchain'].value_counts()
        dominant_blockchain = blockchain_counts.index[0]
        blockchain_percentage = (blockchain_counts.iloc[0] / len(df)) * 100
        st.info(f"""
        **⛓️ Dominant Blockchain**

        {dominant_blockchain}

        {blockchain_percentage:.1f}% of positions
        """)


def calculate_concentration_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """Calculate portfolio concentration metrics."""
    if len(df) == 0:
        return {}

    total_value = df['usd_value_numeric'].sum()

    # Top holdings concentration
    holdings = df.groupby('coin')['usd_value_numeric'].sum().sort_values(ascending=False)
    top_5_concentration = holdings.head(5).sum() / total_value * 100
    top_10_concentration = holdings.head(10).sum() / total_value * 100

    # Wallet concentration
    wallet_values = df.groupby('wallet_label')['usd_value_numeric'].sum().sort_values(ascending=False)
    largest_wallet_concentration = wallet_values.iloc[0] / total_value * 100

    # Blockchain concentration
    blockchain_values = df.groupby('blockchain')['usd_value_numeric'].sum().sort_values(ascending=False)
    largest_blockchain_concentration = blockchain_values.iloc[0] / total_value * 100

    return {
        'top_5_holdings': top_5_concentration,
        'top_10_holdings': top_10_concentration,
        'largest_wallet': largest_wallet_concentration,
        'largest_blockchain': largest_blockchain_concentration
    }


def display_concentration_metrics(concentration: Dict[str, float]) -> None:
    """Display portfolio concentration metrics."""
    if not concentration:
        return

    st.subheader("📊 Portfolio Concentration Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Top 5 Holdings Concentration",
            f"{concentration.get('top_5_holdings', 0):.1f}%"
        )
        st.metric(
            "Top 10 Holdings Concentration",
            f"{concentration.get('top_10_holdings', 0):.1f}%"
        )

    with col2:
        st.metric(
            "Largest Wallet Concentration",
            f"{concentration.get('largest_wallet', 0):.1f}%"
        )
        st.metric(
            "Largest Blockchain Concentration",
            f"{concentration.get('largest_blockchain', 0):.1f}%"
        )


def display_risk_assessment(concentration: Dict[str, float]) -> None:
    """Display basic risk assessment based on concentration."""
    if not concentration:
        return

    st.subheader("⚠️ Risk Assessment")

    risk_level = "Low"
    risk_color = "green"

    top_5_conc = concentration.get('top_5_holdings', 0)
    wallet_conc = concentration.get('largest_wallet', 0)

    if top_5_conc > 80 or wallet_conc > 90:
        risk_level = "High"
        risk_color = "red"
    elif top_5_conc > 60 or wallet_conc > 70:
        risk_level = "Medium"
        risk_color = "orange"

    st.markdown(f"""
    <div style="padding: 1rem; border-radius: 0.5rem; background-color: {risk_color}20; border-left: 4px solid {risk_color};">
        <h4 style="color: {risk_color}; margin: 0;">Concentration Risk: {risk_level}</h4>
        <p style="margin: 0.5rem 0 0 0;">
            {'Consider diversifying your holdings to reduce concentration risk.' if risk_level != 'Low' else 'Your portfolio shows good diversification.'}
        </p>
    </div>
    """, unsafe_allow_html=True)
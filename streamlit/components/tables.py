"""
Table display components for the crypto portfolio dashboard.
"""

import streamlit as st
import pandas as pd
from typing import List, Optional


def create_detailed_holdings_table(df: pd.DataFrame) -> None:
    """Create detailed holdings table with filters."""
    if len(df) == 0:
        st.warning("No data available for the detailed table.")
        return

    st.subheader("📋 Detailed Holdings")

    # Create filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        wallet_filter = st.selectbox(
            "Filter by Wallet",
            options=['All'] + sorted(df['wallet_label'].unique().tolist()),
            key="wallet_filter"
        )

    with col2:
        blockchain_filter = st.selectbox(
            "Filter by Blockchain",
            options=['All'] + sorted(df['blockchain'].unique().tolist()),
            key="blockchain_filter"
        )

    with col3:
        protocol_filter = st.selectbox(
            "Filter by Protocol",
            options=['All'] + sorted(df['protocol'].unique().tolist()),
            key="protocol_filter"
        )

    with col4:
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

    if protocol_filter != 'All':
        filtered_df = filtered_df[filtered_df['protocol'] == protocol_filter]

    filtered_df = filtered_df[filtered_df['usd_value_numeric'] >= min_value]

    # Sort by USD value descending
    filtered_df = filtered_df.sort_values('usd_value_numeric', ascending=False)

    # Display columns
    display_columns = [
        'wallet_label', 'blockchain', 'coin', 'token_name',
        'protocol', 'amount', 'price', 'usd_value'
    ]

    # Create a formatted dataframe for display
    display_df = filtered_df[display_columns].copy()

    # Format columns for better display
    display_df.columns = [
        'Wallet', 'Blockchain', 'Symbol', 'Token Name',
        'Protocol', 'Amount', 'Price', 'USD Value'
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Amount": st.column_config.NumberColumn(
                "Amount",
                help="Token amount",
                format="%.6f"
            ),
            "Price": st.column_config.TextColumn(
                "Price",
                help="Current token price"
            ),
            "USD Value": st.column_config.TextColumn(
                "USD Value",
                help="Total USD value of holding"
            )
        }
    )

    # Show summary
    total_filtered_value = filtered_df['usd_value_numeric'].sum()
    total_original_value = df['usd_value_numeric'].sum()
    percentage_shown = (total_filtered_value / total_original_value * 100) if total_original_value > 0 else 0

    st.info(
        f"Showing **{len(filtered_df)}** positions with total value: **${total_filtered_value:,.2f}** "
        f"({percentage_shown:.1f}% of total portfolio)"
    )


def create_wallet_summary_table(df: pd.DataFrame) -> None:
    """Create wallet summary table."""
    if len(df) == 0:
        return

    st.subheader("👛 Wallet Summary")

    wallet_summary = df.groupby('wallet_label').agg({
        'usd_value_numeric': 'sum',
        'coin': 'nunique',
        'protocol': 'nunique',
        'blockchain': 'nunique'
    }).reset_index()

    wallet_summary.columns = ['Wallet', 'Total Value', 'Unique Tokens', 'Protocols', 'Blockchains']
    wallet_summary = wallet_summary.sort_values('Total Value', ascending=False)

    # Calculate percentages
    total_portfolio_value = wallet_summary['Total Value'].sum()
    wallet_summary['Percentage'] = (wallet_summary['Total Value'] / total_portfolio_value * 100).round(2)

    st.dataframe(
        wallet_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Total Value": st.column_config.NumberColumn(
                "Total Value",
                help="Total USD value in wallet",
                format="$%.2f"
            ),
            "Percentage": st.column_config.NumberColumn(
                "Percentage",
                help="Percentage of total portfolio",
                format="%.2f%%"
            )
        }
    )


def create_blockchain_summary_table(df: pd.DataFrame) -> None:
    """Create blockchain summary table."""
    if len(df) == 0:
        return

    st.subheader("⛓️ Blockchain Summary")

    blockchain_summary = df.groupby('blockchain').agg({
        'usd_value_numeric': 'sum',
        'coin': 'nunique',
        'wallet_label': 'nunique',
        'protocol': 'nunique'
    }).reset_index()

    blockchain_summary.columns = ['Blockchain', 'Total Value', 'Unique Tokens', 'Wallets', 'Protocols']
    blockchain_summary = blockchain_summary.sort_values('Total Value', ascending=False)

    # Calculate percentages
    total_portfolio_value = blockchain_summary['Total Value'].sum()
    blockchain_summary['Percentage'] = (blockchain_summary['Total Value'] / total_portfolio_value * 100).round(2)

    st.dataframe(
        blockchain_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Total Value": st.column_config.NumberColumn(
                "Total Value",
                help="Total USD value on blockchain",
                format="$%.2f"
            ),
            "Percentage": st.column_config.NumberColumn(
                "Percentage",
                help="Percentage of total portfolio",
                format="%.2f%%"
            )
        }
    )


def create_token_summary_table(df: pd.DataFrame, top_n: int = 20) -> None:
    """Create token summary table."""
    if len(df) == 0:
        return

    st.subheader(f"🪙 Top {top_n} Tokens by Value")

    token_summary = df.groupby(['coin', 'token_name']).agg({
        'usd_value_numeric': 'sum',
        'amount_numeric': 'sum',
        'price_numeric': 'mean',
        'wallet_label': 'nunique',
        'blockchain': 'nunique'
    }).reset_index()

    token_summary.columns = ['Symbol', 'Token Name', 'Total Value', 'Total Amount', 'Avg Price', 'Wallets',
                             'Blockchains']
    token_summary = token_summary.sort_values('Total Value', ascending=False).head(top_n)

    # Calculate percentages
    total_portfolio_value = df['usd_value_numeric'].sum()
    token_summary['Percentage'] = (token_summary['Total Value'] / total_portfolio_value * 100).round(2)

    st.dataframe(
        token_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Total Value": st.column_config.NumberColumn(
                "Total Value",
                help="Total USD value of token",
                format="$%.2f"
            ),
            "Total Amount": st.column_config.NumberColumn(
                "Total Amount",
                help="Total token amount across all wallets",
                format="%.6f"
            ),
            "Avg Price": st.column_config.NumberColumn(
                "Avg Price",
                help="Average token price",
                format="$%.6f"
            ),
            "Percentage": st.column_config.NumberColumn(
                "Percentage",
                help="Percentage of total portfolio",
                format="%.2f%%"
            )
        }
    )


def create_export_section(df: pd.DataFrame, selected_date: str) -> None:
    """Create data export section."""
    if len(df) == 0:
        return

    st.subheader("📤 Export Data")

    col1, col2 = st.columns(2)

    with col1:
        # Export full data
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="📄 Download Full Portfolio Data (CSV)",
            data=csv_data,
            file_name=f"portfolio_data_{selected_date}.csv",
            mime="text/csv"
        )

    with col2:
        # Export summary data
        summary_data = df.groupby(['coin', 'token_name']).agg({
            'usd_value_numeric': 'sum',
            'amount_numeric': 'sum'
        }).reset_index()
        summary_csv = summary_data.to_csv(index=False)

        st.download_button(
            label="📊 Download Summary Data (CSV)",
            data=summary_csv,
            file_name=f"portfolio_summary_{selected_date}.csv",
            mime="text/csv"
        )
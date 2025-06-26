"""
Data processing utilities for the crypto portfolio dashboard.
"""

import pandas as pd
import re
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple


def parse_currency(value) -> float:
    """Parse currency string to float."""
    if pd.isna(value) or value == "None":
        return 0.0
    cleaned = re.sub(r'[$,]', '', str(value))
    try:
        return float(cleaned)
    except:
        return 0.0


def parse_amount(value) -> float:
    """Parse amount string to float."""
    if pd.isna(value) or value == "None":
        return 0.0
    try:
        return float(value)
    except:
        return 0.0


def parse_timestamp(timestamp_str) -> pd.Timestamp:
    """Parse timestamp from filename format."""
    try:
        timestamp_str = timestamp_str.replace('.csv', '')
        return pd.to_datetime(timestamp_str, format='%d-%m-%Y_%H-%M-%S')
    except:
        try:
            return pd.to_datetime(timestamp_str)
        except:
            return pd.NaT


def load_historical_data(file_path: str = "../portfolio_data/ALL_PORTFOLIOS_HISTORY.csv") -> Optional[pd.DataFrame]:
    """Load and process historical portfolio data."""
    try:
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

        # Extract date for filtering
        df['date'] = df['timestamp'].dt.date

        # Filter out zero value positions
        df = df[df['usd_value_numeric'] > 0]

        return df.sort_values('timestamp')

    except Exception as e:
        print(f"Error loading historical data: {e}")
        return None


def get_portfolio_for_date(df: pd.DataFrame, selected_date: datetime.date) -> pd.DataFrame:
    """Get portfolio data for a specific date, taking the latest timestamp if multiple exist."""
    if df is None:
        return pd.DataFrame()

    # Filter by selected date
    date_data = df[df['date'] == selected_date]

    if len(date_data) == 0:
        return pd.DataFrame()

    # Get the latest timestamp for the selected date
    latest_timestamp = date_data['timestamp'].max()
    return date_data[date_data['timestamp'] == latest_timestamp]


def get_available_dates(df: pd.DataFrame) -> list:
    """Get list of available dates from the dataset."""
    if df is None or len(df) == 0:
        return []

    return sorted(df['date'].unique(), reverse=True)


def calculate_portfolio_summary(df: pd.DataFrame) -> dict:
    """Calculate basic portfolio summary statistics."""
    if len(df) == 0:
        return {}

    return {
        'total_value': df['usd_value_numeric'].sum(),
        'total_wallets': df['wallet_label'].nunique(),
        'total_tokens': df['coin'].nunique(),
        'total_protocols': df['protocol'].nunique(),
        'total_blockchains': df['blockchain'].nunique()
    }


def get_top_holdings(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Get top N holdings by value."""
    if len(df) == 0:
        return pd.DataFrame()

    holdings = df.groupby(['coin', 'token_name']).agg({
        'usd_value_numeric': 'sum',
        'amount_numeric': 'sum',
        'price_numeric': 'mean'
    }).reset_index()

    return holdings.sort_values('usd_value_numeric', ascending=False).head(top_n)


def get_wallet_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Get wallet breakdown by total value."""
    if len(df) == 0:
        return pd.DataFrame()

    return df.groupby('wallet_label').agg({
        'usd_value_numeric': 'sum'
    }).reset_index().sort_values('usd_value_numeric', ascending=False)


def get_blockchain_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Get blockchain breakdown by total value."""
    if len(df) == 0:
        return pd.DataFrame()

    return df.groupby('blockchain').agg({
        'usd_value_numeric': 'sum'
    }).reset_index().sort_values('usd_value_numeric', ascending=False)


def get_protocol_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Get protocol breakdown by total value."""
    if len(df) == 0:
        return pd.DataFrame()

    return df.groupby('protocol').agg({
        'usd_value_numeric': 'sum'
    }).reset_index().sort_values('usd_value_numeric', ascending=False)
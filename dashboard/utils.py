import pandas as pd
import numpy as np
import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import streamlit as st

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

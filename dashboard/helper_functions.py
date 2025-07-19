import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, date
import sys
import os

# Add project root for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.ui_components import StandardComponents, StandardPageTemplate
from core.config_manager import ConfigManager


def apply_asset_combinations(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Apply asset combinations from config"""
    df_processed = df.copy()
    combinations = config.get('asset_combinations', {})
    renames = config.get('asset_renames', {})
    
    df_processed['combined_asset'] = df_processed['coin']
    
    # Apply combinations
    for combined_name, items_to_combine in combinations.items():
        for item in items_to_combine:
            df_processed.loc[df_processed['coin'] == item, 'combined_asset'] = combined_name
    
    # Apply renames
    for original_name, new_name in renames.items():
        df_processed.loc[df_processed['coin'] == original_name, 'combined_asset'] = new_name
    
    return df_processed

def create_wallet_breakdown_chart(df: pd.DataFrame, min_wallet_value: float = 0):
    """Create wallet breakdown pie chart"""
    wallet_totals = df.groupby('wallet_label')['usd_value_numeric'].sum().reset_index()
    wallet_totals = wallet_totals[wallet_totals['usd_value_numeric'] >= min_wallet_value]
    wallet_totals = wallet_totals.sort_values('usd_value_numeric', ascending=False)
    
    if len(wallet_totals) == 0:
        return None
    
    fig = px.pie(
        wallet_totals,
        values='usd_value_numeric',
        names='wallet_label',
        title=f"Portfolio Distribution by Wallet (Min: ${min_wallet_value:,.0f})"
    )
    return fig

def create_blockchain_breakdown_chart(df: pd.DataFrame):
    """Create blockchain breakdown chart"""
    blockchain_totals = df.groupby('blockchain')['usd_value_numeric'].sum().reset_index()
    blockchain_totals = blockchain_totals.sort_values('usd_value_numeric', ascending=False)
    
    fig = px.bar(
        blockchain_totals,
        x='blockchain',
        y='usd_value_numeric',
        title="Asset Distribution by Blockchain"
    )
    return fig

def create_top_holdings_chart(df: pd.DataFrame, config: dict = None, top_n: int = 10):
    """Create top holdings chart"""
    if config and 'combined_asset' in df.columns:
        token_totals = df.groupby('combined_asset')['usd_value_numeric'].sum().reset_index()
        token_totals = token_totals.sort_values('usd_value_numeric', ascending=False).head(top_n)
        x_col = 'combined_asset'
        title_suffix = " (Grouped by Config)"
    else:
        token_totals = df.groupby('coin')['usd_value_numeric'].sum().reset_index()
        token_totals = token_totals.sort_values('usd_value_numeric', ascending=False).head(top_n)
        x_col = 'coin'
        title_suffix = ""
    
    fig = px.bar(
        token_totals,
        x='usd_value_numeric',
        y=x_col,
        orientation='h',
        title=f"Top {top_n} Token Holdings{title_suffix}"
    )
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    return fig

def create_protocol_breakdown_chart(df: pd.DataFrame):
    """Create protocol breakdown chart"""
    protocol_totals = df.groupby('protocol')['usd_value_numeric'].sum().reset_index()
    protocol_totals = protocol_totals.sort_values('usd_value_numeric', ascending=False).head(15)
    
    fig = px.treemap(
        protocol_totals,
        path=['protocol'],
        values='usd_value_numeric',
        title="Asset Distribution by Protocol"
    )
    return fig

def get_top_items_by_value(df: pd.DataFrame, analysis_type: str, top_n: int = 10) -> list:
    """Get top items by current value"""
    if analysis_type == "assets":
        if 'combined_asset' in df.columns:
            return df.groupby('combined_asset')['usd_value_numeric'].sum().nlargest(top_n).index.tolist()
        else:
            return df.groupby('coin')['usd_value_numeric'].sum().nlargest(top_n).index.tolist()
    else:
        # Protocol positions
        df_no_wallet = df[df['protocol'] != 'Wallet'].copy()
        df_no_wallet['protocol_asset'] = df_no_wallet['coin'] + " | " + df_no_wallet['protocol']
        return df_no_wallet.groupby('protocol_asset')['usd_value_numeric'].sum().nlargest(top_n).index.tolist()

def get_top_performing_items(df: pd.DataFrame, analysis_type: str, period_days: int, top_n: int = 10) -> list:
    """Get top performing items (placeholder implementation)"""
    # This would require historical performance calculation
    return get_top_items_by_value(df, analysis_type, top_n)

def get_available_items(df: pd.DataFrame, analysis_type: str) -> list:
    """Get all available items for selection"""
    if analysis_type == "assets":
        if 'combined_asset' in df.columns:
            return sorted(df['combined_asset'].dropna().unique())
        else:
            return sorted(df['coin'].dropna().unique())
    else:
        df_no_wallet = df[df['protocol'] != 'Wallet'].copy()
        df_no_wallet['protocol_asset'] = df_no_wallet['coin'] + " | " + df_no_wallet['protocol']
        return sorted(df_no_wallet['protocol_asset'].dropna().unique())

def create_performance_comparison_chart(df: pd.DataFrame, selected_items: list, period_days: int, analysis_type: str):
    """Create performance comparison chart (placeholder)"""
    # This would require historical data analysis
    # For now, return a simple placeholder
    import numpy as np
    
    # Generate sample performance data
    dates = pd.date_range(end=pd.Timestamp.now(), periods=period_days, freq='D')
    
    fig = go.Figure()
    
    for item in selected_items[:5]:  # Limit to 5 items for clarity
        # Generate sample cumulative return data
        returns = np.random.normal(0.001, 0.05, period_days)
        cumulative_returns = np.cumsum(returns) * 100
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=cumulative_returns,
            mode='lines',
            name=item,
            hovertemplate=f'{item}<br>Date: %{{x}}<br>Return: %{{y:.2f}}%<extra></extra>'
        ))
    
    fig.update_layout(
        title=f"Performance Comparison ({period_days} Days)",
        xaxis_title="Date",
        yaxis_title="Cumulative Return (%)",
        hovermode='x unified'
    )
    
    return fig

def calculate_performance_metrics(df: pd.DataFrame, selected_items: list, period_days: int, analysis_type: str):
    """Calculate performance metrics (placeholder)"""
    # This would require historical data analysis
    # For now, return sample metrics
    
    metrics_data = []
    for item in selected_items:
        # Sample metrics calculation
        item_data = df[df['coin'] == item] if analysis_type == "assets" else df
        current_value = item_data['usd_value_numeric'].sum()
        
        metrics_data.append({
            'Item': item,
            'Current Value ($)': f"${current_value:,.2f}",
            f'{period_days}d Return (%)': f"{np.random.uniform(-20, 30):+.2f}%",
            'APR (%)': f"{np.random.uniform(-50, 100):+.2f}%"
        })
    
    return pd.DataFrame(metrics_data)

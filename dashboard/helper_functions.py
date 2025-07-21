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
    """Create wallet breakdown pie chart with REAL data"""
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
    
    # Add hover info
    fig.update_traces(
        hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<br>Share: %{percent}<extra></extra>'
    )
    
    return fig

def create_blockchain_breakdown_chart(df: pd.DataFrame):
    """Create blockchain breakdown chart with REAL data"""
    blockchain_totals = df.groupby('blockchain')['usd_value_numeric'].sum().reset_index()
    blockchain_totals = blockchain_totals.sort_values('usd_value_numeric', ascending=False)
    
    fig = px.bar(
        blockchain_totals,
        x='blockchain',
        y='usd_value_numeric',
        title="Asset Distribution by Blockchain",
        labels={'usd_value_numeric': 'USD Value ($)', 'blockchain': 'Blockchain'}
    )
    
    # Add value labels on bars
    fig.update_traces(
        texttemplate='$%{y:,.0f}',
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Value: $%{y:,.2f}<extra></extra>'
    )
    
    return fig

def create_top_holdings_chart(df: pd.DataFrame, config: dict = None, top_n: int = 10):
    """Create top holdings chart with REAL data"""
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
        title=f"Top {top_n} Token Holdings{title_suffix}",
        labels={'usd_value_numeric': 'USD Value ($)', x_col: 'Token'}
    )
    
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    
    # Add value labels
    fig.update_traces(
        texttemplate='$%{x:,.0f}',
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Value: $%{x:,.2f}<extra></extra>'
    )
    
    return fig

def create_protocol_breakdown_chart(df: pd.DataFrame):
    """Create protocol breakdown chart with REAL data"""
    protocol_totals = df.groupby('protocol')['usd_value_numeric'].sum().reset_index()
    protocol_totals = protocol_totals.sort_values('usd_value_numeric', ascending=False).head(15)
    
    fig = px.treemap(
        protocol_totals,
        path=['protocol'],
        values='usd_value_numeric',
        title="Asset Distribution by Protocol",
        hover_data=['usd_value_numeric']
    )
    
    # Custom hover template
    fig.update_traces(
        hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<extra></extra>'
    )
    
    return fig

def get_top_items_by_value(df: pd.DataFrame, analysis_type: str, top_n: int = 10) -> list:
    """Get top items by current value - REAL DATA"""
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
    """Get top performing items based on REAL historical performance or fallback to value"""
    # This requires historical analysis - for now, fallback to current value
    # In a full implementation, this would analyze price changes over time
    return get_top_items_by_value(df, analysis_type, top_n)

def get_available_items(df: pd.DataFrame, analysis_type: str) -> list:
    """Get all available items for selection - REAL DATA"""
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
    """Create performance comparison chart with REAL DATA"""
    
    # Check if we have historical data (multiple timestamps)
    if 'timestamp' not in df.columns:
        st.info("📊 No timestamp data available. Showing current value comparison instead.")
        return create_current_value_comparison(df, selected_items, analysis_type)
    
    # Convert timestamp if needed
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    unique_timestamps = df['timestamp'].nunique()
    
    if unique_timestamps < 2:
        st.info("📊 Limited historical data. Showing current value comparison instead.")
        return create_current_value_comparison(df, selected_items, analysis_type)
    
    # Calculate historical performance
    fig = go.Figure()
    
    for item in selected_items[:10]:  # Limit to 10 for readability
        if analysis_type == "assets":
            if 'combined_asset' in df.columns:
                item_data = df[df['combined_asset'] == item]
            else:
                item_data = df[df['coin'] == item]
        else:
            # Protocol positions
            parts = item.split(' | ')
            if len(parts) == 2:
                coin, protocol = parts
                item_data = df[(df['coin'] == coin) & (df['protocol'] == protocol)]
            else:
                continue
        
        if len(item_data) == 0:
            continue
        
        # Group by timestamp and calculate cumulative performance
        timeline = item_data.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
        timeline = timeline.sort_values('timestamp')
        
        if len(timeline) >= 2:
            # Calculate cumulative returns
            baseline = timeline['usd_value_numeric'].iloc[0]
            timeline['cumulative_return'] = ((timeline['usd_value_numeric'] / baseline) - 1) * 100
            
            fig.add_trace(go.Scatter(
                x=timeline['timestamp'],
                y=timeline['cumulative_return'],
                mode='lines+markers',
                name=item,
                hovertemplate=f'{item}<br>Date: %{{x}}<br>Return: %{{y:.2f}}%<br>Value: $%{{customdata:,.2f}}<extra></extra>',
                customdata=timeline['usd_value_numeric']
            ))
    
    fig.update_layout(
        title=f"Performance Comparison - Historical Data",
        xaxis_title="Date",
        yaxis_title="Cumulative Return (%)",
        hovermode='x unified',
        showlegend=True
    )
    
    return fig

def create_current_value_comparison(df: pd.DataFrame, selected_items: list, analysis_type: str):
    """Create current value comparison chart - REAL DATA"""
    
    values_data = []
    
    for item in selected_items:
        if analysis_type == "assets":
            if 'combined_asset' in df.columns:
                current_value = df[df['combined_asset'] == item]['usd_value_numeric'].sum()
            else:
                current_value = df[df['coin'] == item]['usd_value_numeric'].sum()
        else:
            # Protocol positions
            parts = item.split(' | ')
            if len(parts) == 2:
                coin, protocol = parts
                current_value = df[(df['coin'] == coin) & (df['protocol'] == protocol)]['usd_value_numeric'].sum()
            else:
                current_value = 0
        
        values_data.append({
            'Item': item,
            'Value': current_value
        })
    
    values_df = pd.DataFrame(values_data)
    values_df = values_df.sort_values('Value', ascending=True)
    
    fig = px.bar(
        values_df,
        x='Value',
        y='Item',
        orientation='h',
        title=f"Current Portfolio Value Comparison",
        labels={'Value': 'USD Value ($)', 'Item': analysis_type.replace('_', ' ').title()}
    )
    
    # Add value labels
    fig.update_traces(
        texttemplate='$%{x:,.0f}',
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Value: $%{x:,.2f}<extra></extra>'
    )
    
    return fig

def calculate_performance_metrics(df: pd.DataFrame, selected_items: list, period_days: int, analysis_type: str):
    """Calculate performance metrics with REAL DATA"""
    
    metrics_data = []
    
    for item in selected_items:
        # Get current value
        if analysis_type == "assets":
            if 'combined_asset' in df.columns:
                current_value = df[df['combined_asset'] == item]['usd_value_numeric'].sum()
                item_data = df[df['combined_asset'] == item]
            else:
                current_value = df[df['coin'] == item]['usd_value_numeric'].sum()
                item_data = df[df['coin'] == item]
        else:
            # Protocol positions
            parts = item.split(' | ')
            if len(parts) == 2:
                coin, protocol = parts
                current_value = df[(df['coin'] == coin) & (df['protocol'] == protocol)]['usd_value_numeric'].sum()
                item_data = df[(df['coin'] == coin) & (df['protocol'] == protocol)]
            else:
                current_value = 0
                item_data = pd.DataFrame()
        
        # Calculate additional metrics if historical data available
        if 'timestamp' in df.columns and len(item_data) > 1:
            # Convert timestamp
            item_data = item_data.copy()
            item_data['timestamp'] = pd.to_datetime(item_data['timestamp'])
            
            # Check for historical data
            timeline = item_data.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
            timeline = timeline.sort_values('timestamp')
            
            if len(timeline) >= 2:
                start_value = timeline['usd_value_numeric'].iloc[0]
                end_value = timeline['usd_value_numeric'].iloc[-1]
                
                # Calculate return
                if start_value > 0:
                    total_return = ((end_value / start_value) - 1) * 100
                    
                    # Simple APR calculation
                    actual_days = (timeline['timestamp'].iloc[-1] - timeline['timestamp'].iloc[0]).days
                    if actual_days > 0:
                        apr = ((end_value / start_value) ** (365 / actual_days) - 1) * 100
                    else:
                        apr = 0
                else:
                    total_return = 0
                    apr = 0
                
                metrics_data.append({
                    'Item': item,
                    'Current Value ($)': f"${current_value:,.2f}",
                    f'Historical Return (%)': f"{total_return:+.2f}%",
                    'Est. APR (%)': f"{apr:+.2f}%",
                    'Data Points': len(timeline)
                })
            else:
                metrics_data.append({
                    'Item': item,
                    'Current Value ($)': f"${current_value:,.2f}",
                    f'Historical Return (%)': "Single data point",
                    'Est. APR (%)': "N/A",
                    'Data Points': len(timeline)
                })
        else:
            # No historical data
            metrics_data.append({
                'Item': item,
                'Current Value ($)': f"${current_value:,.2f}",
                f'Historical Return (%)': "No historical data",
                'Est. APR (%)': "N/A",
                'Data Points': 0
            })
    
    return pd.DataFrame(metrics_data)
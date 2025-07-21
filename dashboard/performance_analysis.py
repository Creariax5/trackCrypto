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

# ========================================
# REAL DATA FUNCTIONS (No Mock Data)
# ========================================

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

# ========================================
# MAIN PERFORMANCE ANALYSIS PAGE
# ========================================

def performance_analysis_page():
    """
    Performance analysis page with REAL data (no mock data) and fixed DataFrame error
    """
    
    def performance_content(data: pd.DataFrame, filters: dict, metrics: dict):
        """
        Page-specific content for performance analysis with REAL calculations
        """
        
        config_manager = ConfigManager()
        
        st.header("🎯 Performance Comparison")
        
        # Check data availability
        has_historical = 'timestamp' in data.columns and len(data['timestamp'].unique()) > 1
        
        if not has_historical:
            st.warning("⚠️ Limited historical data. Showing current portfolio analysis instead of performance trends.")
        
        # Analysis type selector
        analysis_type = st.selectbox(
            "Analysis Type",
            ["assets", "protocol_positions"],
            format_func=lambda x: {
                "assets": "💰 Asset Performance",
                "protocol_positions": "🏛️ Protocol Position Performance"
            }[x],
            key="perf_analysis_type"
        )
        
        # Period selector
        col1, col2 = st.columns(2)
        
        with col1:
            analysis_period = st.selectbox(
                "Analysis Period",
                [7, 14, 30, 60, 90],
                index=2,
                format_func=lambda x: f"{x} days"
            )
        
        with col2:
            selection_method = st.selectbox(
                f"Selection Method",
                ["top_value", "custom"],
                format_func=lambda x: {
                    "top_value": "🏆 Top 10 by Value",
                    "custom": "🎯 Custom Selection"
                }[x]
            )
        
        # Get asset groups for combinations
        asset_groups = config_manager.get_asset_groups()
        selected_config = None
        
        if asset_groups:
            with st.expander("⚙️ Asset Grouping Configuration"):
                config_names = ["None"] + [group.get('name', f'Config {i}') for i, group in enumerate(asset_groups)]
                selected_config_name = st.selectbox(
                    "Asset Grouping",
                    config_names,
                    key="perf_asset_config"
                )
                
                if selected_config_name != "None":
                    selected_config = next((g for g in asset_groups if g.get('name') == selected_config_name), None)
        
        # Filter data for protocol analysis if needed
        analysis_data = data.copy()
        if analysis_type == "protocol_positions" and 'protocol' in analysis_data.columns:
            analysis_data = analysis_data[analysis_data['protocol'] != 'Wallet']
        
        # Apply asset combinations if selected
        if selected_config:
            analysis_data = apply_asset_combinations(analysis_data, selected_config)
        
        # Performance calculation based on selection method
        if selection_method == "top_value":
            selected_items = get_top_items_by_value(analysis_data, analysis_type, 10)
            st.info(f"📈 Showing top 10 {analysis_type.replace('_', ' ')} by current portfolio value")
            
        else:  # custom
            available_items = get_available_items(analysis_data, analysis_type)
            selected_items = st.multiselect(
                f"Select {analysis_type.replace('_', ' ')}:",
                options=available_items,
                default=available_items[:5] if len(available_items) >= 5 else available_items,
                key="custom_items_selection"
            )
        
        # Create performance chart
        if selected_items:
            st.markdown("---")
            
            chart = create_performance_comparison_chart(
                analysis_data, selected_items, analysis_period, analysis_type
            )
            
            if chart:
                st.plotly_chart(chart, use_container_width=True)
            
            # Performance metrics table
            st.subheader("📊 Performance Metrics")
            
            metrics_data = calculate_performance_metrics(
                analysis_data, selected_items, analysis_period, analysis_type
            )
            
            # ✅ FIXED: Use .empty instead of boolean check to avoid DataFrame ambiguity error
            if not metrics_data.empty:
                st.dataframe(metrics_data, use_container_width=True, hide_index=True)
            else:
                st.warning("No performance metrics calculated")
            
        else:
            st.warning("No items selected for analysis")
    
    # Use StandardPageTemplate
    template = StandardPageTemplate()
    template.create_page(
        page_title="🎯 Performance Analysis",
        page_description="Compare asset and protocol performance with real historical data (no mock data)",
        content_function=performance_content,
        page_key="performance_analysis"
    )
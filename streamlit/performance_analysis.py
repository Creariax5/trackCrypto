import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import timedelta


def get_top_assets_by_value(df, top_n=10):
    """Get top N assets by current portfolio value"""
    current_time = df['timestamp'].max()
    current_data = df[df['timestamp'] == current_time]
    
    asset_values = current_data.groupby('coin')['usd_value_numeric'].sum().sort_values(ascending=False)
    return asset_values.head(top_n).index.tolist()


def get_top_performing_assets(df, period_days=30, top_n=10):
    """Get top N performing assets by return percentage"""
    current_time = df['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    
    asset_returns = []
    
    for asset in df['coin'].unique():
        asset_data = df[df['coin'] == asset]
        
        # Current value
        current_data = asset_data[asset_data['timestamp'] == current_time]
        if len(current_data) == 0:
            continue
        current_value = current_data['usd_value_numeric'].sum()
        
        # Period start value
        period_data = asset_data[asset_data['timestamp'] >= period_start]
        if len(period_data) == 0:
            continue
            
        start_data = period_data.sort_values('timestamp').iloc[0]
        start_value = start_data['usd_value_numeric']
        
        if start_value > 0:
            return_pct = ((current_value - start_value) / start_value) * 100
            asset_returns.append({'asset': asset, 'return': return_pct, 'current_value': current_value})
    
    # Sort by return and filter for assets with meaningful value (>$1)
    asset_returns_df = pd.DataFrame(asset_returns)
    if len(asset_returns_df) > 0:
        filtered_returns = asset_returns_df[asset_returns_df['current_value'] > 1]
        top_performers = filtered_returns.sort_values('return', ascending=False).head(top_n)
        return top_performers['asset'].tolist()
    
    return []


def get_top_protocols_by_value(df, top_n=10):
    """Get top N protocols by current portfolio value"""
    if 'protocol' not in df.columns:
        return []
        
    current_time = df['timestamp'].max()
    current_data = df[df['timestamp'] == current_time]
    
    protocol_values = current_data.groupby('protocol')['usd_value_numeric'].sum().sort_values(ascending=False)
    return protocol_values.head(top_n).index.tolist()


def get_top_performing_protocols(df, period_days=30, top_n=10):
    """Get top N performing protocols by return percentage"""
    if 'protocol' not in df.columns:
        return []
        
    current_time = df['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    
    protocol_returns = []
    
    for protocol in df['protocol'].unique():
        if pd.isna(protocol):
            continue
            
        protocol_data = df[df['protocol'] == protocol]
        
        # Current value
        current_data = protocol_data[protocol_data['timestamp'] == current_time]
        if len(current_data) == 0:
            continue
        current_value = current_data['usd_value_numeric'].sum()
        
        # Period start value
        period_data = protocol_data[protocol_data['timestamp'] >= period_start]
        if len(period_data) == 0:
            continue
            
        start_value = period_data.sort_values('timestamp').iloc[0]['usd_value_numeric']
        
        if start_value > 0:
            return_pct = ((current_value - start_value) / start_value) * 100
            protocol_returns.append({
                'protocol': protocol, 
                'return': return_pct, 
                'current_value': current_value
            })
    
    # Sort by return and filter for protocols with meaningful value (>$5)
    protocol_returns_df = pd.DataFrame(protocol_returns)
    if len(protocol_returns_df) > 0:
        filtered_returns = protocol_returns_df[protocol_returns_df['current_value'] > 5]
        top_performers = filtered_returns.sort_values('return', ascending=False).head(top_n)
        return top_performers['protocol'].tolist()
    
    return []


def create_asset_performance_comparison(df, selected_assets, period_days=30):
    """Create simplified asset performance comparison chart"""
    if not selected_assets:
        return None
    
    current_time = df['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    filtered_df = df[df['timestamp'] >= period_start]
    
    performance_data = []
    
    for asset in selected_assets:
        asset_data = filtered_df[filtered_df['coin'] == asset]
        if len(asset_data) == 0:
            continue
            
        # Group by timestamp and sum values
        asset_timeline = asset_data.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
        asset_timeline = asset_timeline.sort_values('timestamp')
        
        if len(asset_timeline) >= 2:
            initial_value = asset_timeline['usd_value_numeric'].iloc[0]
            
            for _, row in asset_timeline.iterrows():
                if initial_value > 0:
                    cumulative_return = ((row['usd_value_numeric'] / initial_value) - 1) * 100
                else:
                    cumulative_return = 0
                    
                performance_data.append({
                    'timestamp': row['timestamp'],
                    'asset': asset,
                    'cumulative_return': cumulative_return
                })
    
    if not performance_data:
        return None
    
    perf_df = pd.DataFrame(performance_data)
    
    # Create the chart
    fig = px.line(
        perf_df,
        x='timestamp',
        y='cumulative_return',
        color='asset',
        title=f"📈 Asset Performance Comparison ({period_days} Days)",
        labels={'cumulative_return': 'Cumulative Return (%)', 'timestamp': 'Date'}
    )
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    # Update layout
    fig.update_layout(
        hovermode='x unified',
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="right", 
            x=1
        ),
        height=500
    )
    
    return fig


def create_protocol_performance_comparison(df, selected_protocols, period_days=30):
    """Create protocol performance comparison chart"""
    if not selected_protocols or 'protocol' not in df.columns:
        return None
    
    current_time = df['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    filtered_df = df[df['timestamp'] >= period_start]
    
    performance_data = []
    
    for protocol in selected_protocols:
        if pd.isna(protocol):
            continue
            
        protocol_data = filtered_df[filtered_df['protocol'] == protocol]
        if len(protocol_data) == 0:
            continue
            
        # Group by timestamp and sum values
        protocol_timeline = protocol_data.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
        protocol_timeline = protocol_timeline.sort_values('timestamp')
        
        if len(protocol_timeline) >= 2:
            initial_value = protocol_timeline['usd_value_numeric'].iloc[0]
            
            for _, row in protocol_timeline.iterrows():
                if initial_value > 0:
                    cumulative_return = ((row['usd_value_numeric'] / initial_value) - 1) * 100
                else:
                    cumulative_return = 0
                    
                performance_data.append({
                    'timestamp': row['timestamp'],
                    'protocol': protocol,
                    'cumulative_return': cumulative_return
                })
    
    if not performance_data:
        return None
    
    perf_df = pd.DataFrame(performance_data)
    
    # Create the chart
    fig = px.line(
        perf_df,
        x='timestamp',
        y='cumulative_return',
        color='protocol',
        title=f"🏛️ Protocol Performance Comparison ({period_days} Days)",
        labels={'cumulative_return': 'Cumulative Return (%)', 'timestamp': 'Date'}
    )
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    # Update layout
    fig.update_layout(
        hovermode='x unified',
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="right", 
            x=1
        ),
        height=500
    )
    
    return fig


def simplified_performance_analysis(historical_df):
    """Simplified performance analysis with asset and protocol comparison"""
    
    st.header("📊 Performance Comparison")
    
    # Main analysis type selector
    analysis_type = st.selectbox(
        "Analysis Type",
        options=["assets", "protocols"],
        format_func=lambda x: {
            "assets": "💰 Asset Performance", 
            "protocols": "🏛️ Protocol Performance"
        }[x],
        key="analysis_type"
    )
    
    # Common settings
    col1, col2 = st.columns(2)
    
    with col1:
        analysis_period = st.selectbox(
            "Analysis Period",
            options=[7, 14, 30, 60, 90],
            index=2,  # Default to 30 days
            format_func=lambda x: f"{x} days"
        )
    
    # Asset or Protocol specific logic
    if analysis_type == "assets":
        with col2:
            selection_method = st.selectbox(
                "Show Assets",
                options=["top_value", "top_performers", "custom"],
                format_func=lambda x: {
                    "top_value": "🏆 Top 10 by Portfolio Value", 
                    "top_performers": "🚀 Top 10 Best Performers",
                    "custom": "🎯 Custom Selection"
                }[x]
            )
        
        # Get selected assets based on method
        if selection_method == "top_value":
            selected_items = get_top_assets_by_value(historical_df, 10)
            st.info(f"Showing top 10 assets by current portfolio value")
            
        elif selection_method == "top_performers":
            selected_items = get_top_performing_assets(historical_df, analysis_period, 10)
            st.info(f"Showing top 10 best performing assets over {analysis_period} days")
            
        else:  # custom
            available_items = sorted(historical_df['coin'].unique())
            selected_items = st.multiselect(
                "Select assets:",
                options=available_items,
                default=available_items[:5] if len(available_items) >= 5 else available_items
            )
        
        # Show selected assets info and create chart
        if selected_items:
            st.write(f"**Selected Assets ({len(selected_items)}):** {', '.join(selected_items)}")
            chart = create_asset_performance_comparison(historical_df, selected_items, analysis_period)
        else:
            chart = None
            st.warning("No assets selected or available for analysis.")
    
    else:  # protocols
        # Check if protocol data exists
        if 'protocol' not in historical_df.columns:
            st.error("❌ Protocol data not found in the dataset. Please ensure your data includes protocol information.")
            return
        
        # Filter out NaN protocols for counting
        available_protocols = historical_df['protocol'].dropna().unique()
        if len(available_protocols) == 0:
            st.error("❌ No protocol data available in the dataset.")
            return
        
        with col2:
            selection_method = st.selectbox(
                "Show Protocols",
                options=["top_value", "top_performers", "custom"],
                format_func=lambda x: {
                    "top_value": "🏆 Top 10 by Portfolio Value", 
                    "top_performers": "🚀 Top 10 Best Performers",
                    "custom": "🎯 Custom Selection"
                }[x]
            )
        
        # Get selected protocols based on method
        if selection_method == "top_value":
            selected_items = get_top_protocols_by_value(historical_df, 10)
            st.info(f"Showing top 10 protocols by current portfolio value")
            
        elif selection_method == "top_performers":
            selected_items = get_top_performing_protocols(historical_df, analysis_period, 10)
            st.info(f"Showing top 10 best performing protocols over {analysis_period} days")
            
        else:  # custom
            available_items = sorted(available_protocols)
            selected_items = st.multiselect(
                "Select protocols:",
                options=available_items,
                default=available_items[:5] if len(available_items) >= 5 else available_items
            )
        
        # Show selected protocols info and create chart
        if selected_items:
            st.write(f"**Selected Protocols ({len(selected_items)}):** {', '.join(selected_items)}")
            chart = create_protocol_performance_comparison(historical_df, selected_items, analysis_period)
        else:
            chart = None
            st.warning("No protocols selected or available for analysis.")
    
    # Display the chart
    if chart:
        st.plotly_chart(chart, use_container_width=True)
    elif selected_items:
        st.warning("No data available for the selected items and period.")


# Main function to integrate into your app
def performance_analysis_page():
    """Main performance analysis page - simplified version with asset and protocol comparison"""
    st.title("📊 Portfolio Performance Analysis")
    st.markdown("---")

    # Load historical data
    from utils import load_historical_data  # Assuming you have this function
    historical_df = load_historical_data()

    if historical_df is None:
        st.warning("⚠️ Historical data file not found. Please run the master portfolio tracker first.")
        
        # Option to upload file manually
        uploaded_file = st.file_uploader("Upload historical data CSV file", type=['csv'])
        
        if uploaded_file:
            historical_df = pd.read_csv(uploaded_file)
            # Add your data processing logic here
            
        if historical_df is None:
            return

    # Run simplified performance analysis (assets and protocols)
    simplified_performance_analysis(historical_df)


# If running as standalone
if __name__ == "__main__":
    performance_analysis_page()
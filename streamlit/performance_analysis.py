import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import timedelta


def create_protocol_asset_identifier(df):
    """Create unique identifier combining protocol and asset, excluding wallet positions"""
    if 'protocol' not in df.columns:
        return df
    
    df_copy = df.copy()
    # Filter out wallet positions (direct token holdings)
    df_copy = df_copy[df_copy['protocol'] != 'Wallet'].copy()
    # Create a unique identifier for each protocol-asset combination
    df_copy['protocol_asset'] = df_copy['coin'] + " | " + df_copy['protocol']
    return df_copy


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


def get_top_protocol_assets_by_value(df, top_n=10):
    """Get top N protocol-asset combinations by current portfolio value, excluding wallet positions"""
    if 'protocol' not in df.columns:
        return []
    
    # Filter out wallet positions first
    df_filtered = df[df['protocol'] != 'Wallet'].copy()
    
    # Create protocol-asset identifier
    df_with_identifier = create_protocol_asset_identifier(df_filtered)
    
    current_time = df_with_identifier['timestamp'].max()
    current_data = df_with_identifier[df_with_identifier['timestamp'] == current_time]
    
    protocol_asset_values = current_data.groupby('protocol_asset')['usd_value_numeric'].sum().sort_values(ascending=False)
    return protocol_asset_values.head(top_n).index.tolist()


def get_top_performing_protocol_assets(df, period_days=30, top_n=10):
    """Get top N performing protocol-asset combinations by return percentage, excluding wallet positions"""
    if 'protocol' not in df.columns:
        return []
    
    # Filter out wallet positions first
    df_filtered = df[df['protocol'] != 'Wallet'].copy()
    
    # Create protocol-asset identifier
    df_with_identifier = create_protocol_asset_identifier(df_filtered)
    
    current_time = df_with_identifier['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    
    protocol_asset_returns = []
    
    for protocol_asset in df_with_identifier['protocol_asset'].unique():
        if pd.isna(protocol_asset):
            continue
            
        protocol_asset_data = df_with_identifier[df_with_identifier['protocol_asset'] == protocol_asset]
        
        # Current value
        current_data = protocol_asset_data[protocol_asset_data['timestamp'] == current_time]
        if len(current_data) == 0:
            continue
        current_value = current_data['usd_value_numeric'].sum()
        
        # Period start value
        period_data = protocol_asset_data[protocol_asset_data['timestamp'] >= period_start]
        if len(period_data) == 0:
            continue
            
        start_value = period_data.sort_values('timestamp').iloc[0]['usd_value_numeric']
        
        if start_value > 0:
            return_pct = ((current_value - start_value) / start_value) * 100
            protocol_asset_returns.append({
                'protocol_asset': protocol_asset, 
                'return': return_pct, 
                'current_value': current_value
            })
    
    # Sort by return and filter for protocol-assets with meaningful value (>$5)
    protocol_asset_returns_df = pd.DataFrame(protocol_asset_returns)
    if len(protocol_asset_returns_df) > 0:
        filtered_returns = protocol_asset_returns_df[protocol_asset_returns_df['current_value'] > 5]
        top_performers = filtered_returns.sort_values('return', ascending=False).head(top_n)
        return top_performers['protocol_asset'].tolist()
    
    return []


def calculate_apr_data(df, selected_items, period_days, analysis_type):
    """Calculate APR and summary data for selected assets or protocol-assets"""
    current_time = df['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    filtered_df = df[df['timestamp'] >= period_start]
    
    apr_data = []
    total_start_value = 0
    total_end_value = 0
    
    if analysis_type == 'assets':
        item_col = 'coin'
    else:  # protocol_positions
        # Filter out wallet positions first
        filtered_df = filtered_df[filtered_df['protocol'] != 'Wallet'].copy()
        # Create protocol-asset identifier for filtered data
        filtered_df = create_protocol_asset_identifier(filtered_df)
        item_col = 'protocol_asset'
    
    for item in selected_items:
        if pd.isna(item):
            continue
            
        item_data = filtered_df[filtered_df[item_col] == item]
        if len(item_data) == 0:
            continue
            
        # Group by timestamp and sum values
        item_timeline = item_data.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
        item_timeline = item_timeline.sort_values('timestamp')
        
        if len(item_timeline) >= 2:
            start_value = item_timeline['usd_value_numeric'].iloc[0]
            end_value = item_timeline['usd_value_numeric'].iloc[-1]
            
            # Calculate period return
            if start_value > 0:
                period_return = ((end_value / start_value) - 1) * 100
                # Calculate APR (annualized)
                apr = (((end_value / start_value) ** (365 / period_days)) - 1) * 100
            else:
                period_return = 0
                apr = 0
            
            apr_data.append({
                'Item': item,
                'Start Value ($)': start_value,
                'End Value ($)': end_value,
                f'{period_days}d Return (%)': period_return,
                'APR (%)': apr
            })
            
            total_start_value += start_value
            total_end_value += end_value
    
    # Calculate total portfolio APR
    if total_start_value > 0:
        total_period_return = ((total_end_value / total_start_value) - 1) * 100
        total_apr = (((total_end_value / total_start_value) ** (365 / period_days)) - 1) * 100
    else:
        total_period_return = 0
        total_apr = 0
    
    return apr_data, total_start_value, total_end_value, total_period_return, total_apr


def create_apr_summary_table(apr_data, total_start_value, total_end_value, total_period_return, total_apr, period_days, analysis_type):
    """Create and display APR summary table"""
    if not apr_data:
        st.warning("No APR data available for the selected items.")
        return
    
    # Create DataFrame
    apr_df = pd.DataFrame(apr_data)
    
    # Format the DataFrame for display
    apr_df_display = apr_df.copy()
    apr_df_display['Start Value ($)'] = apr_df_display['Start Value ($)'].apply(lambda x: f"${x:,.2f}")
    apr_df_display['End Value ($)'] = apr_df_display['End Value ($)'].apply(lambda x: f"${x:,.2f}")
    apr_df_display[f'{period_days}d Return (%)'] = apr_df_display[f'{period_days}d Return (%)'].apply(lambda x: f"{x:+.2f}%")
    apr_df_display['APR (%)'] = apr_df_display['APR (%)'].apply(lambda x: f"{x:+.2f}%")
    
    # Display the table
    item_type = "Assets" if analysis_type == "assets" else "Protocol Positions"
    st.subheader(f"📊 APR Summary - {item_type}")
    
    st.dataframe(
        apr_df_display,
        use_container_width=True,
        hide_index=True
    )
    
    # Display total summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Start Value",
            f"${total_start_value:,.2f}"
        )
    
    with col2:
        st.metric(
            "Total End Value",
            f"${total_end_value:,.2f}"
        )
    
    with col3:
        st.metric(
            f"{period_days}d Return",
            f"{total_period_return:+.2f}%"
        )
    
    with col4:
        st.metric(
            "Total APR",
            f"{total_apr:+.2f}%"
        )
    
    # Additional insights
    st.markdown("---")
    st.markdown("**📈 Key Insights:**")
    
    if apr_data:
        # Find best and worst performers
        best_performer = max(apr_data, key=lambda x: x['APR (%)'])
        worst_performer = min(apr_data, key=lambda x: x['APR (%)'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"🏆 **Best Performer:** {best_performer['Item']} ({best_performer['APR (%)']:+.2f}% APR)")
        
        with col2:
            if worst_performer['APR (%)'] < 0:
                st.error(f"📉 **Worst Performer:** {worst_performer['Item']} ({worst_performer['APR (%)']:+.2f}% APR)")
            else:
                st.info(f"📊 **Lowest Performer:** {worst_performer['Item']} ({worst_performer['APR (%)']:+.2f}% APR)")


def create_asset_performance_comparison(df, selected_assets, period_days=30):
    """Create asset performance comparison chart"""
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


def create_protocol_asset_performance_comparison(df, selected_protocol_assets, period_days=30):
    """Create protocol-asset performance comparison chart with separate positions, excluding wallet positions"""
    if not selected_protocol_assets or 'protocol' not in df.columns:
        return None
    
    current_time = df['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    filtered_df = df[df['timestamp'] >= period_start]
    
    # Filter out wallet positions first
    filtered_df = filtered_df[filtered_df['protocol'] != 'Wallet'].copy()
    
    # Create protocol-asset identifier
    filtered_df = create_protocol_asset_identifier(filtered_df)
    
    performance_data = []
    
    for protocol_asset in selected_protocol_assets:
        if pd.isna(protocol_asset):
            continue
            
        protocol_asset_data = filtered_df[filtered_df['protocol_asset'] == protocol_asset]
        if len(protocol_asset_data) == 0:
            continue
            
        # Group by timestamp and sum values
        protocol_asset_timeline = protocol_asset_data.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
        protocol_asset_timeline = protocol_asset_timeline.sort_values('timestamp')
        
        if len(protocol_asset_timeline) >= 2:
            initial_value = protocol_asset_timeline['usd_value_numeric'].iloc[0]
            
            for _, row in protocol_asset_timeline.iterrows():
                if initial_value > 0:
                    cumulative_return = ((row['usd_value_numeric'] / initial_value) - 1) * 100
                else:
                    cumulative_return = 0
                    
                performance_data.append({
                    'timestamp': row['timestamp'],
                    'protocol_asset': protocol_asset,
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
        color='protocol_asset',
        title=f"🏛️ Protocol Position Performance Comparison ({period_days} Days)",
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
    """Simplified performance analysis with asset and protocol-asset comparison"""
    
    st.header("📊 Performance Comparison")
    
    # Main analysis type selector
    analysis_type = st.selectbox(
        "Analysis Type",
        options=["assets", "protocol_positions"],
        format_func=lambda x: {
            "assets": "💰 Asset Performance", 
            "protocol_positions": "🏛️ Protocol Position Performance"
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
    
    # Asset or Protocol Position specific logic
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
        
        # Create chart
        if selected_items:
            chart = create_asset_performance_comparison(historical_df, selected_items, analysis_period)
        else:
            chart = None
            st.warning("No assets selected or available for analysis.")
    
    else:  # protocol_positions
        # Check if protocol data exists
        if 'protocol' not in historical_df.columns:
            st.error("❌ Protocol data not found in the dataset. Please ensure your data includes protocol information.")
            return
        
        # Filter out wallet positions and create protocol-asset combinations
        df_no_wallet = historical_df[historical_df['protocol'] != 'Wallet'].copy()
        
        if len(df_no_wallet) == 0:
            st.error("❌ No protocol positions found in the dataset. Only wallet positions available.")
            return
            
        df_with_identifier = create_protocol_asset_identifier(df_no_wallet)
        available_protocol_assets = df_with_identifier['protocol_asset'].dropna().unique()
        
        if len(available_protocol_assets) == 0:
            st.error("❌ No protocol position data available in the dataset.")
            return
        
        with col2:
            selection_method = st.selectbox(
                "Show Protocol Positions",
                options=["top_value", "top_performers", "custom"],
                format_func=lambda x: {
                    "top_value": "🏆 Top 10 by Portfolio Value", 
                    "top_performers": "🚀 Top 10 Best Performers",
                    "custom": "🎯 Custom Selection"
                }[x]
            )
        
        # Get selected protocol-assets based on method
        if selection_method == "top_value":
            selected_items = get_top_protocol_assets_by_value(historical_df, 10)
            st.info(f"Showing top 10 protocol positions by current portfolio value")
            
        elif selection_method == "top_performers":
            selected_items = get_top_performing_protocol_assets(historical_df, analysis_period, 10)
            st.info(f"Showing top 10 best performing protocol positions over {analysis_period} days")
            
        else:  # custom
            selected_items = st.multiselect(
                "Select protocol positions:",
                options=sorted(available_protocol_assets),
                default=sorted(available_protocol_assets)[:5] if len(available_protocol_assets) >= 5 else sorted(available_protocol_assets),
                help="Format: Asset | Protocol (e.g., USDC | Peapods Finance V2 (Lending))"
            )
        
        # Create chart
        if selected_items:
            chart = create_protocol_asset_performance_comparison(historical_df, selected_items, analysis_period)
        else:
            chart = None
            st.warning("No protocol positions selected or available for analysis.")
    
    # Display the chart
    if chart:
        st.plotly_chart(chart, use_container_width=True)
    elif selected_items:
        st.warning("No data available for the selected items and period.")
    
    # Add APR Summary Table after the chart
    if selected_items:
        st.markdown("---")
        
        # Calculate APR data
        apr_data, total_start_value, total_end_value, total_period_return, total_apr = calculate_apr_data(
            historical_df, selected_items, analysis_period, analysis_type
        )
        
        # Display APR summary table
        create_apr_summary_table(
            apr_data, total_start_value, total_end_value, 
            total_period_return, total_apr, analysis_period, analysis_type
        )


# Main function to integrate into your app
def performance_analysis_page():
    """Main performance analysis page - simplified version with asset and protocol position comparison"""
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

    # Run simplified performance analysis
    simplified_performance_analysis(historical_df)


# If running as standalone
if __name__ == "__main__":
    performance_analysis_page()
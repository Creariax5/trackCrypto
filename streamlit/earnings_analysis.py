import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import timedelta, datetime, date
import os
import glob
from typing import Dict, List, Tuple, Optional
import warnings
import subprocess
import sys
warnings.filterwarnings('ignore')

def parse_currency(value_str):
    """Parse currency string to float"""
    if pd.isna(value_str) or value_str == 'None':
        return 0.0
    try:
        # Remove $ and commas, convert to float
        clean_str = str(value_str).replace('$', '').replace(',', '')
        return float(clean_str)
    except:
        return 0.0

def parse_timestamp(timestamp_str):
    """Parse timestamp string"""
    if pd.isna(timestamp_str):
        return None
    try:
        # Try different timestamp formats
        formats = [
            '%d-%m-%Y_%H-%M-%S',
            '%Y-%m-%d_%H-%M-%S', 
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d-%m-%Y'
        ]
        
        for fmt in formats:
            try:
                return pd.to_datetime(timestamp_str, format=fmt)
            except:
                continue
        
        # If no format works, try pandas auto-parsing
        return pd.to_datetime(timestamp_str)
    except:
        return None

def run_pnl_calculator():
    """Run the PnL calculator script if needed"""
    try:
        result = subprocess.run([sys.executable, 'calculate_portfolio_pnl.py'], 
                              capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return True, "PnL calculation completed successfully"
        else:
            return False, f"PnL calculation failed: {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "PnL calculation timed out"
    except Exception as e:
        return False, f"Error running PnL calculator: {str(e)}"

def load_portfolio_data_with_pnl() -> pd.DataFrame:
    """Load portfolio data with PnL calculations"""
    try:
        # First try to load PnL-enhanced file
        pnl_file = "portfolio_data/ALL_PORTFOLIOS_HISTORY_WITH_PNL.csv"
        base_file = "portfolio_data/ALL_PORTFOLIOS_HISTORY.csv"
        
        if os.path.exists(pnl_file):
            df = pd.read_csv(pnl_file)
            st.success(f"✅ Loaded PnL-enhanced data from: {pnl_file}")
        elif os.path.exists(base_file):
            st.warning("⚠️ PnL-enhanced file not found. Loading base data...")
            df = pd.read_csv(base_file)
            
            # Offer to calculate PnL
            if st.button("🔄 Calculate PnL for Enhanced Analysis"):
                with st.spinner("Running PnL calculations..."):
                    success, message = run_pnl_calculator()
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                        return df
        else:
            st.error("❌ No portfolio data files found")
            return pd.DataFrame()
        
        # Process the data
        if 'usd_value' in df.columns and 'usd_value_numeric' not in df.columns:
            df['usd_value_numeric'] = df['usd_value'].apply(parse_currency)
        
        # Handle timestamp parsing
        if 'source_file_timestamp' in df.columns:
            df['timestamp'] = df['source_file_timestamp'].apply(parse_timestamp)
            df = df.dropna(subset=['timestamp'])
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        else:
            df['timestamp'] = pd.Timestamp.now()
        
        # Filter out zero value positions
        df = df[df['usd_value_numeric'] > 0]
        
        # Sort by timestamp
        df = df.sort_values('timestamp')
        
        return df
        
    except Exception as e:
        st.error(f"Error loading portfolio data: {str(e)}")
        return pd.DataFrame()

def create_pnl_waterfall_chart(df: pd.DataFrame) -> go.Figure:
    """Create waterfall chart showing PnL progression"""
    if 'pnl_since_last_update' not in df.columns:
        return None
    
    # Get daily PnL totals
    daily_pnl = df[df['pnl_since_last_update'] != 0].groupby(
        df['timestamp'].dt.date
    )['pnl_since_last_update'].sum().reset_index()
    
    daily_pnl = daily_pnl.sort_values('timestamp')
    
    if len(daily_pnl) == 0:
        return None
    
    # Create waterfall chart
    fig = go.Figure(go.Waterfall(
        name="Daily PnL",
        orientation="v",
        measure=["relative"] * len(daily_pnl),
        x=daily_pnl['timestamp'].astype(str),
        textposition="outside",
        text=[f"${v:+,.0f}" for v in daily_pnl['pnl_since_last_update']],
        y=daily_pnl['pnl_since_last_update'],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "green"}},
        decreasing={"marker": {"color": "red"}}
    ))
    
    fig.update_layout(
        title="💧 Daily PnL Waterfall Chart",
        showlegend=False,
        height=500,
        xaxis_title="Date",
        yaxis_title="PnL ($)"
    )
    
    return fig

def create_pnl_heatmap(df: pd.DataFrame) -> go.Figure:
    """Create heatmap of PnL by protocol and date"""
    if 'pnl_since_last_update' not in df.columns:
        return None
    
    # Filter data with PnL
    pnl_data = df[df['pnl_since_last_update'] != 0].copy()
    
    if len(pnl_data) == 0:
        return None
    
    # Create pivot table
    pnl_pivot = pnl_data.pivot_table(
        index='protocol',
        columns=pnl_data['timestamp'].dt.date,
        values='pnl_since_last_update',
        aggfunc='sum',
        fill_value=0
    )
    
    # Only show protocols with significant PnL
    protocol_totals = pnl_pivot.sum(axis=1).abs()
    significant_protocols = protocol_totals[protocol_totals > 1].index
    pnl_pivot = pnl_pivot.loc[significant_protocols]
    
    if len(pnl_pivot) == 0:
        return None
    
    fig = go.Figure(data=go.Heatmap(
        z=pnl_pivot.values,
        x=[str(col) for col in pnl_pivot.columns],
        y=pnl_pivot.index,
        colorscale='RdYlGn',
        zmid=0,
        colorbar=dict(title="PnL ($)"),
        hovertemplate='Protocol: %{y}<br>Date: %{x}<br>PnL: $%{z:,.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="🔥 PnL Heatmap by Protocol and Date",
        xaxis_title="Date",
        yaxis_title="Protocol",
        height=max(400, len(pnl_pivot) * 25)
    )
    
    return fig

def create_pnl_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Create distribution chart of PnL values"""
    if 'pnl_since_last_update' not in df.columns:
        return None
    
    pnl_data = df[df['pnl_since_last_update'] != 0]['pnl_since_last_update']
    
    if len(pnl_data) == 0:
        return None
    
    fig = go.Figure()
    
    # Add histogram
    fig.add_trace(go.Histogram(
        x=pnl_data,
        nbinsx=50,
        name="PnL Distribution",
        marker_color='lightblue',
        opacity=0.7
    ))
    
    # Add vertical line at zero
    fig.add_vline(x=0, line_dash="dash", line_color="red", 
                  annotation_text="Break Even", annotation_position="top")
    
    # Add mean line
    mean_pnl = pnl_data.mean()
    fig.add_vline(x=mean_pnl, line_dash="dot", line_color="green", 
                  annotation_text=f"Mean: ${mean_pnl:.2f}", annotation_position="top")
    
    fig.update_layout(
        title="📊 PnL Distribution Across All Position Updates",
        xaxis_title="PnL ($)",
        yaxis_title="Frequency",
        height=400
    )
    
    return fig

def create_cumulative_pnl_chart(df: pd.DataFrame) -> go.Figure:
    """Create cumulative PnL chart over time"""
    if 'pnl_since_last_update' not in df.columns:
        return None
    
    # Get daily PnL totals
    daily_pnl = df[df['pnl_since_last_update'] != 0].groupby(
        df['timestamp'].dt.date
    )['pnl_since_last_update'].sum().reset_index()
    
    daily_pnl = daily_pnl.sort_values('timestamp')
    daily_pnl['cumulative_pnl'] = daily_pnl['pnl_since_last_update'].cumsum()
    
    if len(daily_pnl) == 0:
        return None
    
    fig = go.Figure()
    
    # Add cumulative PnL line
    fig.add_trace(go.Scatter(
        x=daily_pnl['timestamp'],
        y=daily_pnl['cumulative_pnl'],
        mode='lines+markers',
        name='Cumulative PnL',
        line=dict(color='#00d4aa', width=3),
        marker=dict(size=8),
        hovertemplate='Date: %{x}<br>Cumulative PnL: $%{y:,.2f}<extra></extra>'
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    # Color background based on profit/loss
    for i in range(len(daily_pnl)):
        color = 'rgba(0, 255, 0, 0.1)' if daily_pnl.iloc[i]['cumulative_pnl'] >= 0 else 'rgba(255, 0, 0, 0.1)'
        if i == 0:
            continue
        fig.add_shape(
            type="rect",
            x0=daily_pnl.iloc[i-1]['timestamp'],
            x1=daily_pnl.iloc[i]['timestamp'],
            y0=min(daily_pnl['cumulative_pnl'].min(), 0),
            y1=max(daily_pnl['cumulative_pnl'].max(), 0),
            fillcolor=color,
            layer="below",
            line_width=0,
        )
    
    fig.update_layout(
        title="📈 Cumulative PnL Over Time",
        xaxis_title="Date",
        yaxis_title="Cumulative PnL ($)",
        height=500,
        hovermode='x unified'
    )
    
    return fig

def calculate_pnl_metrics(df: pd.DataFrame) -> Dict:
    """Calculate comprehensive PnL metrics"""
    if 'pnl_since_last_update' not in df.columns:
        return {}
    
    pnl_data = df[df['pnl_since_last_update'] != 0]
    
    if len(pnl_data) == 0:
        return {}
    
    # Basic metrics
    total_pnl = pnl_data['pnl_since_last_update'].sum()
    profitable_positions = len(pnl_data[pnl_data['pnl_since_last_update'] > 0])
    losing_positions = len(pnl_data[pnl_data['pnl_since_last_update'] < 0])
    total_positions = len(pnl_data)
    
    # Performance metrics
    win_rate = (profitable_positions / total_positions * 100) if total_positions > 0 else 0
    avg_win = pnl_data[pnl_data['pnl_since_last_update'] > 0]['pnl_since_last_update'].mean()
    avg_loss = pnl_data[pnl_data['pnl_since_last_update'] < 0]['pnl_since_last_update'].mean()
    
    # Risk metrics
    max_gain = pnl_data['pnl_since_last_update'].max()
    max_loss = pnl_data['pnl_since_last_update'].min()
    avg_pnl = pnl_data['pnl_since_last_update'].mean()
    
    # Profit factor
    total_profits = pnl_data[pnl_data['pnl_since_last_update'] > 0]['pnl_since_last_update'].sum()
    total_losses = abs(pnl_data[pnl_data['pnl_since_last_update'] < 0]['pnl_since_last_update'].sum())
    profit_factor = total_profits / total_losses if total_losses > 0 else float('inf')
    
    return {
        'total_pnl': total_pnl,
        'total_positions': total_positions,
        'profitable_positions': profitable_positions,
        'losing_positions': losing_positions,
        'win_rate': win_rate,
        'avg_win': avg_win if not pd.isna(avg_win) else 0,
        'avg_loss': avg_loss if not pd.isna(avg_loss) else 0,
        'max_gain': max_gain,
        'max_loss': max_loss,
        'avg_pnl': avg_pnl,
        'profit_factor': profit_factor,
        'total_profits': total_profits,
        'total_losses': total_losses
    }

def display_pnl_key_metrics(pnl_metrics: Dict):
    """Display key PnL metrics in columns"""
    if not pnl_metrics:
        st.warning("No PnL data available")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total PnL",
            f"${pnl_metrics['total_pnl']:,.2f}",
            help="Total profit/loss across all position updates"
        )
    
    with col2:
        st.metric(
            "Win Rate",
            f"{pnl_metrics['win_rate']:.1f}%",
            f"{pnl_metrics['profitable_positions']}/{pnl_metrics['total_positions']} positions",
            help="Percentage of profitable position updates"
        )
    
    with col3:
        st.metric(
            "Avg Win",
            f"${pnl_metrics['avg_win']:,.2f}",
            help="Average profit per winning position"
        )
    
    with col4:
        st.metric(
            "Avg Loss",
            f"${pnl_metrics['avg_loss']:,.2f}",
            help="Average loss per losing position"
        )
    
    # Second row of metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Max Gain",
            f"${pnl_metrics['max_gain']:,.2f}",
            help="Largest single position gain"
        )
    
    with col2:
        st.metric(
            "Max Loss",
            f"${pnl_metrics['max_loss']:,.2f}",
            help="Largest single position loss"
        )
    
    with col3:
        profit_factor_display = f"{pnl_metrics['profit_factor']:.2f}" if pnl_metrics['profit_factor'] != float('inf') else "∞"
        st.metric(
            "Profit Factor",
            profit_factor_display,
            help="Ratio of total profits to total losses"
        )
    
    with col4:
        st.metric(
            "Avg PnL",
            f"${pnl_metrics['avg_pnl']:,.2f}",
            help="Average PnL per position update"
        )

def create_top_performers_table(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Create table of top performing positions"""
    if 'pnl_since_last_update' not in df.columns:
        return pd.DataFrame()
    
    pnl_data = df[df['pnl_since_last_update'] != 0].copy()
    
    if len(pnl_data) == 0:
        return pd.DataFrame()
    
    # Get top performers
    top_performers = pnl_data.nlargest(top_n, 'pnl_since_last_update')[
        ['wallet_label', 'coin', 'protocol', 'pnl_since_last_update', 
         'pnl_percentage', 'usd_value_numeric', 'timestamp', 'days_since_last_update']
    ].copy()
    
    # Format for display
    top_performers['PnL ($)'] = top_performers['pnl_since_last_update'].apply(lambda x: f"${x:+,.2f}")
    top_performers['PnL (%)'] = top_performers['pnl_percentage'].apply(lambda x: f"{x:+.2f}%")
    top_performers['Current Value'] = top_performers['usd_value_numeric'].apply(lambda x: f"${x:,.2f}")
    top_performers['Date'] = top_performers['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
    top_performers['Days'] = top_performers['days_since_last_update'].astype(int)
    
    display_cols = ['wallet_label', 'coin', 'protocol', 'PnL ($)', 'PnL (%)', 
                   'Current Value', 'Date', 'Days']
    
    return top_performers[display_cols].rename(columns={
        'wallet_label': 'Wallet',
        'coin': 'Token',
        'protocol': 'Protocol'
    })

def create_worst_performers_table(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Create table of worst performing positions"""
    if 'pnl_since_last_update' not in df.columns:
        return pd.DataFrame()
    
    pnl_data = df[df['pnl_since_last_update'] != 0].copy()
    
    if len(pnl_data) == 0:
        return pd.DataFrame()
    
    # Get worst performers
    worst_performers = pnl_data.nsmallest(top_n, 'pnl_since_last_update')[
        ['wallet_label', 'coin', 'protocol', 'pnl_since_last_update', 
         'pnl_percentage', 'usd_value_numeric', 'timestamp', 'days_since_last_update']
    ].copy()
    
    # Format for display
    worst_performers['PnL ($)'] = worst_performers['pnl_since_last_update'].apply(lambda x: f"${x:+,.2f}")
    worst_performers['PnL (%)'] = worst_performers['pnl_percentage'].apply(lambda x: f"{x:+.2f}%")
    worst_performers['Current Value'] = worst_performers['usd_value_numeric'].apply(lambda x: f"${x:,.2f}")
    worst_performers['Date'] = worst_performers['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
    worst_performers['Days'] = worst_performers['days_since_last_update'].astype(int)
    
    display_cols = ['wallet_label', 'coin', 'protocol', 'PnL ($)', 'PnL (%)', 
                   'Current Value', 'Date', 'Days']
    
    return worst_performers[display_cols].rename(columns={
        'wallet_label': 'Wallet',
        'coin': 'Token',
        'protocol': 'Protocol'
    })

def calculate_protocol_performance_with_pnl(df: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    """Calculate protocol performance including PnL metrics"""
    if df.empty or 'timestamp' not in df.columns:
        return pd.DataFrame()
    
    # Filter recent data
    end_date = df['timestamp'].max()
    start_date = end_date - timedelta(days=days)
    period_df = df[df['timestamp'] >= start_date].copy()
    
    # Group by protocol and calculate metrics
    protocol_metrics = []
    
    for protocol in period_df['protocol'].unique():
        if pd.isna(protocol):
            continue
            
        protocol_data = period_df[period_df['protocol'] == protocol]
        
        # Basic value metrics
        current_value = protocol_data[protocol_data['timestamp'] == protocol_data['timestamp'].max()]['usd_value_numeric'].sum()
        
        # PnL metrics if available
        pnl_sum = 0
        pnl_count = 0
        pnl_positive = 0
        avg_pnl = 0
        
        if 'pnl_since_last_update' in protocol_data.columns:
            protocol_pnl = protocol_data[protocol_data['pnl_since_last_update'] != 0]
            if len(protocol_pnl) > 0:
                pnl_sum = protocol_pnl['pnl_since_last_update'].sum()
                pnl_count = len(protocol_pnl)
                pnl_positive = len(protocol_pnl[protocol_pnl['pnl_since_last_update'] > 0])
                avg_pnl = protocol_pnl['pnl_since_last_update'].mean()
        
        win_rate = (pnl_positive / pnl_count * 100) if pnl_count > 0 else 0
        
        protocol_metrics.append({
            'Protocol': protocol,
            'Current Value ($)': current_value,
            'Total PnL ($)': pnl_sum,
            'PnL Count': pnl_count,
            'Win Rate (%)': win_rate,
            'Avg PnL ($)': avg_pnl,
            'Active Positions': len(protocol_data[protocol_data['timestamp'] == protocol_data['timestamp'].max()])
        })
    
    result_df = pd.DataFrame(protocol_metrics)
    if len(result_df) > 0:
        result_df = result_df.sort_values('Total PnL ($)', ascending=False)
    
    return result_df

def earnings_analysis_page():
    """Enhanced earnings analysis page with PnL integration"""
    st.title("💰 Enhanced Earnings & PnL Analytics Dashboard")
    st.markdown("Comprehensive analysis of your DeFi portfolio performance and position-level PnL")
    
    # Sidebar controls
    st.sidebar.header("⚙️ Dashboard Controls")
    
    # Debug mode
    debug_mode = st.sidebar.checkbox("🐛 Debug Mode", value=False)
    
    # Analysis period selector
    analysis_period = st.sidebar.selectbox(
        "Analysis Period (Days)",
        [7, 14, 30, 60, 90, 180, 365],
        index=2
    )
    
    # Protocol filter
    show_wallet = st.sidebar.checkbox("Include Wallet Holdings", value=False)
    min_value_filter = st.sidebar.number_input("Minimum Value Filter ($)", min_value=0, value=10)
    
    # PnL analysis options
    st.sidebar.subheader("📊 PnL Analysis Options")
    show_new_positions_only = st.sidebar.checkbox("Show Only Position Updates (Exclude New Positions)", value=False)
    min_pnl_filter = st.sidebar.number_input("Minimum |PnL| Filter ($)", min_value=0.0, value=0.0, step=0.1)
    
    # Data refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    # Load data with PnL
    with st.spinner("Loading portfolio data with PnL calculations..."):
        df = load_portfolio_data_with_pnl()
    
    if df.empty:
        st.error("No data available. Please run wallet data collection first.")
        st.info("💡 **Next Steps:**")
        st.info("1. Run `python get_wallet_csv.py` or `python get_multi_wallet_csv.py`")
        st.info("2. Run `python master_portfolio_tracker.py` to create history")
        st.info("3. Run `python calculate_portfolio_pnl.py` to add PnL calculations")
        return
    
    # Check if PnL data is available
    has_pnl_data = 'pnl_since_last_update' in df.columns
    
    if not has_pnl_data:
        st.warning("⚠️ PnL data not found. Basic analysis mode only.")
        st.info("Run `python calculate_portfolio_pnl.py` to enable enhanced PnL analysis")
    
    # Apply filters
    if not show_wallet:
        df = df[df['protocol'] != 'Wallet']
    
    df = df[df['usd_value_numeric'] >= min_value_filter]
    
    if has_pnl_data and show_new_positions_only:
        df = df[df['is_new_position'] == False]
    
    if has_pnl_data and min_pnl_filter > 0:
        df = df[abs(df['pnl_since_last_update']) >= min_pnl_filter]
    
    # Debug information
    if debug_mode:
        st.subheader("🐛 Debug Information")
        with st.expander("Data Overview"):
            st.write(f"**Total rows:** {len(df)}")
            st.write(f"**Date range:** {df['timestamp'].min()} to {df['timestamp'].max()}")
            st.write(f"**Unique protocols:** {df['protocol'].nunique()}")
            st.write(f"**Total portfolio value:** ${df['usd_value_numeric'].sum():,.2f}")
            st.write(f"**Has PnL data:** {has_pnl_data}")
            
            if has_pnl_data:
                pnl_data = df[df['pnl_since_last_update'] != 0]
                st.write(f"**Positions with PnL:** {len(pnl_data)}")
                st.write(f"**Total PnL:** ${pnl_data['pnl_since_last_update'].sum():,.2f}")
            
            st.write("**Sample data:**")
            st.dataframe(df.head())
    
    # Data diagnosis
    st.subheader("📊 Data Diagnosis & Status")
    with st.expander("View Data Status", expanded=not debug_mode):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Records", f"{len(df):,}")
            st.metric("Date Range", f"{df['timestamp'].dt.date.nunique()} days")
            if has_pnl_data:
                updates_count = len(df[df['is_new_position'] == False])
                st.metric("Position Updates", f"{updates_count:,}")
        
        with col2:
            total_value = df['usd_value_numeric'].sum()
            st.metric("Total Value", f"${total_value:,.2f}")
            st.metric("Protocols", f"{df['protocol'].nunique()}")
            if has_pnl_data:
                total_pnl = df['pnl_since_last_update'].sum()
                st.metric("Total PnL", f"${total_pnl:+,.2f}")
        
        with col3:
            avg_daily_value = df.groupby(df['timestamp'].dt.date)['usd_value_numeric'].sum().mean()
            st.metric("Avg Daily Value", f"${avg_daily_value:,.2f}")
            data_quality = "Excellent" if has_pnl_data else "Good" if df['timestamp'].dt.date.nunique() > 1 else "Limited"
            st.metric("Data Quality", data_quality)
            if has_pnl_data:
                pnl_positions = len(df[df['pnl_since_last_update'] != 0])
                st.metric("PnL Positions", f"{pnl_positions:,}")
    
    # Enhanced PnL Analysis Section
    if has_pnl_data:
        st.markdown("---")
        st.header("📈 Enhanced PnL Analysis")
        
        # Calculate and display PnL metrics
        pnl_metrics = calculate_pnl_metrics(df)
        display_pnl_key_metrics(pnl_metrics)
        
        # PnL Charts
        st.subheader("📊 PnL Visualizations")
        
        # Create tabs for different PnL views
        pnl_tab1, pnl_tab2, pnl_tab3, pnl_tab4 = st.tabs([
            "💧 Cumulative PnL", "🌊 Waterfall Chart", "🔥 PnL Heatmap", "📊 Distribution"
        ])
        
        with pnl_tab1:
            cumulative_chart = create_cumulative_pnl_chart(df)
            if cumulative_chart:
                st.plotly_chart(cumulative_chart, use_container_width=True)
            else:
                st.info("No PnL data available for cumulative chart")
        
        with pnl_tab2:
            waterfall_chart = create_pnl_waterfall_chart(df)
            if waterfall_chart:
                st.plotly_chart(waterfall_chart, use_container_width=True)
            else:
                st.info("No daily PnL data available for waterfall chart")
        
        with pnl_tab3:
            heatmap_chart = create_pnl_heatmap(df)
            if heatmap_chart:
                st.plotly_chart(heatmap_chart, use_container_width=True)
            else:
                st.info("Insufficient data for PnL heatmap")
        
        with pnl_tab4:
            distribution_chart = create_pnl_distribution_chart(df)
            if distribution_chart:
                st.plotly_chart(distribution_chart, use_container_width=True)
            else:
                st.info("No PnL data available for distribution chart")
        
        # Performance Tables
        st.markdown("---")
        st.subheader("🏆 Top & Bottom Performers")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🚀 Top Gainers**")
            top_performers = create_top_performers_table(df, 10)
            if not top_performers.empty:
                st.dataframe(top_performers, hide_index=True)
            else:
                st.info("No profitable positions found")
        
        with col2:
            st.markdown("**📉 Biggest Losses**")
            worst_performers = create_worst_performers_table(df, 10)
            if not worst_performers.empty:
                st.dataframe(worst_performers, hide_index=True)
            else:
                st.info("No losing positions found")
    
    # Protocol Performance Analysis (Enhanced with PnL)
    st.markdown("---")
    st.header("🏛️ Protocol Performance Analysis")
    
    if has_pnl_data:
        protocol_performance = calculate_protocol_performance_with_pnl(df, analysis_period)
    else:
        # Fallback to basic protocol analysis
        protocol_performance = df.groupby('protocol').agg({
            'usd_value_numeric': ['sum', 'count', 'mean']
        }).round(2)
        protocol_performance.columns = ['Total Value', 'Position Count', 'Avg Value']
        protocol_performance = protocol_performance.reset_index()
        protocol_performance = protocol_performance.sort_values('Total Value', ascending=False)
    
    if not protocol_performance.empty:
        st.dataframe(protocol_performance, use_container_width=True, hide_index=True)
        
        # Download button for protocol analysis
        csv_data = protocol_performance.to_csv(index=False)
        st.download_button(
            label="📥 Download Protocol Analysis CSV",
            data=csv_data,
            file_name=f"protocol_analysis_with_pnl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No protocol performance data available")
    
    # Advanced Analytics Section
    if has_pnl_data:
        st.markdown("---")
        st.header("🔬 Advanced Analytics")
        
        with st.expander("📈 Position Lifecycle Analysis", expanded=False):
            # Analyze position lifecycle
            lifecycle_data = df[df['update_sequence'].notna()].groupby('position_id').agg({
                'update_sequence': 'max',
                'pnl_since_last_update': 'sum',
                'days_since_last_update': 'sum',
                'usd_value_numeric': 'last'
            }).reset_index()
            
            lifecycle_data = lifecycle_data[lifecycle_data['update_sequence'] > 0]
            
            if len(lifecycle_data) > 0:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Positions Tracked Over Time", f"{len(lifecycle_data):,}")
                    avg_updates = lifecycle_data['update_sequence'].mean()
                    st.metric("Avg Updates Per Position", f"{avg_updates:.1f}")
                
                with col2:
                    total_lifecycle_pnl = lifecycle_data['pnl_since_last_update'].sum()
                    st.metric("Total Lifecycle PnL", f"${total_lifecycle_pnl:+,.2f}")
                    avg_days_tracked = lifecycle_data['days_since_last_update'].mean()
                    st.metric("Avg Days Tracked", f"{avg_days_tracked:.1f}")
                
                # Top lifecycle performers
                st.markdown("**🏆 Best Performing Positions (Lifecycle)**")
                top_lifecycle = lifecycle_data.nlargest(10, 'pnl_since_last_update')
                st.dataframe(top_lifecycle[['position_id', 'update_sequence', 'pnl_since_last_update', 'usd_value_numeric']], hide_index=True)
            else:
                st.info("No position lifecycle data available")
    
    # Summary and insights
    st.markdown("---")
    st.header("💡 Key Insights & Recommendations")
    
    insights = []
    
    if has_pnl_data and pnl_metrics:
        if pnl_metrics['total_pnl'] > 0:
            insights.append(f"✅ **Portfolio is profitable** with total PnL of ${pnl_metrics['total_pnl']:,.2f}")
        else:
            insights.append(f"❌ **Portfolio showing losses** with total PnL of ${pnl_metrics['total_pnl']:,.2f}")
        
        if pnl_metrics['win_rate'] > 60:
            insights.append(f"🎯 **Strong win rate** of {pnl_metrics['win_rate']:.1f}% indicates good position management")
        elif pnl_metrics['win_rate'] < 40:
            insights.append(f"⚠️ **Low win rate** of {pnl_metrics['win_rate']:.1f}% suggests room for improvement in position timing")
        
        if pnl_metrics['profit_factor'] > 1.5:
            insights.append(f"💪 **Excellent profit factor** of {pnl_metrics['profit_factor']:.2f} shows strong risk management")
        elif pnl_metrics['profit_factor'] < 1:
            insights.append(f"📉 **Poor profit factor** of {pnl_metrics['profit_factor']:.2f} indicates losses exceed gains")
    
    if len(insights) > 0:
        for insight in insights:
            st.markdown(insight)
    else:
        st.info("Enable PnL calculations for detailed insights and recommendations")
    
    # Footer
    st.markdown("---")
    st.markdown("*Enhanced dashboard with position-level PnL tracking and advanced analytics*")
    st.markdown("💡 **Pro Tip:** Run the PnL calculator regularly to maintain accurate performance tracking")

if __name__ == "__main__":
    earnings_analysis_page()
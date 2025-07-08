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

def load_portfolio_data() -> pd.DataFrame:
    """Load the most recent portfolio data using existing system structure"""
    try:
        # First try to load from existing ALL_PORTFOLIOS_HISTORY.csv
        history_file = "portfolio_data/ALL_PORTFOLIOS_HISTORY.csv"
        if os.path.exists(history_file):
            df = pd.read_csv(history_file)
            
            # Parse the data using existing structure
            if 'usd_value' in df.columns:
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
            
            # Sort by timestamp and get most recent data
            df = df.sort_values('timestamp')
            
            st.success(f"Loaded historical data from: {history_file}")
            return df
        
        # Fallback to individual date folders method
        data_folder = "portfolio_data"
        if not os.path.exists(data_folder):
            st.error("No portfolio_data folder found. Please run the wallet data collection first.")
            return pd.DataFrame()
        
        # Get the most recent date folder
        date_folders = [d for d in os.listdir(data_folder) if os.path.isdir(os.path.join(data_folder, d)) and d != '__pycache__']
        if not date_folders:
            st.error("No data folders found in portfolio_data.")
            return pd.DataFrame()
        
        latest_date = max(date_folders)
        combined_folder = os.path.join(data_folder, latest_date, "combined")
        
        if not os.path.exists(combined_folder):
            # Try individual folder
            individual_folder = os.path.join(data_folder, latest_date, "individual_wallets")
            if os.path.exists(individual_folder):
                csv_files = glob.glob(os.path.join(individual_folder, "*.csv"))
            else:
                st.error(f"No data found for {latest_date}")
                return pd.DataFrame()
        else:
            csv_files = glob.glob(os.path.join(combined_folder, "*.csv"))
        
        if not csv_files:
            st.error("No CSV files found")
            return pd.DataFrame()
        
        # Load and combine all CSV files
        all_data = []
        for csv_file in csv_files:
            try:
                df_temp = pd.read_csv(csv_file)
                df_temp['source_file'] = os.path.basename(csv_file)
                df_temp['source_file_timestamp'] = latest_date
                all_data.append(df_temp)
            except Exception as e:
                st.warning(f"Error loading {csv_file}: {e}")
                continue
        
        if all_data:
            df = pd.concat(all_data, ignore_index=True)
            
            # Process the data
            if 'usd_value' in df.columns:
                df['usd_value_numeric'] = df['usd_value'].apply(parse_currency)
            
            df['timestamp'] = df['source_file_timestamp'].apply(parse_timestamp)
            df = df.dropna(subset=['timestamp'])
            df = df[df['usd_value_numeric'] > 0]
            df = df.sort_values('timestamp')
            
            st.success(f"Loaded data from {len(csv_files)} files in {latest_date}")
            return df
        else:
            st.error("No valid data found")
            return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def load_historical_data() -> pd.DataFrame:
    """Load historical data using existing system structure"""
    try:
        # First try the consolidated history file
        history_file = "portfolio_data/ALL_PORTFOLIOS_HISTORY.csv"
        if os.path.exists(history_file):
            df = pd.read_csv(history_file)
            
            # Parse the data
            if 'usd_value' in df.columns:
                df['usd_value_numeric'] = df['usd_value'].apply(parse_currency)
            
            # Handle timestamp parsing
            if 'source_file_timestamp' in df.columns:
                df['timestamp'] = df['source_file_timestamp'].apply(parse_timestamp)
                df = df.dropna(subset=['timestamp'])
            elif 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            else:
                return pd.DataFrame()
            
            # Filter and sort
            df = df[df['usd_value_numeric'] > 0]
            df = df.sort_values('timestamp')
            
            return df
        
        # Fallback to scanning date folders
        data_folder = "portfolio_data"
        all_data = []
        
        if not os.path.exists(data_folder):
            return pd.DataFrame()
        
        # Get all date folders
        for item in os.listdir(data_folder):
            if item.startswith('.') or item == '__pycache__':
                continue
                
            date_path = os.path.join(data_folder, item)
            if not os.path.isdir(date_path):
                continue
            
            # Look for CSV files in various subfolders
            csv_files = []
            
            # Check combined folder
            combined_folder = os.path.join(date_path, "combined")
            if os.path.exists(combined_folder):
                csv_files.extend(glob.glob(os.path.join(combined_folder, "*.csv")))
            
            # Check individual folder
            individual_folder = os.path.join(date_path, "individual_wallets")
            if os.path.exists(individual_folder):
                csv_files.extend(glob.glob(os.path.join(individual_folder, "*.csv")))
            
            # Process CSV files from this date
            for csv_file in csv_files:
                try:
                    df_temp = pd.read_csv(csv_file)
                    df_temp['source_file'] = os.path.basename(csv_file)
                    df_temp['source_file_timestamp'] = item
                    all_data.append(df_temp)
                except Exception as e:
                    continue
        
        if all_data:
            historical_df = pd.concat(all_data, ignore_index=True)
            
            # Process the combined data
            if 'usd_value' in historical_df.columns:
                historical_df['usd_value_numeric'] = historical_df['usd_value'].apply(parse_currency)
            
            historical_df['timestamp'] = historical_df['source_file_timestamp'].apply(parse_timestamp)
            historical_df = historical_df.dropna(subset=['timestamp'])
            historical_df = historical_df[historical_df['usd_value_numeric'] > 0]
            historical_df = historical_df.sort_values('timestamp')
            
            return historical_df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error loading historical data: {str(e)}")
        return pd.DataFrame()

def calculate_protocol_performance(df: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    """Calculate performance metrics by protocol"""
    if df.empty or 'timestamp' not in df.columns:
        return pd.DataFrame()
    
    # Ensure we have enough data
    unique_dates = df['timestamp'].dt.date.nunique()
    if unique_dates < 2:
        # If we only have one date, create a simple current value summary
        current_metrics = []
        for protocol in df['protocol'].unique():
            if pd.isna(protocol):
                continue
                
            protocol_data = df[df['protocol'] == protocol]
            current_value = protocol_data['usd_value_numeric'].sum()
            
            current_metrics.append({
                'Protocol': protocol,
                'Current Value ($)': current_value,
                'Start Value ($)': current_value,
                'Absolute Change ($)': 0,
                'Percent Change (%)': 0,
                'Peak Value ($)': current_value,
                'Min Value ($)': current_value,
                'Volatility (%)': 0,
                'Max Drawdown (%)': 0,
                'Sharpe Ratio': 0,
                'Days Active': 1
            })
        
        return pd.DataFrame(current_metrics).sort_values('Current Value ($)', ascending=False)
    
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
        
        # Calculate total value over time
        daily_values = protocol_data.groupby(protocol_data['timestamp'].dt.date)['usd_value_numeric'].sum()
        daily_values = daily_values.sort_index()
        
        if len(daily_values) < 1:
            continue
        
        # Handle single day case
        if len(daily_values) == 1:
            current_value = daily_values.iloc[0]
            protocol_metrics.append({
                'Protocol': protocol,
                'Current Value ($)': current_value,
                'Start Value ($)': current_value,
                'Absolute Change ($)': 0,
                'Percent Change (%)': 0,
                'Peak Value ($)': current_value,
                'Min Value ($)': current_value,
                'Volatility (%)': 0,
                'Max Drawdown (%)': 0,
                'Sharpe Ratio': 0,
                'Days Active': 1
            })
            continue
            
        start_value = daily_values.iloc[0]
        end_value = daily_values.iloc[-1]
        peak_value = daily_values.max()
        min_value = daily_values.min()
        
        # Calculate metrics with error handling
        absolute_change = end_value - start_value
        percent_change = (absolute_change / start_value * 100) if start_value > 0 else 0
        
        # Volatility calculation
        if len(daily_values) > 1 and daily_values.mean() > 0:
            volatility = daily_values.std() / daily_values.mean() * 100
        else:
            volatility = 0
        
        # Risk metrics
        max_drawdown = ((peak_value - min_value) / peak_value * 100) if peak_value > 0 else 0
        
        # Sharpe ratio calculation
        if len(daily_values) > 1:
            returns = daily_values.pct_change().dropna()
            if len(returns) > 0 and returns.std() > 0:
                sharpe_ratio = returns.mean() / returns.std()
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        protocol_metrics.append({
            'Protocol': protocol,
            'Current Value ($)': end_value,
            'Start Value ($)': start_value,
            'Absolute Change ($)': absolute_change,
            'Percent Change (%)': percent_change,
            'Peak Value ($)': peak_value,
            'Min Value ($)': min_value,
            'Volatility (%)': volatility,
            'Max Drawdown (%)': max_drawdown,
            'Sharpe Ratio': sharpe_ratio,
            'Days Active': len(daily_values)
        })
    
    return pd.DataFrame(protocol_metrics).sort_values('Absolute Change ($)', ascending=False)

def calculate_time_based_earnings(df: pd.DataFrame) -> Dict:
    """Calculate earnings across different time periods"""
    if df.empty:
        return {}
    
    # Check if we have multiple time points
    unique_dates = df['timestamp'].dt.date.nunique()
    if unique_dates < 2:
        # If only one date, return current value info
        current_value = df['usd_value_numeric'].sum()
        return {
            '1D': {'earnings': 0, 'return_pct': 0, 'start_value': current_value, 'end_value': current_value},
            '7D': {'earnings': 0, 'return_pct': 0, 'start_value': current_value, 'end_value': current_value},
            '30D': {'earnings': 0, 'return_pct': 0, 'start_value': current_value, 'end_value': current_value},
            '90D': {'earnings': 0, 'return_pct': 0, 'start_value': current_value, 'end_value': current_value},
            '1Y': {'earnings': 0, 'return_pct': 0, 'start_value': current_value, 'end_value': current_value}
        }
    
    current_time = df['timestamp'].max()
    
    time_periods = {
        '1D': 1,
        '7D': 7,
        '30D': 30,
        '90D': 90,
        '1Y': 365
    }
    
    earnings_summary = {}
    
    for period_name, days in time_periods.items():
        start_time = current_time - timedelta(days=days)
        period_data = df[df['timestamp'] >= start_time]
        
        if len(period_data) == 0:
            earnings_summary[period_name] = {'earnings': 0, 'return_pct': 0, 'start_value': 0, 'end_value': 0}
            continue
        
        # Calculate total portfolio value over time
        daily_totals = period_data.groupby(period_data['timestamp'].dt.date)['usd_value_numeric'].sum()
        daily_totals = daily_totals.sort_index()
        
        if len(daily_totals) >= 2:
            start_value = daily_totals.iloc[0]
            end_value = daily_totals.iloc[-1]
            earnings = end_value - start_value
            return_pct = (earnings / start_value * 100) if start_value > 0 else 0
            
            earnings_summary[period_name] = {
                'earnings': earnings,
                'return_pct': return_pct,
                'start_value': start_value,
                'end_value': end_value
            }
        elif len(daily_totals) == 1:
            # Only one data point in this period
            value = daily_totals.iloc[0]
            earnings_summary[period_name] = {
                'earnings': 0, 
                'return_pct': 0, 
                'start_value': value, 
                'end_value': value
            }
        else:
            earnings_summary[period_name] = {'earnings': 0, 'return_pct': 0, 'start_value': 0, 'end_value': 0}
    
    return earnings_summary

def create_earnings_heatmap(df: pd.DataFrame) -> go.Figure:
    """Create a heatmap of daily earnings by protocol"""
    if df.empty:
        return None
    
    # Prepare data for heatmap
    df_pivot = df.pivot_table(
        index='protocol',
        columns=df['timestamp'].dt.date,
        values='usd_value_numeric',
        aggfunc='sum'
    )
    
    # Calculate daily changes
    df_changes = df_pivot.diff(axis=1)
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=df_changes.values,
        x=[str(col) for col in df_changes.columns],
        y=df_changes.index,
        colorscale='RdYlGn',
        zmid=0,
        colorbar=dict(title="Daily Change ($)")
    ))
    
    fig.update_layout(
        title="📈 Daily Earnings Heatmap by Protocol",
        xaxis_title="Date",
        yaxis_title="Protocol",
        height=600
    )
    
    return fig

def create_portfolio_composition_overtime(df: pd.DataFrame) -> go.Figure:
    """Create stacked area chart showing portfolio composition over time"""
    if df.empty:
        return None
    
    # Group by date and protocol
    composition_data = df.groupby([df['timestamp'].dt.date, 'protocol'])['usd_value_numeric'].sum().reset_index()
    composition_pivot = composition_data.pivot(index='timestamp', columns='protocol', values='usd_value_numeric').fillna(0)
    
    # Create stacked area chart
    fig = go.Figure()
    
    for protocol in composition_pivot.columns:
        if protocol != 'Wallet':  # Skip wallet holdings for clarity
            fig.add_trace(go.Scatter(
                x=composition_pivot.index,
                y=composition_pivot[protocol],
                mode='lines',
                stackgroup='one',
                name=protocol,
                hovertemplate=f"{protocol}<br>%{{y:$,.2f}}<br>%{{x}}<extra></extra>"
            ))
    
    fig.update_layout(
        title="📊 Portfolio Composition Over Time",
        xaxis_title="Date",
        yaxis_title="Value ($)",
        hovermode='x unified',
        height=500
    )
    
    return fig

def create_roi_comparison_chart(protocol_df: pd.DataFrame) -> go.Figure:
    """Create ROI comparison chart"""
    if protocol_df.empty:
        return None
    
    # Filter for significant protocols
    significant_protocols = protocol_df[protocol_df['Current Value ($)'] >= 100].head(10)
    
    fig = go.Figure()
    
    # Create scatter plot with bubble sizes
    fig.add_trace(go.Scatter(
        x=significant_protocols['Current Value ($)'],
        y=significant_protocols['Percent Change (%)'],
        mode='markers+text',
        marker=dict(
            size=significant_protocols['Volatility (%)'] * 2,
            sizemode='area',
            sizeref=2.*max(significant_protocols['Volatility (%)'])/40**2,
            color=significant_protocols['Percent Change (%)'],
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="ROI (%)")
        ),
        text=significant_protocols['Protocol'],
        textposition="top center",
        hovertemplate="Protocol: %{text}<br>Value: $%{x:,.2f}<br>ROI: %{y:.2f}%<br>Volatility: %{marker.size:.1f}%<extra></extra>"
    ))
    
    fig.update_layout(
        title="🎯 Protocol Performance: ROI vs Value vs Volatility",
        xaxis_title="Current Value ($)",
        yaxis_title="ROI (%)",
        height=500,
        showlegend=False
    )
    
    return fig

def create_earnings_waterfall(earnings_summary: Dict) -> go.Figure:
    """Create waterfall chart for earnings breakdown"""
    if not earnings_summary:
        return None
    
    periods = list(earnings_summary.keys())
    values = [earnings_summary[period]['earnings'] for period in periods]
    
    fig = go.Figure(go.Waterfall(
        name="Earnings",
        orientation="v",
        measure=["relative"] * len(periods),
        x=periods,
        textposition="outside",
        text=[f"${v:+,.0f}" for v in values],
        y=values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "green"}},
        decreasing={"marker": {"color": "red"}}
    ))
    
    fig.update_layout(
        title="💧 Earnings Waterfall by Time Period",
        showlegend=False,
        height=400
    )
    
    return fig

def display_key_metrics(earnings_summary: Dict, protocol_df: pd.DataFrame):
    """Display key performance metrics"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if '30D' in earnings_summary:
            monthly_earnings = earnings_summary['30D']['earnings']
            st.metric(
                "30-Day Earnings",
                f"${monthly_earnings:,.2f}",
                f"{earnings_summary['30D']['return_pct']:.2f}%"
            )
        else:
            st.metric("30-Day Earnings", "No Data")
    
    with col2:
        if '7D' in earnings_summary:
            weekly_earnings = earnings_summary['7D']['earnings']
            st.metric(
                "7-Day Earnings",
                f"${weekly_earnings:,.2f}",
                f"{earnings_summary['7D']['return_pct']:.2f}%"
            )
        else:
            st.metric("7-Day Earnings", "No Data")
    
    with col3:
        if not protocol_df.empty:
            best_performer = protocol_df.iloc[0]
            st.metric(
                "Best Protocol",
                best_performer['Protocol'],
                f"${best_performer['Absolute Change ($)']:+,.2f}"
            )
        else:
            st.metric("Best Protocol", "No Data")
    
    with col4:
        if not protocol_df.empty:
            total_protocols = len(protocol_df)
            profitable_protocols = len(protocol_df[protocol_df['Absolute Change ($)'] > 0])
            st.metric(
                "Win Rate",
                f"{profitable_protocols}/{total_protocols}",
                f"{(profitable_protocols/total_protocols*100):.1f}%" if total_protocols > 0 else "0%"
            )
        else:
            st.metric("Win Rate", "No Data")

def earnings_analysis_page():
    """Main dashboard function"""
    st.title("💰 Earnings Analytics Dashboard")
    st.markdown("Track your DeFi portfolio performance across protocols and time periods")
    
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
    
    # Data refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    # Load data
    with st.spinner("Loading portfolio data..."):
        df = load_portfolio_data()
        historical_df = load_historical_data()
    
    if df.empty and historical_df.empty:
        st.error("No data available. Please run wallet data collection first.")
        st.info("💡 **Next Steps:**")
        st.info("1. Run `python get_wallet_csv.py` or `python get_multi_wallet_csv.py`")
        st.info("2. Or upload a CSV file manually using the file uploader below")
        
        uploaded_file = st.file_uploader("Upload Portfolio CSV", type=['csv'])
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                if 'usd_value' in df.columns:
                    df['usd_value_numeric'] = df['usd_value'].apply(parse_currency)
                df['timestamp'] = pd.Timestamp.now()
                historical_df = df.copy()
                st.success("Data uploaded successfully!")
            except Exception as e:
                st.error(f"Error loading uploaded file: {e}")
                return
        else:
            return
    
    # Use historical data if available, otherwise current data
    working_df = historical_df if not historical_df.empty else df
    
    # Debug information
    if debug_mode:
        st.subheader("🐛 Debug Information")
        with st.expander("Data Overview"):
            st.write(f"**Total rows:** {len(working_df)}")
            st.write(f"**Date range:** {working_df['timestamp'].min()} to {working_df['timestamp'].max()}")
            st.write(f"**Unique protocols:** {working_df['protocol'].nunique()}")
            st.write(f"**Total portfolio value:** ${working_df['usd_value_numeric'].sum():,.2f}")
            
            st.write("**Protocol breakdown:**")
            protocol_summary = working_df.groupby('protocol')['usd_value_numeric'].sum().sort_values(ascending=False)
            st.dataframe(protocol_summary)
            
            st.write("**Sample data:**")
            st.dataframe(working_df.head())
    
    # Data diagnosis
    st.subheader("📊 Data Diagnosis")
    with st.expander("View Data Status", expanded=not debug_mode):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Records", f"{len(working_df):,}")
            st.metric("Date Range", f"{working_df['timestamp'].dt.date.nunique()} days")
        
        with col2:
            total_value = working_df['usd_value_numeric'].sum()
            st.metric("Total Value", f"${total_value:,.2f}")
            st.metric("Protocols", f"{working_df['protocol'].nunique()}")
        
        with col3:
            avg_daily_value = working_df.groupby(working_df['timestamp'].dt.date)['usd_value_numeric'].sum().mean()
            st.metric("Avg Daily Value", f"${avg_daily_value:,.2f}")
            data_quality = "Good" if working_df['timestamp'].dt.date.nunique() > 1 else "Limited"
            st.metric("Data Quality", data_quality)
        
        # Data quality warnings
        if working_df['timestamp'].dt.date.nunique() == 1:
            st.warning("⚠️ **Limited Historical Data**: Only one date found. Earnings calculations will be limited.")
            st.info("💡 **To get meaningful earnings analysis:**")
            st.info("- Run data collection multiple times over several days")
            st.info("- Or upload historical CSV files with different dates")
        
        elif working_df['timestamp'].dt.date.nunique() < 7:
            st.warning(f"⚠️ **Limited Time Series**: Only {working_df['timestamp'].dt.date.nunique()} days of data found.")
            st.info("💡 **For better analysis**: Collect data over more days for accurate trends")
    
    # Filter data
    if not show_wallet:
        working_df = working_df[working_df['protocol'] != 'Wallet']
        historical_df = historical_df[historical_df['protocol'] != 'Wallet'] if not historical_df.empty else historical_df
    
    # Apply minimum value filter
    working_df = working_df[working_df['usd_value_numeric'] >= min_value_filter]
    if not historical_df.empty:
        historical_df = historical_df[historical_df['usd_value_numeric'] >= min_value_filter]
    
    # Calculate metrics
    with st.spinner("Calculating performance metrics..."):
        protocol_performance = calculate_protocol_performance(working_df, analysis_period)
        earnings_summary = calculate_time_based_earnings(working_df)
    
    # Display key metrics
    st.subheader("📊 Key Performance Metrics")
    display_key_metrics(earnings_summary, protocol_performance)
    
    st.markdown("---")
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Protocol Performance", 
        "⏰ Time-based Analysis", 
        "🔥 Heatmap", 
        "📊 Composition", 
        "📋 Detailed Tables"
    ])
    
    with tab1:
        st.subheader(f"🏛️ Protocol Performance ({analysis_period} days)")
        
        if not protocol_performance.empty:
            # ROI comparison chart
            roi_chart = create_roi_comparison_chart(protocol_performance)
            if roi_chart:
                st.plotly_chart(roi_chart, use_container_width=True)
            
            # Top and bottom performers
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🏆 Top Performers**")
                top_performers = protocol_performance.head(5)[['Protocol', 'Absolute Change ($)', 'Percent Change (%)']].copy()
                top_performers['Absolute Change ($)'] = top_performers['Absolute Change ($)'].apply(lambda x: f"${x:+,.2f}")
                top_performers['Percent Change (%)'] = top_performers['Percent Change (%)'].apply(lambda x: f"{x:+.2f}%")
                st.dataframe(top_performers, hide_index=True)
            
            with col2:
                st.markdown("**📉 Bottom Performers**")
                bottom_performers = protocol_performance.tail(5)[['Protocol', 'Absolute Change ($)', 'Percent Change (%)']].copy()
                bottom_performers['Absolute Change ($)'] = bottom_performers['Absolute Change ($)'].apply(lambda x: f"${x:+,.2f}")
                bottom_performers['Percent Change (%)'] = bottom_performers['Percent Change (%)'].apply(lambda x: f"{x:+.2f}%")
                st.dataframe(bottom_performers, hide_index=True)
        else:
            st.info("No protocol performance data available for the selected period.")
    
    with tab2:
        st.subheader("⏰ Time-based Earnings Analysis")
        
        if earnings_summary:
            # Earnings waterfall
            waterfall_chart = create_earnings_waterfall(earnings_summary)
            if waterfall_chart:
                st.plotly_chart(waterfall_chart, use_container_width=True)
            
            # Earnings summary table
            st.markdown("**📅 Earnings by Time Period**")
            earnings_df = pd.DataFrame.from_dict(earnings_summary, orient='index')
            earnings_df.index.name = 'Period'
            earnings_df['Earnings ($)'] = earnings_df['earnings'].apply(lambda x: f"${x:+,.2f}")
            earnings_df['Return (%)'] = earnings_df['return_pct'].apply(lambda x: f"{x:+.2f}%")
            earnings_df['Start Value ($)'] = earnings_df['start_value'].apply(lambda x: f"${x:,.2f}")
            earnings_df['End Value ($)'] = earnings_df['end_value'].apply(lambda x: f"${x:,.2f}")
            
            display_earnings = earnings_df[['Start Value ($)', 'End Value ($)', 'Earnings ($)', 'Return (%)']].reset_index()
            st.dataframe(display_earnings, hide_index=True)
        else:
            st.info("No time-based earnings data available.")
    
    with tab3:
        st.subheader("🔥 Daily Earnings Heatmap")
        
        if working_df['timestamp'].dt.date.nunique() > 1:
            heatmap_chart = create_earnings_heatmap(working_df)
            if heatmap_chart:
                st.plotly_chart(heatmap_chart, use_container_width=True)
            else:
                st.info("Not enough data for heatmap visualization.")
        else:
            st.info("Heatmap requires multiple days of data. Current data has only one date.")
    
    with tab4:
        st.subheader("📊 Portfolio Composition Over Time")
        
        if working_df['timestamp'].dt.date.nunique() > 1:
            composition_chart = create_portfolio_composition_overtime(working_df)
            if composition_chart:
                st.plotly_chart(composition_chart, use_container_width=True)
        else:
            st.info("Composition over time requires multiple days of data.")
            
            # Show current composition instead
            st.subheader("📊 Current Portfolio Composition")
            current_composition = working_df.groupby('protocol')['usd_value_numeric'].sum().sort_values(ascending=False)
            
            if not current_composition.empty:
                fig = px.pie(
                    values=current_composition.values,
                    names=current_composition.index,
                    title="Current Portfolio Distribution by Protocol"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        st.subheader("📋 Detailed Protocol Analysis")
        
        if not protocol_performance.empty:
            # Format the dataframe for display
            display_df = protocol_performance.copy()
            numeric_columns = ['Current Value ($)', 'Start Value ($)', 'Absolute Change ($)', 'Peak Value ($)', 'Min Value ($)']
            for col in numeric_columns:
                if col in display_df.columns:
                    display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}")
            
            percentage_columns = ['Percent Change (%)', 'Volatility (%)', 'Max Drawdown (%)']
            for col in percentage_columns:
                if col in display_df.columns:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%")
            
            if 'Sharpe Ratio' in display_df.columns:
                display_df['Sharpe Ratio'] = display_df['Sharpe Ratio'].apply(lambda x: f"{x:.3f}")
            
            st.dataframe(display_df, hide_index=True, use_container_width=True)
            
            # Download button
            csv_data = protocol_performance.to_csv(index=False)
            st.download_button(
                label="📥 Download Protocol Analysis CSV",
                data=csv_data,
                file_name=f"protocol_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No detailed protocol data available.")
    
    # Footer
    st.markdown("---")
    st.markdown("*Dashboard updates automatically with new portfolio data*")

if __name__ == "__main__":
    earnings_analysis_page()
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import timedelta, datetime
import json
import os
import glob


def get_available_configs():
    """Get list of available configuration files from config folder"""
    config_folder = "config"
    
    if not os.path.exists(config_folder):
        os.makedirs(config_folder)
        return []
    
    json_files = glob.glob(os.path.join(config_folder, "*.json"))
    configs = []
    
    for file_path in json_files:
        try:
            with open(file_path, 'r') as f:
                config_data = json.load(f)
                config_name = config_data.get('name', os.path.basename(file_path))
                
                configs.append({
                    'file_path': file_path,
                    'file_name': os.path.basename(file_path),
                    'display_name': config_name,
                    'data': config_data
                })
        except Exception as e:
            st.warning(f"Error reading {file_path}: {e}")
    
    return configs


def load_selected_config(selected_config_file):
    """Load the selected configuration file"""
    try:
        config_folder = "config"
        file_path = os.path.join(config_folder, selected_config_file)
        
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        else:
            return get_default_config()
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        return get_default_config()


def get_default_config():
    """Return default empty configuration"""
    return {
        "name": "No Configuration",
        "asset_combinations": {},
        "asset_renames": {},
        "protocol_combinations": {},
        "protocol_renames": {}
    }


def apply_earnings_combinations(df, config):
    """Apply protocol combinations for earnings analysis"""
    if 'protocol' not in df.columns:
        return df, 'protocol'
    
    df_processed = df.copy()
    
    # Filter out wallet positions for protocol analysis
    df_no_wallet = df_processed[df_processed['protocol'] != 'Wallet'].copy()
    
    if len(df_no_wallet) == 0:
        return df_processed, 'protocol'
    
    # Create protocol-asset identifier
    df_no_wallet['protocol_asset'] = df_no_wallet['coin'] + " | " + df_no_wallet['protocol']
    
    # Apply protocol combinations
    protocol_combinations = config.get('protocol_combinations', {})
    protocol_renames = config.get('protocol_renames', {})
    
    # Initialize combined protocol column
    df_no_wallet['combined_protocol'] = df_no_wallet['protocol']
    
    # Apply combinations first
    items_in_combinations = set()
    for combined_name, protocol_assets in protocol_combinations.items():
        for protocol_asset in protocol_assets:
            items_in_combinations.add(protocol_asset)
            # Replace protocol for matching protocol-asset combinations
            df_no_wallet.loc[df_no_wallet['protocol_asset'] == protocol_asset, 'combined_protocol'] = combined_name
    
    # Apply renames to protocols not in combinations
    for original_protocol_asset, new_name in protocol_renames.items():
        if original_protocol_asset not in items_in_combinations:
            df_no_wallet.loc[df_no_wallet['protocol_asset'] == original_protocol_asset, 'combined_protocol'] = new_name
    
    # Add wallet positions back with original protocol names
    df_wallet = df_processed[df_processed['protocol'] == 'Wallet'].copy()
    if len(df_wallet) > 0:
        df_wallet['combined_protocol'] = 'Wallet Holdings'
        df_wallet['protocol_asset'] = df_wallet['coin'] + " | " + df_wallet['protocol']
        
        # Combine wallet and protocol data
        df_final = pd.concat([df_no_wallet, df_wallet], ignore_index=True)
    else:
        df_final = df_no_wallet
    
    return df_final, 'combined_protocol'


def calculate_protocol_earnings(df, config, period_days=30):
    """Calculate earnings by protocol over specified period"""
    df_processed, protocol_col = apply_earnings_combinations(df, config)
    
    current_time = df_processed['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    
    # Filter data for the period
    period_df = df_processed[df_processed['timestamp'] >= period_start].copy()
    
    protocol_earnings = []
    
    for protocol in period_df[protocol_col].unique():
        if pd.isna(protocol):
            continue
            
        protocol_data = period_df[period_df[protocol_col] == protocol]
        
        # Get start and end values
        protocol_timeline = protocol_data.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
        protocol_timeline = protocol_timeline.sort_values('timestamp')
        
        if len(protocol_timeline) >= 2:
            start_value = protocol_timeline['usd_value_numeric'].iloc[0]
            end_value = protocol_timeline['usd_value_numeric'].iloc[-1]
            
            absolute_earnings = end_value - start_value
            
            if start_value > 0:
                percentage_return = (absolute_earnings / start_value) * 100
                daily_rate = (((end_value / start_value) ** (1 / period_days)) - 1) * 100
            else:
                percentage_return = 0
                daily_rate = 0
            
            protocol_earnings.append({
                'Protocol': protocol,
                'Start Value ($)': start_value,
                'End Value ($)': end_value,
                'Absolute Earnings ($)': absolute_earnings,
                'Percentage Return (%)': percentage_return,
                'Daily Rate (%)': daily_rate,
                'Current Value ($)': end_value
            })
    
    return pd.DataFrame(protocol_earnings).sort_values('Absolute Earnings ($)', ascending=False)


def calculate_daily_earnings(df, config):
    """Calculate daily earnings across all protocols"""
    df_processed, protocol_col = apply_earnings_combinations(df, config)
    
    # Group by date and sum daily values
    df_processed['date'] = df_processed['timestamp'].dt.date
    daily_values = df_processed.groupby('date')['usd_value_numeric'].sum().reset_index()
    daily_values = daily_values.sort_values('date')
    
    # Calculate daily earnings (change from previous day)
    daily_values['daily_earnings'] = daily_values['usd_value_numeric'].diff()
    daily_values['daily_return_pct'] = (daily_values['daily_earnings'] / daily_values['usd_value_numeric'].shift(1)) * 100
    
    # Remove first row (no previous day to compare)
    daily_values = daily_values.dropna()
    
    return daily_values


def calculate_monthly_earnings(df, config):
    """Calculate monthly earnings summary"""
    df_processed, protocol_col = apply_earnings_combinations(df, config)
    
    # Add month-year column
    df_processed['month_year'] = df_processed['timestamp'].dt.to_period('M')
    
    monthly_data = []
    
    for month in df_processed['month_year'].unique():
        month_df = df_processed[df_processed['month_year'] == month]
        
        # Get first and last day values for the month
        month_timeline = month_df.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
        month_timeline = month_timeline.sort_values('timestamp')
        
        if len(month_timeline) >= 2:
            start_value = month_timeline['usd_value_numeric'].iloc[0]
            end_value = month_timeline['usd_value_numeric'].iloc[-1]
            
            monthly_earnings = end_value - start_value
            
            if start_value > 0:
                monthly_return = (monthly_earnings / start_value) * 100
            else:
                monthly_return = 0
            
            monthly_data.append({
                'Month': str(month),
                'Start Value ($)': start_value,
                'End Value ($)': end_value,
                'Monthly Earnings ($)': monthly_earnings,
                'Monthly Return (%)': monthly_return
            })
    
    return pd.DataFrame(monthly_data).sort_values('Month')


def create_protocol_earnings_chart(protocol_earnings_df):
    """Create protocol earnings visualization"""
    if protocol_earnings_df.empty:
        return None
    
    # Filter for meaningful earnings (positive or negative > $1)
    significant_earnings = protocol_earnings_df[
        abs(protocol_earnings_df['Absolute Earnings ($)']) >= 1
    ].head(15)
    
    fig = go.Figure()
    
    # Color code based on positive/negative earnings
    colors = ['green' if x >= 0 else 'red' for x in significant_earnings['Absolute Earnings ($)']]
    
    fig.add_trace(go.Bar(
        x=significant_earnings['Protocol'],
        y=significant_earnings['Absolute Earnings ($)'],
        marker_color=colors,
        text=significant_earnings['Absolute Earnings ($)'].apply(lambda x: f"${x:,.0f}"),
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>' +
                      'Earnings: $%{y:,.2f}<br>' +
                      '<extra></extra>'
    ))
    
    fig.update_layout(
        title="💰 Protocol Earnings Breakdown",
        xaxis_title="Protocol",
        yaxis_title="Absolute Earnings ($)",
        hovermode='x',
        height=500,
        xaxis={'categoryorder': 'total descending'}
    )
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    return fig


def create_daily_earnings_trend(daily_earnings_df):
    """Create daily earnings trend chart"""
    if daily_earnings_df.empty:
        return None
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Daily Portfolio Value', 'Daily Earnings'),
        vertical_spacing=0.1,
        row_heights=[0.6, 0.4]
    )
    
    # Portfolio value trend
    fig.add_trace(
        go.Scatter(
            x=daily_earnings_df['date'],
            y=daily_earnings_df['usd_value_numeric'],
            mode='lines+markers',
            name='Portfolio Value',
            line=dict(color='blue', width=2),
            hovertemplate='Date: %{x}<br>Value: $%{y:,.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Daily earnings bars
    colors = ['green' if x >= 0 else 'red' for x in daily_earnings_df['daily_earnings']]
    
    fig.add_trace(
        go.Bar(
            x=daily_earnings_df['date'],
            y=daily_earnings_df['daily_earnings'],
            marker_color=colors,
            name='Daily Earnings',
            hovertemplate='Date: %{x}<br>Earnings: $%{y:,.2f}<extra></extra>'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        title="📈 Daily Portfolio Performance & Earnings",
        height=600,
        hovermode='x unified',
        showlegend=True
    )
    
    fig.update_yaxes(title_text="Portfolio Value ($)", row=1, col=1)
    fig.update_yaxes(title_text="Daily Earnings ($)", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    
    return fig


def create_monthly_earnings_summary(monthly_earnings_df):
    """Create monthly earnings summary chart"""
    if monthly_earnings_df.empty:
        return None
    
    fig = go.Figure()
    
    # Color code based on positive/negative earnings
    colors = ['green' if x >= 0 else 'red' for x in monthly_earnings_df['Monthly Earnings ($)']]
    
    fig.add_trace(go.Bar(
        x=monthly_earnings_df['Month'],
        y=monthly_earnings_df['Monthly Earnings ($)'],
        marker_color=colors,
        text=monthly_earnings_df['Monthly Earnings ($)'].apply(lambda x: f"${x:,.0f}"),
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>' +
                      'Earnings: $%{y:,.2f}<br>' +
                      '<extra></extra>'
    ))
    
    fig.update_layout(
        title="📅 Monthly Earnings Summary",
        xaxis_title="Month",
        yaxis_title="Monthly Earnings ($)",
        height=400,
        hovermode='x'
    )
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    return fig


def create_earnings_composition_pie(protocol_earnings_df):
    """Create pie chart showing earnings composition"""
    if protocol_earnings_df.empty:
        return None
    
    # Filter for positive earnings only
    positive_earnings = protocol_earnings_df[protocol_earnings_df['Absolute Earnings ($)'] > 0]
    
    if positive_earnings.empty:
        return None
    
    fig = go.Figure(data=[go.Pie(
        labels=positive_earnings['Protocol'],
        values=positive_earnings['Absolute Earnings ($)'],
        hole=0.3,
        hovertemplate='<b>%{label}</b><br>' +
                      'Earnings: $%{value:,.2f}<br>' +
                      'Percentage: %{percent}<br>' +
                      '<extra></extra>'
    )])
    
    fig.update_layout(
        title="🥧 Positive Earnings Composition",
        height=400,
        showlegend=True
    )
    
    return fig


def create_cumulative_earnings_chart(df, config):
    """Create cumulative earnings over time"""
    df_processed, protocol_col = apply_earnings_combinations(df, config)
    
    # Calculate portfolio value over time
    timeline = df_processed.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
    timeline = timeline.sort_values('timestamp')
    
    if len(timeline) < 2:
        return None
    
    # Calculate cumulative earnings from initial investment
    initial_value = timeline['usd_value_numeric'].iloc[0]
    timeline['cumulative_earnings'] = timeline['usd_value_numeric'] - initial_value
    timeline['cumulative_return_pct'] = ((timeline['usd_value_numeric'] / initial_value) - 1) * 100
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Cumulative Earnings ($)', 'Cumulative Return (%)'),
        vertical_spacing=0.1
    )
    
    # Cumulative earnings in dollars
    fig.add_trace(
        go.Scatter(
            x=timeline['timestamp'],
            y=timeline['cumulative_earnings'],
            mode='lines',
            name='Cumulative Earnings',
            line=dict(color='green', width=3),
            fill='tonexty',
            hovertemplate='Date: %{x}<br>Cumulative Earnings: $%{y:,.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Cumulative return percentage
    fig.add_trace(
        go.Scatter(
            x=timeline['timestamp'],
            y=timeline['cumulative_return_pct'],
            mode='lines',
            name='Cumulative Return %',
            line=dict(color='blue', width=3),
            hovertemplate='Date: %{x}<br>Cumulative Return: %{y:.2f}%<extra></extra>'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        title="📊 Cumulative Earnings & Returns Over Time",
        height=500,
        hovermode='x unified'
    )
    
    fig.update_yaxes(title_text="Cumulative Earnings ($)", row=1, col=1)
    fig.update_yaxes(title_text="Cumulative Return (%)", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    
    # Add zero lines
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=1, col=1)
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)
    
    return fig


def display_earnings_summary_metrics(protocol_earnings_df, daily_earnings_df, period_days):
    """Display key earnings summary metrics"""
    if protocol_earnings_df.empty:
        st.warning("No earnings data available for the selected period.")
        return
    
    # Calculate summary metrics
    total_earnings = protocol_earnings_df['Absolute Earnings ($)'].sum()
    total_start_value = protocol_earnings_df['Start Value ($)'].sum()
    total_end_value = protocol_earnings_df['End Value ($)'].sum()
    
    if total_start_value > 0:
        total_return_pct = (total_earnings / total_start_value) * 100
        daily_avg_return = total_return_pct / period_days
    else:
        total_return_pct = 0
        daily_avg_return = 0
    
    # Count profitable vs unprofitable protocols
    profitable_protocols = len(protocol_earnings_df[protocol_earnings_df['Absolute Earnings ($)'] > 0])
    total_protocols = len(protocol_earnings_df)
    
    # Daily earnings statistics
    if not daily_earnings_df.empty:
        avg_daily_earnings = daily_earnings_df['daily_earnings'].mean()
        positive_days = len(daily_earnings_df[daily_earnings_df['daily_earnings'] > 0])
        total_days = len(daily_earnings_df)
        win_rate = (positive_days / total_days) * 100 if total_days > 0 else 0
    else:
        avg_daily_earnings = 0
        win_rate = 0
    
    st.subheader("📊 Earnings Summary")
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Earnings",
            f"${total_earnings:,.2f}",
            delta=f"{total_return_pct:+.2f}%"
        )
    
    with col2:
        st.metric(
            "Portfolio Value",
            f"${total_end_value:,.2f}",
            delta=f"${total_earnings:+,.2f}"
        )
    
    with col3:
        st.metric(
            "Average Daily Return",
            f"{daily_avg_return:+.3f}%",
            delta=f"${avg_daily_earnings:+,.2f}/day"
        )
    
    with col4:
        st.metric(
            "Win Rate",
            f"{win_rate:.1f}%",
            delta=f"{profitable_protocols}/{total_protocols} protocols profitable"
        )


def earnings_analysis_page():
    """Main earnings analysis page"""
    st.title("💰 Earnings Analysis Dashboard")
    st.markdown("Analyze your portfolio earnings by protocol, time period, and performance metrics")
    
    # Configuration Management
    with st.expander("⚙️ Configuration Settings", expanded=False):
        available_configs = get_available_configs()
        
        if available_configs:
            config_options = {config['file_name']: config for config in available_configs}
            
            selected_file = st.selectbox(
                "Select Configuration",
                options=list(config_options.keys()),
                format_func=lambda x: config_options[x]['display_name'],
                help="Choose configuration for protocol groupings"
            )
            
            config = load_selected_config(selected_file)
            st.success(f"✅ Using: {config.get('name', 'Unknown Configuration')}")
        else:
            st.info("No configurations found. Using default settings.")
            config = get_default_config()
    
    st.markdown("---")
    
    # Load historical data
    try:
        from utils import load_historical_data
        historical_df = load_historical_data()
    except ImportError:
        st.error("Unable to import load_historical_data function. Please ensure utils.py is available.")
        return
    
    if historical_df is None:
        st.warning("⚠️ Historical data not found. Please upload your data file.")
        uploaded_file = st.file_uploader("Upload historical data CSV", type=['csv'])
        
        if uploaded_file:
            historical_df = pd.read_csv(uploaded_file)
            # Ensure timestamp is datetime
            historical_df['timestamp'] = pd.to_datetime(historical_df['timestamp'])
        else:
            return
    
    # Ensure we have the required columns
    if 'usd_value_numeric' not in historical_df.columns:
        st.error("Missing 'usd_value_numeric' column in the data")
        return
    
    # Analysis Settings
    st.subheader("🔧 Analysis Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        analysis_period = st.selectbox(
            "Analysis Period",
            options=[7, 14, 30, 60, 90, 180],
            index=2,  # Default to 30 days
            format_func=lambda x: f"{x} days"
        )
    
    with col2:
        analysis_type = st.selectbox(
            "Analysis Focus",
            options=["overview", "protocol_detailed", "time_analysis", "composition"],
            format_func=lambda x: {
                "overview": "📊 Overview Dashboard",
                "protocol_detailed": "🏛️ Detailed Protocol Analysis", 
                "time_analysis": "📅 Time-based Analysis",
                "composition": "🥧 Earnings Composition"
            }[x]
        )
    
    st.markdown("---")
    
    # Calculate earnings data
    with st.spinner("Calculating earnings data..."):
        protocol_earnings_df = calculate_protocol_earnings(historical_df, config, analysis_period)
        daily_earnings_df = calculate_daily_earnings(historical_df, config)
        monthly_earnings_df = calculate_monthly_earnings(historical_df, config)
    
    # Display based on analysis type
    if analysis_type == "overview":
        # Summary metrics
        display_earnings_summary_metrics(protocol_earnings_df, daily_earnings_df, analysis_period)
        
        st.markdown("---")
        
        # Main charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Protocol earnings chart
            protocol_chart = create_protocol_earnings_chart(protocol_earnings_df)
            if protocol_chart:
                st.plotly_chart(protocol_chart, use_container_width=True)
        
        with col2:
            # Earnings composition pie
            composition_chart = create_earnings_composition_pie(protocol_earnings_df)
            if composition_chart:
                st.plotly_chart(composition_chart, use_container_width=True)
        
        # Cumulative earnings
        cumulative_chart = create_cumulative_earnings_chart(historical_df, config)
        if cumulative_chart:
            st.plotly_chart(cumulative_chart, use_container_width=True)
    
    elif analysis_type == "protocol_detailed":
        # Detailed protocol analysis
        st.subheader(f"🏛️ Protocol Earnings Details ({analysis_period} days)")
        
        # Protocol earnings table
        if not protocol_earnings_df.empty:
            # Format for display
            display_df = protocol_earnings_df.copy()
            display_df['Start Value ($)'] = display_df['Start Value ($)'].apply(lambda x: f"${x:,.2f}")
            display_df['End Value ($)'] = display_df['End Value ($)'].apply(lambda x: f"${x:,.2f}")
            display_df['Absolute Earnings ($)'] = display_df['Absolute Earnings ($)'].apply(lambda x: f"${x:+,.2f}")
            display_df['Percentage Return (%)'] = display_df['Percentage Return (%)'].apply(lambda x: f"{x:+.2f}%")
            display_df['Daily Rate (%)'] = display_df['Daily Rate (%)'].apply(lambda x: f"{x:+.3f}%")
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Protocol earnings chart
        protocol_chart = create_protocol_earnings_chart(protocol_earnings_df)
        if protocol_chart:
            st.plotly_chart(protocol_chart, use_container_width=True)
    
    elif analysis_type == "time_analysis":
        # Time-based analysis
        st.subheader("📅 Time-based Earnings Analysis")
        
        # Daily earnings trend
        daily_chart = create_daily_earnings_trend(daily_earnings_df)
        if daily_chart:
            st.plotly_chart(daily_chart, use_container_width=True)
        
        # Monthly summary
        monthly_chart = create_monthly_earnings_summary(monthly_earnings_df)
        if monthly_chart:
            st.plotly_chart(monthly_chart, use_container_width=True)
        
        # Monthly earnings table
        if not monthly_earnings_df.empty:
            st.subheader("📅 Monthly Earnings Summary")
            display_monthly_df = monthly_earnings_df.copy()
            display_monthly_df['Start Value ($)'] = display_monthly_df['Start Value ($)'].apply(lambda x: f"${x:,.2f}")
            display_monthly_df['End Value ($)'] = display_monthly_df['End Value ($)'].apply(lambda x: f"${x:,.2f}")
            display_monthly_df['Monthly Earnings ($)'] = display_monthly_df['Monthly Earnings ($)'].apply(lambda x: f"${x:+,.2f}")
            display_monthly_df['Monthly Return (%)'] = display_monthly_df['Monthly Return (%)'].apply(lambda x: f"{x:+.2f}%")
            
            st.dataframe(display_monthly_df, use_container_width=True, hide_index=True)
    
    elif analysis_type == "composition":
        # Composition analysis
        st.subheader("🥧 Earnings Composition Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Positive earnings composition
            composition_chart = create_earnings_composition_pie(protocol_earnings_df)
            if composition_chart:
                st.plotly_chart(composition_chart, use_container_width=True)
        
        with col2:
            # Protocol performance metrics
            st.subheader("📊 Protocol Performance Metrics")
            if not protocol_earnings_df.empty:
                # Best and worst performers
                best_performer = protocol_earnings_df.loc[protocol_earnings_df['Absolute Earnings ($)'].idxmax()]
                worst_performer = protocol_earnings_df.loc[protocol_earnings_df['Absolute Earnings ($)'].idxmin()]
                
                st.success(f"🏆 **Best Performer**: {best_performer['Protocol']}")
                st.write(f"Earnings: ${best_performer['Absolute Earnings ($)']:,.2f}")
                st.write(f"Return: {best_performer['Percentage Return (%)']:+.2f}%")
                
                st.error(f"📉 **Worst Performer**: {worst_performer['Protocol']}")
                st.write(f"Earnings: ${worst_performer['Absolute Earnings ($)']:,.2f}")
                st.write(f"Return: {worst_performer['Percentage Return (%)']:+.2f}%")
        
        # Cumulative earnings
        cumulative_chart = create_cumulative_earnings_chart(historical_df, config)
        if cumulative_chart:
            st.plotly_chart(cumulative_chart, use_container_width=True)


if __name__ == "__main__":
    earnings_analysis_page()
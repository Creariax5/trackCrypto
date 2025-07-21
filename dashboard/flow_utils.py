# dashboard/flow_utils.py
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import timedelta
import os

def load_flows_data():
    """Load the manual flows CSV file"""
    flows_file = "portfolio_data/manual_flows.csv"
    
    if not os.path.exists(flows_file):
        st.error(f"❌ Flows file not found: {flows_file}")
        st.info("💡 **Create the file with these columns:**")
        st.code("""protocol_token_name,token_inflow,usd_value_inflow,timestamp,transaction_type
USDC | Peapods Finance V2 (Lending),345,345,2025-06-26 14:45:00,deposit
BTC,-0.02,-456.3,2025-06-16 05:34:00,withdrawal""")
        return None
    
    try:
        flows_df = pd.read_csv(flows_file)
        flows_df['timestamp'] = pd.to_datetime(flows_df['timestamp'])
        
        # Validate required columns
        required_cols = ['protocol_token_name', 'token_inflow', 'usd_value_inflow', 'timestamp', 'transaction_type']
        missing_cols = [col for col in required_cols if col not in flows_df.columns]
        
        if missing_cols:
            st.error(f"❌ Missing required columns in flows file: {missing_cols}")
            return None
            
        return flows_df
        
    except Exception as e:
        st.error(f"❌ Error loading flows file: {e}")
        return None

def create_flows_management_ui():
    """Create UI for managing flows data"""
    st.subheader("💰 Capital Flows Management")
    
    flows_df = load_flows_data()
    
    if flows_df is None:
        # Show example and instructions
        if st.button("📝 Create Example Flows File"):
            create_example_flows_file()
            st.rerun()
        return None
    
    # Show flows summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_inflows = flows_df[flows_df['usd_value_inflow'] > 0]['usd_value_inflow'].sum()
        st.metric("Total Inflows", f"${total_inflows:,.2f}")
    
    with col2:
        total_outflows = abs(flows_df[flows_df['usd_value_inflow'] < 0]['usd_value_inflow'].sum())
        st.metric("Total Outflows", f"${total_outflows:,.2f}")
    
    with col3:
        net_flow = flows_df['usd_value_inflow'].sum()
        st.metric("Net Flow", f"${net_flow:,.2f}")
    
    with col4:
        flow_count = len(flows_df)
        st.metric("Total Transactions", flow_count)
    
    # Show recent flows
    with st.expander("📋 Recent Flows (Last 10)", expanded=False):
        recent_flows = flows_df.sort_values('timestamp', ascending=False).head(10)
        
        # Format for display
        display_flows = recent_flows.copy()
        display_flows['usd_value_inflow'] = display_flows['usd_value_inflow'].apply(lambda x: f"${x:+,.2f}")
        display_flows['token_inflow'] = display_flows['token_inflow'].apply(lambda x: f"{x:+,.6f}")
        display_flows['timestamp'] = display_flows['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(
            display_flows[['timestamp', 'protocol_token_name', 'token_inflow', 'usd_value_inflow', 'transaction_type']],
            use_container_width=True,
            hide_index=True
        )
    
    return flows_df

def create_example_flows_file():
    """Create an example flows file"""
    os.makedirs("portfolio_data", exist_ok=True)
    
    example_data = {
        'protocol_token_name': [
            'USDC | Peapods Finance V2 (Lending)',
            'BTC',
            'ETH | Compound V3 (Lending)',
            'USDC | Peapods Finance V2 (Lending)',
            'SILO | Silo (Rewards)'
        ],
        'token_inflow': [345, -0.02, 2.5, -100, 150],
        'usd_value_inflow': [345, -456.3, 4500, -100, 250],
        'timestamp': [
            '2025-06-26 14:45:00',
            '2025-06-16 05:34:00', 
            '2025-06-10 09:15:00',
            '2025-06-28 16:20:00',
            '2025-06-20 11:30:00'
        ],
        'transaction_type': ['deposit', 'withdrawal', 'deposit', 'withdrawal', 'reward_claim']
    }
    
    example_df = pd.DataFrame(example_data)
    example_df.to_csv("portfolio_data/manual_flows.csv", index=False)
    st.success("✅ Created example flows file: portfolio_data/manual_flows.csv")

def calculate_flows_for_period(flows_df, item_name, start_time, end_time):
    """Calculate total flows for a specific item during a time period"""
    if flows_df is None:
        return 0
    
    item_flows = flows_df[
        (flows_df['protocol_token_name'] == item_name) &
        (flows_df['timestamp'] >= start_time) &
        (flows_df['timestamp'] <= end_time)
    ]
    
    return item_flows['usd_value_inflow'].sum()

def calculate_flow_adjusted_performance(df, flows_df, config, selected_items, period_days, analysis_type):
    """Calculate flow-adjusted performance for selected items"""
    # Import locally to avoid circular imports
    from dashboard.performance_analysis import apply_asset_combinations
    
    df_processed, combined_col = apply_asset_combinations(df, config, analysis_type)
    
    current_time = df_processed['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    
    performance_data = []
    total_start_value = 0
    total_end_value = 0
    total_flows = 0
    
    for item in selected_items:
        if pd.isna(item):
            continue
            
        item_data = df_processed[df_processed[combined_col] == item]
        if len(item_data) == 0:
            continue
            
        # Group by timestamp and sum values
        item_timeline = item_data.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
        item_timeline = item_timeline.sort_values('timestamp')
        
        # Filter for period
        period_timeline = item_timeline[item_timeline['timestamp'] >= period_start]
        
        if len(period_timeline) >= 2:
            start_value = period_timeline['usd_value_numeric'].iloc[0]
            end_value = period_timeline['usd_value_numeric'].iloc[-1]
            
            # Calculate flows during this period
            period_flows = calculate_flows_for_period(flows_df, item, period_start, current_time)
            
            # Flow-adjusted performance calculation
            if start_value > 0:
                # True Performance = (End Value - Start Value - Total Flows) / Start Value
                raw_change = end_value - start_value
                flow_adjusted_change = raw_change - period_flows
                flow_adjusted_return = (flow_adjusted_change / start_value) * 100
                
                # Calculate APR (annualized)
                if flow_adjusted_change != 0:
                    flow_adjusted_apr = (((start_value + flow_adjusted_change) / start_value) ** (365 / period_days) - 1) * 100
                else:
                    flow_adjusted_apr = 0
            else:
                flow_adjusted_return = 0
                flow_adjusted_apr = 0
            
            # Raw performance (without flow adjustment)
            raw_return = ((end_value / start_value) - 1) * 100 if start_value > 0 else 0
            
            # Calculate dollar gain/loss
            flow_adjusted_dollar_gain = flow_adjusted_change
            
            performance_data.append({
                'Item': item,
                'Start Value ($)': start_value,
                'End Value ($)': end_value,
                'Period Flows ($)': period_flows,
                f'Raw {period_days}d Return (%)': raw_return,
                f'Flow-Adj {period_days}d Return (%)': flow_adjusted_return,
                'Flow-Adj APR (%)': flow_adjusted_apr,
                'Flow-Adj Gain/Loss ($)': flow_adjusted_dollar_gain
            })
            
            total_start_value += start_value
            total_end_value += end_value
            total_flows += period_flows
    
    # Calculate total portfolio flow-adjusted performance
    if total_start_value > 0:
        total_raw_return = ((total_end_value / total_start_value) - 1) * 100
        total_flow_adjusted_change = (total_end_value - total_start_value) - total_flows
        total_flow_adjusted_return = (total_flow_adjusted_change / total_start_value) * 100
        total_flow_adjusted_dollar_gain = total_flow_adjusted_change
        
        if total_flow_adjusted_change != 0:
            total_flow_adjusted_apr = (((total_start_value + total_flow_adjusted_change) / total_start_value) ** (365 / period_days) - 1) * 100
        else:
            total_flow_adjusted_apr = 0
    else:
        total_raw_return = 0
        total_flow_adjusted_return = 0
        total_flow_adjusted_apr = 0
        total_flow_adjusted_dollar_gain = 0
    
    return (performance_data, total_start_value, total_end_value, total_flows, 
            total_raw_return, total_flow_adjusted_return, total_flow_adjusted_apr, total_flow_adjusted_dollar_gain)

def create_flow_adjusted_performance_chart(df, flows_df, config, selected_items, period_days, analysis_type):
    """Create flow-adjusted performance comparison chart"""
    # Import locally to avoid circular imports
    from dashboard.performance_analysis import apply_asset_combinations
    
    if not selected_items:
        return None
    
    df_processed, combined_col = apply_asset_combinations(df, config, analysis_type)
    
    current_time = df_processed['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    filtered_df = df_processed[df_processed['timestamp'] >= period_start]
    
    performance_data = []
    
    for item in selected_items:
        if pd.isna(item):
            continue
            
        item_data = filtered_df[filtered_df[combined_col] == item]
        if len(item_data) == 0:
            continue
            
        # Group by timestamp and sum values
        item_timeline = item_data.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
        item_timeline = item_timeline.sort_values('timestamp')
        
        if len(item_timeline) >= 2:
            initial_value = item_timeline['usd_value_numeric'].iloc[0]
            
            for _, row in item_timeline.iterrows():
                # Calculate flows up to this point
                flows_to_date = calculate_flows_for_period(flows_df, item, period_start, row['timestamp'])
                
                if initial_value > 0:
                    # Flow-adjusted cumulative return
                    raw_change = row['usd_value_numeric'] - initial_value
                    flow_adjusted_change = raw_change - flows_to_date
                    flow_adjusted_return = (flow_adjusted_change / initial_value) * 100
                else:
                    flow_adjusted_return = 0
                    
                performance_data.append({
                    'timestamp': row['timestamp'],
                    'item': item,
                    'flow_adjusted_return': flow_adjusted_return
                })
    
    if not performance_data:
        return None
    
    perf_df = pd.DataFrame(performance_data)
    
    # Create the chart
    title_prefix = "💰" if analysis_type == "assets" else "🏛️"
    title_type = "Asset" if analysis_type == "assets" else "Protocol Position"
    
    fig = px.line(
        perf_df,
        x='timestamp',
        y='flow_adjusted_return',
        color='item',
        title=f"{title_prefix} Flow-Adjusted {title_type} Performance ({period_days} Days)",
        labels={'flow_adjusted_return': 'Flow-Adjusted Return (%)', 'timestamp': 'Date', 'item': title_type}
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

def create_flow_adjusted_summary_table(performance_data, total_start_value, total_end_value, total_flows, 
                                      total_raw_return, total_flow_adjusted_return, total_flow_adjusted_apr, 
                                      total_flow_adjusted_dollar_gain, period_days, analysis_type):
    """Create and display flow-adjusted performance summary table"""
    if not performance_data:
        st.warning("No performance data available for the selected items.")
        return
    
    # Create DataFrame
    perf_df = pd.DataFrame(performance_data)
    
    # Format the DataFrame for display
    perf_df_display = perf_df.copy()
    perf_df_display['Start Value ($)'] = perf_df_display['Start Value ($)'].apply(lambda x: f"${x:,.2f}")
    perf_df_display['End Value ($)'] = perf_df_display['End Value ($)'].apply(lambda x: f"${x:,.2f}")
    perf_df_display['Period Flows ($)'] = perf_df_display['Period Flows ($)'].apply(lambda x: f"${x:+,.2f}")
    perf_df_display[f'Raw {period_days}d Return (%)'] = perf_df_display[f'Raw {period_days}d Return (%)'].apply(lambda x: f"{x:+.2f}%")
    perf_df_display[f'Flow-Adj {period_days}d Return (%)'] = perf_df_display[f'Flow-Adj {period_days}d Return (%)'].apply(lambda x: f"{x:+.2f}%")
    perf_df_display['Flow-Adj APR (%)'] = perf_df_display['Flow-Adj APR (%)'].apply(lambda x: f"{x:+.2f}%")
    perf_df_display['Flow-Adj Gain/Loss ($)'] = perf_df_display['Flow-Adj Gain/Loss ($)'].apply(lambda x: f"${x:+,.2f}")
    
    # Display the table
    item_type = "Assets" if analysis_type == "assets" else "Protocol Positions"
    st.subheader(f"📊 Flow-Adjusted Performance Summary - {item_type}")
    
    st.dataframe(
        perf_df_display,
        use_container_width=True,
        hide_index=True
    )
    
    # Display total summary
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Start Value", f"${total_start_value:,.2f}")
    
    with col2:
        st.metric("End Value", f"${total_end_value:,.2f}")
    
    with col3:
        st.metric("Total Flows", f"${total_flows:+,.2f}")
    
    with col4:
        st.metric(f"Raw {period_days}d Return", f"{total_raw_return:+.2f}%")
    
    with col5:
        st.metric("Flow-Adj APR", f"{total_flow_adjusted_apr:+.2f}%")
    
    with col6:
        gain_loss_color = "normal" if total_flow_adjusted_dollar_gain == 0 else ("inverse" if total_flow_adjusted_dollar_gain < 0 else "normal")
        st.metric(
            "💰 Total Earned/Lost", 
            f"${total_flow_adjusted_dollar_gain:+,.2f}",
            help="Total flow-adjusted profit/loss in USD"
        )
    
    # Show comparison
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            f"Raw {period_days}d Return", 
            f"{total_raw_return:+.2f}%",
            help="Includes impact of your deposits/withdrawals"
        )
    
    with col2:
        st.metric(
            f"Flow-Adjusted {period_days}d Return", 
            f"{total_flow_adjusted_return:+.2f}%",
            help="True protocol performance excluding your capital flows"
        )
    
    # Key insights
    st.markdown("**📈 Key Insights:**")
    
    if performance_data:
        # Find best and worst flow-adjusted performers
        best_performer = max(performance_data, key=lambda x: x['Flow-Adj Gain/Loss ($)'])
        worst_performer = min(performance_data, key=lambda x: x['Flow-Adj Gain/Loss ($)'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"🏆 **Best Performer:** {best_performer['Item']}")
            st.write(f"• **Earned:** ${best_performer['Flow-Adj Gain/Loss ($)']:+,.2f}")
            st.write(f"• **APR:** {best_performer['Flow-Adj APR (%)']:+.2f}%")
        
        with col2:
            if worst_performer['Flow-Adj Gain/Loss ($)'] < 0:
                st.error(f"📉 **Worst Performer:** {worst_performer['Item']}")
                st.write(f"• **Lost:** ${worst_performer['Flow-Adj Gain/Loss ($)']:+,.2f}")
                st.write(f"• **APR:** {worst_performer['Flow-Adj APR (%)']:+.2f}%")
            else:
                st.info(f"📊 **Lowest Performer:** {worst_performer['Item']}")
                st.write(f"• **Earned:** ${worst_performer['Flow-Adj Gain/Loss ($)']:+,.2f}")
                st.write(f"• **APR:** {worst_performer['Flow-Adj APR (%)']:+.2f}%")
        
        # Show impact of flows
        flow_impact = total_raw_return - total_flow_adjusted_return
        if abs(flow_impact) > 0.1:  # Show if significant impact
            if flow_impact > 0:
                st.info(f"💰 **Flow Impact:** Your deposits boosted apparent returns by {flow_impact:+.2f}%")
            else:
                st.info(f"💸 **Flow Impact:** Your withdrawals reduced apparent returns by {abs(flow_impact):+.2f}%")
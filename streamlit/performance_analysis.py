import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import timedelta
import json
import os
import glob


def get_available_configs():
    """Get list of available configuration files from config folder"""
    config_folder = "config"
    
    # Create config folder if it doesn't exist
    if not os.path.exists(config_folder):
        os.makedirs(config_folder)
        st.info(f"📁 Created {config_folder} folder. Add your JSON configuration files there.")
        return []
    
    # Get all JSON files in config folder
    json_files = glob.glob(os.path.join(config_folder, "*.json"))
    
    configs = []
    for file_path in json_files:
        try:
            with open(file_path, 'r') as f:
                config_data = json.load(f)
                config_name = config_data.get('name', os.path.basename(file_path))
                config_description = config_data.get('description', 'No description available')
                
                configs.append({
                    'file_path': file_path,
                    'file_name': os.path.basename(file_path),
                    'display_name': config_name,
                    'description': config_description,
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
            st.error(f"Configuration file {selected_config_file} not found")
            return get_default_config()
            
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        return get_default_config()


def get_default_config():
    """Return default empty configuration"""
    return {
        "name": "Empty Configuration",
        "description": "No combinations or renames applied",
        "asset_combinations": {},
        "asset_renames": {},
        "protocol_combinations": {},
        "protocol_renames": {}
    }


def save_config_to_file(config_data, filename):
    """Save configuration data to a file in config folder"""
    config_folder = "config"
    
    # Create config folder if it doesn't exist
    if not os.path.exists(config_folder):
        os.makedirs(config_folder)
    
    file_path = os.path.join(config_folder, filename)
    
    try:
        with open(file_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving configuration: {e}")
        return False


def create_config_management_ui():
    """Create UI for managing configurations"""
    st.subheader("⚙️ Configuration Management")
    
    # Get available configurations
    available_configs = get_available_configs()
    
    if not available_configs:
        st.warning("📂 No configuration files found in the config folder.")
        st.info("💡 **Quick Start:** Create configuration files in the `config/` folder with .json extension")
        
        # Option to create a sample config
        if st.button("🔧 Create Sample Configuration Files"):
            # Create sample configurations
            sample_configs = [
                {
                    "filename": "default.json",
                    "data": {
                        "name": "Default Configuration",
                        "description": "Basic asset and protocol combinations",
                        "asset_combinations": {
                            "Stablecoins": ["USDC", "USDT", "DAI"],
                            "Ethereum Ecosystem": ["ETH", "WETH"]
                        },
                        "asset_renames": {
                            "BTC": "Bitcoin",
                            "ETH": "Ethereum"
                        },
                        "protocol_combinations": {
                            "Silo Combined": ["SILO | Silo (Rewards)", "USDC | Silo (Yield)"]
                        },
                        "protocol_renames": {}
                    }
                }
            ]
            
            success_count = 0
            for config in sample_configs:
                if save_config_to_file(config["data"], config["filename"]):
                    success_count += 1
            
            if success_count > 0:
                st.success(f"✅ Created {success_count} sample configuration file(s)")
                st.rerun()
            
        return None
    
    # Configuration selector
    config_options = {config['file_name']: config for config in available_configs}
    
    selected_file = st.selectbox(
        "📋 Select Configuration",
        options=list(config_options.keys()),
        format_func=lambda x: f"{config_options[x]['display_name']} ({x})",
        help="Choose which configuration to use for asset combinations and renames"
    )
    
    if selected_file:
        selected_config = config_options[selected_file]
        
        # Show configuration details
        st.info(f"**Description:** {selected_config['description']}")
        
        # Configuration preview
        with st.expander("👀 Preview Configuration", expanded=False):
            config_data = selected_config['data']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Asset Combinations:**")
                asset_combinations = config_data.get('asset_combinations', {})
                if asset_combinations:
                    for group_name, assets in asset_combinations.items():
                        st.write(f"• {group_name}: {', '.join(assets)}")
                else:
                    st.write("None")
                
                st.markdown("**Asset Renames:**")
                asset_renames = config_data.get('asset_renames', {})
                if asset_renames:
                    for old_name, new_name in asset_renames.items():
                        st.write(f"• {old_name} → {new_name}")
                else:
                    st.write("None")
            
            with col2:
                st.markdown("**Protocol Combinations:**")
                protocol_combinations = config_data.get('protocol_combinations', {})
                if protocol_combinations:
                    for group_name, protocols in protocol_combinations.items():
                        st.write(f"• {group_name}:")
                        for protocol in protocols:
                            st.write(f"  - {protocol}")
                else:
                    st.write("None")
                
                st.markdown("**Protocol Renames:**")
                protocol_renames = config_data.get('protocol_renames', {})
                if protocol_renames:
                    for old_name, new_name in protocol_renames.items():
                        st.write(f"• {old_name} → {new_name}")
                else:
                    st.write("None")
        
        return selected_file
    
    return None


def apply_asset_combinations(df, config, analysis_type):
    """Apply asset combinations and renames based on configuration"""
    df_processed = df.copy()
    
    if analysis_type == 'assets':
        combinations = config.get('asset_combinations', {})
        renames = config.get('asset_renames', {})
        item_col = 'coin'
        combined_col = 'combined_asset'
        
    else:  # protocol_positions
        # Filter out wallet positions first
        df_processed = df_processed[df_processed['protocol'] != 'Wallet'].copy()
        # Create protocol-asset identifier
        df_processed = create_protocol_asset_identifier(df_processed)
        combinations = config.get('protocol_combinations', {})
        renames = config.get('protocol_renames', {})
        item_col = 'protocol_asset'
        combined_col = 'combined_protocol_asset'
    
    # Initialize the combined column with original values
    df_processed[combined_col] = df_processed[item_col]
    
    # Apply combinations first (items in combinations will be grouped)
    items_in_combinations = set()
    for combined_name, items_to_combine in combinations.items():
        for item in items_to_combine:
            items_in_combinations.add(item)
            # Replace individual items with combined name
            df_processed.loc[df_processed[item_col] == item, combined_col] = combined_name
    
    # Apply renames to items NOT in combinations
    for original_name, new_name in renames.items():
        if original_name not in items_in_combinations:
            df_processed.loc[df_processed[item_col] == original_name, combined_col] = new_name
    
    return df_processed, combined_col


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


def get_top_items_by_value(df, config, analysis_type, top_n=10):
    """Get top N items by current portfolio value with combinations applied"""
    df_processed, combined_col = apply_asset_combinations(df, config, analysis_type)
    
    current_time = df_processed['timestamp'].max()
    current_data = df_processed[df_processed['timestamp'] == current_time]
    
    item_values = current_data.groupby(combined_col)['usd_value_numeric'].sum().sort_values(ascending=False)
    return item_values.head(top_n).index.tolist()


def get_top_performing_items(df, config, analysis_type, period_days=30, top_n=10):
    """Get top N performing items by return percentage with combinations applied"""
    df_processed, combined_col = apply_asset_combinations(df, config, analysis_type)
    
    current_time = df_processed['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    
    item_returns = []
    
    for item in df_processed[combined_col].unique():
        if pd.isna(item):
            continue
            
        item_data = df_processed[df_processed[combined_col] == item]
        
        # Current value
        current_data = item_data[item_data['timestamp'] == current_time]
        if len(current_data) == 0:
            continue
        current_value = current_data['usd_value_numeric'].sum()
        
        # Period start value
        period_data = item_data[item_data['timestamp'] >= period_start]
        if len(period_data) == 0:
            continue
            
        start_data = period_data.sort_values('timestamp').iloc[0]
        start_value = start_data['usd_value_numeric']
        
        if start_value > 0:
            return_pct = ((current_value - start_value) / start_value) * 100
            item_returns.append({
                'item': item, 
                'return': return_pct, 
                'current_value': current_value
            })
    
    # Sort by return and filter for items with meaningful value
    item_returns_df = pd.DataFrame(item_returns)
    if len(item_returns_df) > 0:
        min_value = 5 if analysis_type == 'protocol_positions' else 1
        filtered_returns = item_returns_df[item_returns_df['current_value'] > min_value]
        top_performers = filtered_returns.sort_values('return', ascending=False).head(top_n)
        return top_performers['item'].tolist()
    
    return []


def calculate_apr_data_with_combinations(df, config, selected_items, period_days, analysis_type):
    """Calculate APR and summary data for selected items with combinations applied"""
    df_processed, combined_col = apply_asset_combinations(df, config, analysis_type)
    
    current_time = df_processed['timestamp'].max()
    period_start = current_time - timedelta(days=period_days)
    filtered_df = df_processed[df_processed['timestamp'] >= period_start]
    
    apr_data = []
    total_start_value = 0
    total_end_value = 0
    
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


def create_performance_comparison_with_combinations(df, config, selected_items, period_days, analysis_type):
    """Create performance comparison chart with combinations applied"""
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
                if initial_value > 0:
                    cumulative_return = ((row['usd_value_numeric'] / initial_value) - 1) * 100
                else:
                    cumulative_return = 0
                    
                performance_data.append({
                    'timestamp': row['timestamp'],
                    'item': item,
                    'cumulative_return': cumulative_return
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
        y='cumulative_return',
        color='item',
        title=f"{title_prefix} {title_type} Performance Comparison ({period_days} Days)",
        labels={'cumulative_return': 'Cumulative Return (%)', 'timestamp': 'Date', 'item': title_type}
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


def simplified_performance_analysis(historical_df, selected_config_file):
    """Simplified performance analysis with asset and protocol-asset comparison and combinations"""
    
    # Load configuration
    if selected_config_file:
        config = load_selected_config(selected_config_file)
        st.success(f"✅ Using configuration: {config.get('name', selected_config_file)}")
    else:
        config = get_default_config()
        st.info("ℹ️ Using default configuration (no combinations)")
    
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
    
    # Protocol Position specific logic
    if analysis_type == "protocol_positions":
        # Check if protocol data exists
        if 'protocol' not in historical_df.columns:
            st.error("❌ Protocol data not found in the dataset. Please ensure your data includes protocol information.")
            return
        
        # Filter out wallet positions and create protocol-asset combinations
        df_no_wallet = historical_df[historical_df['protocol'] != 'Wallet'].copy()
        
        if len(df_no_wallet) == 0:
            st.error("❌ No protocol positions found in the dataset. Only wallet positions available.")
            return
    
    with col2:
        selection_method = st.selectbox(
            f"Show {analysis_type.replace('_', ' ').title()}",
            options=["top_value", "top_performers", "custom"],
            format_func=lambda x: {
                "top_value": "🏆 Top 10 by Portfolio Value", 
                "top_performers": "🚀 Top 10 Best Performers",
                "custom": "🎯 Custom Selection"
            }[x]
        )
    
    # Get selected items based on method
    if selection_method == "top_value":
        selected_items = get_top_items_by_value(historical_df, config, analysis_type, 10)
        st.info(f"Showing top 10 {analysis_type.replace('_', ' ')} by current portfolio value")
        
    elif selection_method == "top_performers":
        selected_items = get_top_performing_items(historical_df, config, analysis_type, analysis_period, 10)
        st.info(f"Showing top 10 best performing {analysis_type.replace('_', ' ')} over {analysis_period} days")
        
    else:  # custom
        # Get available items with combinations applied
        df_processed, combined_col = apply_asset_combinations(historical_df, config, analysis_type)
        available_items = sorted(df_processed[combined_col].dropna().unique())
        
        selected_items = st.multiselect(
            f"Select {analysis_type.replace('_', ' ')}:",
            options=available_items,
            default=available_items[:5] if len(available_items) >= 5 else available_items,
            help="Items are shown with combinations and renames applied based on selected configuration"
        )
    
    # Create chart
    if selected_items:
        chart = create_performance_comparison_with_combinations(
            historical_df, config, selected_items, analysis_period, analysis_type
        )
        
        if chart:
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.warning("No data available for the selected items and period.")
            
        # Add APR Summary Table after the chart
        st.markdown("---")
        
        # Calculate APR data
        apr_data, total_start_value, total_end_value, total_period_return, total_apr = calculate_apr_data_with_combinations(
            historical_df, config, selected_items, analysis_period, analysis_type
        )
        
        # Display APR summary table
        create_apr_summary_table(
            apr_data, total_start_value, total_end_value, 
            total_period_return, total_apr, analysis_period, analysis_type
        )
    else:
        st.warning("No items selected or available for analysis.")


# Main function to integrate into your app
def performance_analysis_page():
    """Main performance analysis page with config folder management"""
    st.title("📊 Portfolio Performance Analysis")
    
    # Configuration Management Section
    with st.expander("⚙️ Configuration Management", expanded=True):
        selected_config_file = create_config_management_ui()
        
        if selected_config_file:
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🔄 Reload Config"):
                    st.rerun()
    
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

    # Run simplified performance analysis with configurations
    simplified_performance_analysis(historical_df, selected_config_file)


# If running as standalone
if __name__ == "__main__":
    performance_analysis_page()
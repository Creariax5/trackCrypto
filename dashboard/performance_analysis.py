# dashboard/performance_analysis.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import timedelta
import json
import os
import glob

# Import from existing modules
from core.config_manager import ConfigManager
from dashboard.utils import load_historical_data
from dashboard.flow_utils import (
    load_flows_data, 
    create_flows_management_ui,
    calculate_flow_adjusted_performance,
    create_flow_adjusted_performance_chart,
    create_flow_adjusted_summary_table
)

def get_available_configs():
    """Get list of available configuration files from config folder"""
    config_folder = "config/streamlit"
    
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
        config_folder = "config/streamlit"
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
    config_folder = "config/streamlit"
    
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
        st.info("💡 **Quick Start:** Create configuration files in the `config/streamlit/` folder with .json extension")
        
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

def flow_adjusted_performance_analysis(historical_df, flows_df, selected_config_file):
    """Main flow-adjusted performance analysis with asset and protocol comparison"""
    
    # Load configuration
    if selected_config_file:
        config = load_selected_config(selected_config_file)
        st.success(f"✅ Using configuration: {config.get('name', selected_config_file)}")
    else:
        config = get_default_config()
        st.info("ℹ️ Using default configuration (no combinations)")
    
    st.header("📊 Flow-Adjusted Performance Analysis")
    
    # Show flows status
    if flows_df is not None:
        st.success(f"✅ Loaded {len(flows_df)} capital flow transactions")
    else:
        st.warning("⚠️ No capital flows data loaded - performance will be calculated without flow adjustments")
        st.info("💡 Create `portfolio_data/manual_flows.csv` to enable true performance tracking")
    
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
            options=["top_value", "custom"],
            format_func=lambda x: {
                "top_value": "🏆 Top 10 by Portfolio Value", 
                "custom": "🎯 Custom Selection"
            }[x]
        )
    
    # Get selected items based on method
    if selection_method == "top_value":
        selected_items = get_top_items_by_value(historical_df, config, analysis_type, 5)
        st.info(f"Showing top 10 {analysis_type.replace('_', ' ')} by current portfolio value")
        
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
    
    # Create flow-adjusted analysis
    if selected_items:
        # Calculate flow-adjusted performance
        (performance_data, total_start_value, total_end_value, total_flows, 
         total_raw_return, total_flow_adjusted_return, total_flow_adjusted_apr, 
         total_flow_adjusted_dollar_gain) = calculate_flow_adjusted_performance(
            historical_df, flows_df, config, selected_items, analysis_period, analysis_type
        )
        
        # Create and display the chart
        chart = create_flow_adjusted_performance_chart(
            historical_df, flows_df, config, selected_items, analysis_period, analysis_type
        )
        
        if chart:
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.warning("No data available for the selected items and period.")
        
        # Display performance summary table
        st.markdown("---")
        create_flow_adjusted_summary_table(
            performance_data, total_start_value, total_end_value, total_flows,
            total_raw_return, total_flow_adjusted_return, total_flow_adjusted_apr,
            total_flow_adjusted_dollar_gain, analysis_period, analysis_type
        )
        
        # Additional flow insights
        if flows_df is not None and total_flows != 0:
            st.markdown("---")
            st.subheader("💰 Flow Analysis")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                flow_impact = total_raw_return - total_flow_adjusted_return
                st.metric(
                    "Flow Impact on Returns",
                    f"{flow_impact:+.2f}%",
                    help="Difference between raw returns and flow-adjusted returns"
                )
            
            with col2:
                if total_start_value > 0:
                    flow_percentage = (abs(total_flows) / total_start_value) * 100
                    st.metric(
                        "Flow Size vs Portfolio",
                        f"{flow_percentage:.1f}%",
                        help="Size of flows relative to starting portfolio value"
                    )
            
            with col3:
                flow_type = "Net Deposits" if total_flows > 0 else "Net Withdrawals"
                st.metric(
                    "Flow Type",
                    flow_type,
                    help="Whether you added or removed capital overall"
                )
        
    else:
        st.warning("No items selected or available for analysis.")

def performance_analysis_page():
    """Main performance analysis page with flow-adjusted calculations"""
    st.title("📊 Flow-Adjusted Portfolio Performance Analysis")
    
    # Configuration Management Section
    with st.expander("⚙️ Configuration Management", expanded=False):
        selected_config_file = create_config_management_ui()
        
        if selected_config_file:
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🔄 Reload Config"):
                    st.rerun()
    
    # Capital Flows Management Section
    with st.expander("💰 Capital Flows Management", expanded=True):
        flows_df = create_flows_management_ui()
    
    st.markdown("---")

    # Load historical data using existing utility
    historical_df = load_historical_data()

    if historical_df is None:
        st.warning("⚠️ Historical data file not found. Please run the portfolio tracker first.")
        
        # Option to upload file manually
        uploaded_file = st.file_uploader("Upload historical data CSV file", type=['csv'])
        
        if uploaded_file:
            historical_df = pd.read_csv(uploaded_file)
            # Convert timestamp column
            if 'timestamp' in historical_df.columns:
                historical_df['timestamp'] = pd.to_datetime(historical_df['timestamp'])
            
            # Ensure numeric columns
            if 'usd_value_numeric' not in historical_df.columns and 'usd_value' in historical_df.columns:
                historical_df['usd_value_numeric'] = pd.to_numeric(
                    historical_df['usd_value'].astype(str).str.replace('$', '').str.replace(',', ''), 
                    errors='coerce'
                )
            
        if historical_df is None:
            return

    # Show data summary
    if historical_df is not None:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Records", f"{len(historical_df):,}")
        
        with col2:
            date_range = historical_df['timestamp'].max() - historical_df['timestamp'].min()
            st.metric("Data Range", f"{date_range.days} days")
        
        with col3:
            unique_assets = historical_df['coin'].nunique()
            st.metric("Unique Assets", unique_assets)
        
        with col4:
            if 'protocol' in historical_df.columns:
                unique_protocols = historical_df['protocol'].nunique()
                st.metric("Unique Protocols", unique_protocols)
    
    # Run flow-adjusted performance analysis
    if historical_df is not None:
        flow_adjusted_performance_analysis(historical_df, flows_df, selected_config_file)

# If running as standalone
if __name__ == "__main__":
    performance_analysis_page()
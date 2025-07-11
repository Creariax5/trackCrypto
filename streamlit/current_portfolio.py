import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from utils import load_and_process_data, load_historical_data
import json
import os
import glob


# Configuration Management Functions (imported from performance_analysis.py)
def get_available_configs():
    """Get list of available configuration files from config folder"""
    config_folder = "config/streamlit"
    
    # Create config folder if it doesn't exist
    if not os.path.exists(config_folder):
        os.makedirs(config_folder)
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
            return get_default_config()
            
    except Exception as e:
        return get_default_config()


def get_default_config():
    """Return default empty configuration"""
    return {
        "name": "Default Configuration",
        "description": "No combinations or renames applied",
        "asset_combinations": {},
        "asset_renames": {},
        "protocol_combinations": {},
        "protocol_renames": {}
    }


def create_config_management_ui():
    """Create UI for managing configurations"""
    # Get available configurations
    available_configs = get_available_configs()
    
    if not available_configs:
        st.info("📂 No configuration files found. Create .json files in the `config/` folder to enable asset grouping.")
        return None
    
    # Configuration selector
    config_options = {config['file_name']: config for config in available_configs}
    
    selected_file = st.selectbox(
        "📋 Select Configuration for Asset Grouping",
        options=['None'] + list(config_options.keys()),
        format_func=lambda x: "No Grouping" if x == 'None' else f"{config_options[x]['display_name']} ({x})" if x != 'None' else x,
        help="Choose which configuration to use for grouping tokens in charts",
        key="portfolio_config_selector"
    )
    
    if selected_file and selected_file != 'None':
        selected_config = config_options[selected_file]
        
        # Show configuration details
        with st.expander("👀 Configuration Preview", expanded=False):
            config_data = selected_config['data']
            st.markdown(f"**{selected_config['display_name']}**: {selected_config['description']}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Asset Combinations:**")
                asset_combinations = config_data.get('asset_combinations', {})
                if asset_combinations:
                    for group_name, assets in asset_combinations.items():
                        st.write(f"• {group_name}: {', '.join(assets)}")
                else:
                    st.write("None")
            
            with col2:
                st.markdown("**Asset Renames:**")
                asset_renames = config_data.get('asset_renames', {})
                if asset_renames:
                    for old_name, new_name in asset_renames.items():
                        st.write(f"• {old_name} → {new_name}")
                else:
                    st.write("None")
        
        return selected_file
    
    return None


def apply_asset_combinations(df, config):
    """Apply asset combinations and renames based on configuration"""
    if not config:
        return df, 'coin'
    
    df_processed = df.copy()
    combinations = config.get('asset_combinations', {})
    renames = config.get('asset_renames', {})
    
    # Initialize the combined column with original values
    df_processed['combined_asset'] = df_processed['coin']
    
    # Apply combinations first (items in combinations will be grouped)
    items_in_combinations = set()
    for combined_name, items_to_combine in combinations.items():
        for item in items_to_combine:
            items_in_combinations.add(item)
            # Replace individual items with combined name
            df_processed.loc[df_processed['coin'] == item, 'combined_asset'] = combined_name
    
    # Apply renames to items NOT in combinations
    for original_name, new_name in renames.items():
        if original_name not in items_in_combinations:
            df_processed.loc[df_processed['coin'] == original_name, 'combined_asset'] = new_name
    
    return df_processed, 'combined_asset'


def filter_data_by_date(df, selected_date):
    """Filter historical data for a specific date"""
    try:
        if df is None or len(df) == 0:
            return None
        
        # Extract date only for filtering
        df['date_only'] = df['timestamp'].dt.date
        
        # Filter by selected date
        filtered_df = df[df['date_only'] == selected_date]
        
        if len(filtered_df) == 0:
            return None
        
        # If multiple entries for the same date, take the latest timestamp
        latest_timestamp = filtered_df['timestamp'].max()
        final_df = filtered_df[filtered_df['timestamp'] == latest_timestamp].copy()
        
        # Remove the temporary date_only column
        final_df = final_df.drop('date_only', axis=1)
        
        return final_df
        
    except Exception as e:
        st.error(f"❌ Error filtering data by date: {str(e)}")
        return None


def create_overview_metrics(df):
    """Create overview metrics cards"""
    total_value = df['usd_value_numeric'].sum()
    total_wallets = df['wallet_label'].nunique()
    total_tokens = df['coin'].nunique()
    total_protocols = df['protocol'].nunique()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Portfolio Value",
            value=f"${total_value:,.2f}",
            delta=None
        )

    with col2:
        st.metric(
            label="Number of Wallets",
            value=f"{total_wallets}",
            delta=None
        )

    with col3:
        st.metric(
            label="Unique Tokens",
            value=f"{total_tokens}",
            delta=None
        )

    with col4:
        st.metric(
            label="Protocols/Platforms",
            value=f"{total_protocols}",
            delta=None
        )


def create_wallet_breakdown_chart(df, min_wallet_value=0):
    """Create wallet breakdown pie chart with minimum value filter"""
    wallet_totals = df.groupby('wallet_label')['usd_value_numeric'].sum().reset_index()
    
    # Apply minimum value filter
    wallet_totals = wallet_totals[wallet_totals['usd_value_numeric'] >= min_wallet_value]
    wallet_totals = wallet_totals.sort_values('usd_value_numeric', ascending=False)

    if len(wallet_totals) == 0:
        st.warning(f"No wallets found with value >= ${min_wallet_value:,.2f}")
        return None

    fig = px.pie(
        wallet_totals,
        values='usd_value_numeric',
        names='wallet_label',
        title=f"Portfolio Distribution by Wallet (Min: ${min_wallet_value:,.0f})",
        hover_data=['usd_value_numeric'],
        labels={'usd_value_numeric': 'USD Value'}
    )

    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>'
    )

    return fig


def create_blockchain_breakdown_chart(df):
    """Create blockchain breakdown chart"""
    blockchain_totals = df.groupby('blockchain')['usd_value_numeric'].sum().reset_index()
    blockchain_totals = blockchain_totals.sort_values('usd_value_numeric', ascending=False)

    fig = px.bar(
        blockchain_totals,
        x='blockchain',
        y='usd_value_numeric',
        title="Asset Distribution by Blockchain",
        labels={'usd_value_numeric': 'USD Value', 'blockchain': 'Blockchain'},
        color='usd_value_numeric',
        color_continuous_scale='viridis'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False
    )

    return fig


def create_top_holdings_chart(df, config=None, top_n=10):
    """Create top holdings chart with optional asset combinations"""
    # Apply configuration if provided
    if config:
        df_processed, asset_col = apply_asset_combinations(df, config)
        title_suffix = " (Grouped by Config)"
    else:
        df_processed = df.copy()
        asset_col = 'coin'
        title_suffix = ""
    
    # Group by the appropriate asset column
    if asset_col == 'combined_asset':
        # For combined assets, we need to aggregate across the combined groups
        token_totals = df_processed.groupby('combined_asset')['usd_value_numeric'].sum().reset_index()
        token_totals = token_totals.sort_values('usd_value_numeric', ascending=False).head(top_n)
        token_totals['display_name'] = token_totals['combined_asset']
    else:
        # Original behavior for individual tokens
        token_totals = df_processed.groupby(['coin', 'token_name'])['usd_value_numeric'].sum().reset_index()
        token_totals = token_totals.sort_values('usd_value_numeric', ascending=False).head(top_n)
        # Create display name combining symbol and name
        token_totals['display_name'] = token_totals['coin'] + ' (' + token_totals['token_name'] + ')'

    fig = px.bar(
        token_totals,
        x='usd_value_numeric',
        y='display_name',
        orientation='h',
        title=f"Top {top_n} Token Holdings by Value{title_suffix}",
        labels={'usd_value_numeric': 'USD Value', 'display_name': 'Token'},
        color='usd_value_numeric',
        color_continuous_scale='plasma'
    )

    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        showlegend=False
    )

    return fig


def create_protocol_breakdown_chart(df):
    """Create protocol breakdown chart"""
    protocol_totals = df.groupby('protocol')['usd_value_numeric'].sum().reset_index()
    protocol_totals = protocol_totals.sort_values('usd_value_numeric', ascending=False).head(15)

    fig = px.treemap(
        protocol_totals,
        path=['protocol'],
        values='usd_value_numeric',
        title="Asset Distribution by Protocol/Platform",
        color='usd_value_numeric',
        color_continuous_scale='blues'
    )

    return fig


def create_wallet_comparison_chart(df, config=None):
    """Create wallet comparison chart showing top tokens per wallet with optional grouping"""
    # Apply configuration if provided
    if config:
        df_processed, asset_col = apply_asset_combinations(df, config)
    else:
        df_processed = df.copy()
        asset_col = 'coin'
    
    # Get top 5 assets per wallet by value
    wallet_tokens = []
    for wallet in df_processed['wallet_label'].unique():
        wallet_data = df_processed[df_processed['wallet_label'] == wallet]
        
        if asset_col == 'combined_asset':
            top_tokens = wallet_data.groupby('combined_asset')['usd_value_numeric'].sum().reset_index()
            top_tokens = top_tokens.sort_values('usd_value_numeric', ascending=False).head(5)
            top_tokens['asset'] = top_tokens['combined_asset']
        else:
            top_tokens = wallet_data.groupby('coin')['usd_value_numeric'].sum().reset_index()
            top_tokens = top_tokens.sort_values('usd_value_numeric', ascending=False).head(5)
            top_tokens['asset'] = top_tokens['coin']
        
        top_tokens['wallet_label'] = wallet
        wallet_tokens.append(top_tokens)

    combined_data = pd.concat(wallet_tokens, ignore_index=True)

    title_suffix = " (Grouped by Config)" if config else ""
    fig = px.bar(
        combined_data,
        x='wallet_label',
        y='usd_value_numeric',
        color='asset',
        title=f"Top Token Holdings by Wallet{title_suffix}",
        labels={'usd_value_numeric': 'USD Value', 'wallet_label': 'Wallet'},
        barmode='stack'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def create_detailed_table(df):
    """Create detailed holdings table with search and filter"""
    st.subheader("📋 Detailed Holdings")

    # Create filters
    col1, col2, col3 = st.columns(3)

    with col1:
        wallet_filter = st.selectbox(
            "Filter by Wallet",
            options=['All'] + list(df['wallet_label'].unique()),
            key="wallet_filter"
        )

    with col2:
        blockchain_filter = st.selectbox(
            "Filter by Blockchain",
            options=['All'] + list(df['blockchain'].unique()),
            key="blockchain_filter"
        )

    with col3:
        min_value = st.number_input(
            "Minimum USD Value",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="min_value_filter"
        )

    # Apply filters
    filtered_df = df.copy()

    if wallet_filter != 'All':
        filtered_df = filtered_df[filtered_df['wallet_label'] == wallet_filter]

    if blockchain_filter != 'All':
        filtered_df = filtered_df[filtered_df['blockchain'] == blockchain_filter]

    filtered_df = filtered_df[filtered_df['usd_value_numeric'] >= min_value]

    # Sort by USD value descending
    filtered_df = filtered_df.sort_values('usd_value_numeric', ascending=False)

    # Display table with selected columns
    display_columns = [
        'wallet_label', 'blockchain', 'coin', 'token_name',
        'protocol', 'amount', 'price', 'usd_value'
    ]

    # Only show columns that exist in the dataframe
    available_columns = [col for col in display_columns if col in filtered_df.columns]

    st.dataframe(
        filtered_df[available_columns],
        use_container_width=True,
        hide_index=True
    )

    # Show summary of filtered data
    st.info(f"Showing {len(filtered_df)} positions with total value: ${filtered_df['usd_value_numeric'].sum():,.2f}")


def current_portfolio_page():
    """Current portfolio analysis page with date selection and configuration management"""
    st.title("💰 Crypto Portfolio Dashboard")
    st.markdown("---")

    # Configuration Management Section
    with st.expander("⚙️ Asset Grouping Configuration", expanded=False):
        selected_config_file = create_config_management_ui()
        
        # Load configuration
        if selected_config_file:
            config = load_selected_config(selected_config_file)
        else:
            config = None

    # Sidebar for controls
    st.sidebar.header("📅 Date Selection")
    
    # Date picker with default to today
    selected_date = st.sidebar.date_input(
        "Select Portfolio Date",
        value=date.today(),
        help="Choose the date for which you want to view portfolio data",
        key="portfolio_date_picker"
    )

    # Display selected date info
    st.sidebar.info(f"Selected Date: {selected_date.strftime('%B %d, %Y')}")

    # Wallet filtering options
    st.sidebar.header("💰 Wallet Filtering")
    min_wallet_value = st.sidebar.number_input(
        "Minimum Wallet Value ($)",
        min_value=0,
        value=0,
        step=10,
        help="Hide wallets with value below this amount",
        key="min_wallet_value"
    )

    # Load historical data using utils function
    with st.spinner(f"Loading portfolio data for {selected_date}..."):
        # Load all historical data using utils function
        full_df = load_historical_data()
        
        # Filter for the selected date
        df = filter_data_by_date(full_df, selected_date) if full_df is not None else None

    if df is not None:
        st.success(f"✅ Successfully loaded {len(df)} portfolio positions for {selected_date}")

        # Show data timestamp info
        if 'timestamp' in df.columns:
            latest_timestamp = df['timestamp'].max()
            st.info(f"📊 Data timestamp: {latest_timestamp}")

        # Show configuration status
        if config:
            st.success(f"🔧 Using configuration: {config.get('name', 'Custom Config')}")

        # Overview metrics
        st.header("📊 Portfolio Overview")
        create_overview_metrics(df)
        st.markdown("---")

        # Charts section
        st.header("📈 Portfolio Analysis")

        # Row 1: Wallet and Blockchain breakdown
        col1, col2 = st.columns(2)

        with col1:
            wallet_fig = create_wallet_breakdown_chart(df, min_wallet_value)
            if wallet_fig:
                st.plotly_chart(wallet_fig, use_container_width=True)

        with col2:
            blockchain_fig = create_blockchain_breakdown_chart(df)
            st.plotly_chart(blockchain_fig, use_container_width=True)

        # Row 2: Top holdings and Protocol breakdown
        col1, col2 = st.columns(2)

        with col1:
            holdings_fig = create_top_holdings_chart(df, config)
            st.plotly_chart(holdings_fig, use_container_width=True)

        with col2:
            protocol_fig = create_protocol_breakdown_chart(df)
            st.plotly_chart(protocol_fig, use_container_width=True)

        # Row 3: Wallet comparison
        st.subheader("🔍 Wallet Comparison")
        wallet_comparison_fig = create_wallet_comparison_chart(df, config)
        st.plotly_chart(wallet_comparison_fig, use_container_width=True)

        st.markdown("---")

        # Detailed table
        create_detailed_table(df)

        # Additional insights in sidebar
        st.sidebar.markdown("---")
        st.sidebar.header("📈 Quick Insights")

        # Filter wallets for insights based on minimum value
        insights_df = df.copy()
        if min_wallet_value > 0:
            wallet_values = insights_df.groupby('wallet_label')['usd_value_numeric'].sum()
            valid_wallets = wallet_values[wallet_values >= min_wallet_value].index
            insights_df = insights_df[insights_df['wallet_label'].isin(valid_wallets)]

        if len(insights_df) > 0:
            # Top wallet by value
            top_wallet = insights_df.groupby('wallet_label')['usd_value_numeric'].sum().idxmax()
            top_wallet_value = insights_df.groupby('wallet_label')['usd_value_numeric'].sum().max()
            st.sidebar.metric(
                "Top Wallet",
                top_wallet,
                f"${top_wallet_value:,.2f}"
            )

            # Most valuable token
            top_token = insights_df.groupby('coin')['usd_value_numeric'].sum().idxmax()
            top_token_value = insights_df.groupby('coin')['usd_value_numeric'].sum().max()
            st.sidebar.metric(
                "Top Token",
                top_token,
                f"${top_token_value:,.2f}"
            )

            # Most used blockchain
            top_blockchain = insights_df.groupby('blockchain')['usd_value_numeric'].sum().idxmax()
            top_blockchain_value = insights_df.groupby('blockchain')['usd_value_numeric'].sum().max()
            st.sidebar.metric(
                "Top Blockchain",
                top_blockchain,
                f"${top_blockchain_value:,.2f}"
            )
        else:
            st.sidebar.warning("No wallets meet the minimum value criteria")

        # Available date range info
        st.sidebar.markdown("---")
        st.sidebar.header("📊 Data Info")
        st.sidebar.write(f"Records loaded: {len(df)}")
        if 'timestamp' in df.columns:
            st.sidebar.write(f"Latest update: {df['timestamp'].max()}")
        
        # Show filtering effects
        if min_wallet_value > 0:
            filtered_wallets = len(insights_df['wallet_label'].unique())
            total_wallets = len(df['wallet_label'].unique())
            st.sidebar.write(f"Displayed wallets: {filtered_wallets}/{total_wallets}")
        
        # Show available date range from full dataset
        if full_df is not None and len(full_df) > 0:
            min_date = full_df['timestamp'].min().date()
            max_date = full_df['timestamp'].max().date()
            available_dates = len(full_df['timestamp'].dt.date.unique())
            st.sidebar.write(f"Available range: {min_date} to {max_date}")
            st.sidebar.write(f"Total dates: {available_dates}")

    else:
        st.warning(f"⚠️ No portfolio data found for {selected_date}")
        
        # Show data requirements
        st.subheader("📋 Data Requirements")
        st.write("To use this dashboard, ensure you have:")
        
        st.markdown("""
        1. **ALL_PORTFOLIOS_HISTORY.csv** file in the `portfolio_data/` directory
        2. The file should contain columns like:
           - `source_file_timestamp` (for date filtering)
           - `wallet_label` (wallet identifier)
           - `blockchain` (blockchain name)
           - `coin` (token symbol)
           - `protocol` (protocol/platform name)
           - `amount` (token amount)
           - `price` (token price)
           - `usd_value` (USD value)
           - `token_name` (full token name)
        3. Data for the selected date exists in the file
        """)
        
        # Suggest trying different dates
        st.info("💡 Try selecting a different date or check if your historical data file contains records for the selected date.")

        # Show available date range if we have partial data
        if full_df is not None and len(full_df) > 0:
            min_date = full_df['timestamp'].min().date()
            max_date = full_df['timestamp'].max().date()
            st.info(f"📅 Available data range: {min_date} to {max_date}")
            
            # Show sample of available dates
            available_dates = full_df['timestamp'].dt.date.unique()
            st.write(f"Total dates with data: {len(available_dates)}")
        else:
            st.error("❌ Could not load any historical data. Please check if the file exists in the correct location.")

    # Quick date navigation
    st.sidebar.markdown("---")
    st.sidebar.header("⚡ Quick Navigation")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Yesterday", key="yesterday_btn"):
            # This will trigger a rerun with yesterday's date
            yesterday = date.today() - pd.Timedelta(days=1)
            st.session_state.portfolio_date_picker = yesterday.date()
            st.rerun()
    
    with col2:
        if st.button("Today", key="today_btn"):
            # This will trigger a rerun with today's date
            st.session_state.portfolio_date_picker = date.today()
            st.rerun()
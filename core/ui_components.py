#!/usr/bin/env python3
"""
Standardized UI Components for Crypto Portfolio Dashboard
Provides consistent interface across ALL pages using ConfigManager
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Callable
import os
import sys

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.config_manager import ConfigManager


class StandardComponents:
    """
    Standardized UI components that ensure consistent behavior across ALL dashboard pages
    Uses ConfigManager for unified configuration access
    """
    
    def __init__(self):
        self.config_manager = ConfigManager()
        
    def create_standard_sidebar(self, page_name: str = "") -> Dict[str, Any]:
        """
        Create standardized sidebar that works the same on ALL pages
        Returns filter values that can be used by any page
        """
        st.sidebar.markdown("---")
        st.sidebar.header("🔍 Standard Filters")
        
        # Get default values from config
        standard_filters = self.config_manager.get_standard_filters()
        
        # Minimum Value Filter (consistent across ALL pages)
        min_value = st.sidebar.number_input(
            "Minimum Position Value ($)",
            min_value=0.0,
            value=standard_filters.get('min_value', 1.0),
            step=0.1,
            key=f"std_min_value_{page_name}",
            help="Hide positions below this USD value (applied to ALL pages)"
        )
        
        # Minimum Wallet Value Filter
        min_wallet_value = st.sidebar.number_input(
            "Minimum Wallet Value ($)",
            min_value=0.0,
            value=standard_filters.get('min_wallet_value', 10.0),
            step=1.0,
            key=f"std_min_wallet_{page_name}",
            help="Hide wallets with total value below this amount"
        )
        
        # Hide Dust Positions
        hide_dust = st.sidebar.checkbox(
            "Hide Dust Positions",
            value=standard_filters.get('hide_dust', True),
            key=f"std_hide_dust_{page_name}",
            help="Automatically hide very small positions"
        )
        
        # Show Wallet Holdings
        show_wallet_holdings = st.sidebar.checkbox(
            "Include Wallet Holdings",
            value=standard_filters.get('show_wallet_holdings', True),
            key=f"std_wallet_holdings_{page_name}",
            help="Include direct wallet token holdings (not just DeFi positions)"
        )
        
        # Date Range Selector (for applicable pages)
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 Time Period")
        
        date_option = st.sidebar.selectbox(
            "Select Time Period",
            ["Today", "Yesterday", "Last 7 days", "Last 30 days", "Custom Date"],
            key=f"std_date_option_{page_name}"
        )
        
        selected_date = None
        date_range = None
        
        if date_option == "Custom Date":
            selected_date = st.sidebar.date_input(
                "Select Date",
                value=date.today(),
                key=f"std_custom_date_{page_name}"
            )
        elif date_option == "Yesterday":
            selected_date = date.today() - timedelta(days=1)
        elif date_option == "Today":
            selected_date = date.today()
        elif date_option in ["Last 7 days", "Last 30 days"]:
            days = 7 if "7 days" in date_option else 30
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            date_range = (start_date, end_date)
        
        # Configuration Status
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚙️ Configuration")
        
        config_summary = self.config_manager.get_config_summary()
        st.sidebar.write(f"**Wallets:** {config_summary['wallets_count']}")
        st.sidebar.write(f"**Asset Groups:** {config_summary['asset_groups_count']}")
        st.sidebar.write(f"**Config Source:** {config_summary['config_source']}")
        
        if st.sidebar.button("🔧 Edit Configuration", key=f"edit_config_{page_name}"):
            st.switch_page("dashboard/config_editor.py")
        
        return {
            'min_value': min_value,
            'min_wallet_value': min_wallet_value,
            'hide_dust': hide_dust,
            'show_wallet_holdings': show_wallet_holdings,
            'selected_date': selected_date,
            'date_range': date_range,
            'date_option': date_option
        }
    
    def create_standard_metrics(self, data: pd.DataFrame, title: str = "Portfolio Metrics") -> Dict[str, float]:
        """
        Create standardized metrics display that works the same on ALL pages
        """
        if data.empty:
            st.warning("No data available for metrics calculation")
            return {}
        
        # Calculate key metrics
        total_value = data['usd_value_numeric'].sum() if 'usd_value_numeric' in data.columns else 0
        position_count = len(data)
        wallet_count = data['wallet_label'].nunique() if 'wallet_label' in data.columns else 0
        token_count = data['coin'].nunique() if 'coin' in data.columns else 0
        protocol_count = data['protocol'].nunique() if 'protocol' in data.columns else 0
        
        # Display metrics in consistent format
        st.subheader(f"📊 {title}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Portfolio Value",
                f"${total_value:,.2f}",
                help="Total USD value of all positions"
            )
        
        with col2:
            st.metric(
                "Total Positions",
                f"{position_count:,}",
                help="Number of individual token positions"
            )
        
        with col3:
            st.metric(
                "Active Wallets",
                f"{wallet_count}",
                help="Number of wallets with positions"
            )
        
        with col4:
            st.metric(
                "Unique Tokens",
                f"{token_count}",
                help="Number of different tokens held"
            )
        
        # Additional metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_position_value = total_value / position_count if position_count > 0 else 0
            st.metric(
                "Avg Position Value",
                f"${avg_position_value:,.2f}",
                help="Average value per position"
            )
        
        with col2:
            st.metric(
                "Protocols Used",
                f"{protocol_count}",
                help="Number of different protocols/platforms"
            )
        
        with col3:
            # Calculate diversification score (simple)
            diversification = min(100, (token_count / max(1, position_count)) * 100)
            st.metric(
                "Diversification",
                f"{diversification:.1f}%",
                help="Portfolio diversification score"
            )
        
        with col4:
            # Calculate largest position percentage
            if total_value > 0:
                largest_position = data.groupby('coin')['usd_value_numeric'].sum().max()
                concentration = (largest_position / total_value) * 100
            else:
                concentration = 0
            
            st.metric(
                "Top Token %",
                f"{concentration:.1f}%",
                help="Percentage of portfolio in largest token position"
            )
        
        return {
            'total_value': total_value,
            'position_count': position_count,
            'wallet_count': wallet_count,
            'token_count': token_count,
            'protocol_count': protocol_count,
            'avg_position_value': avg_position_value,
            'diversification': diversification,
            'concentration': concentration
        }
    
    def apply_standard_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """
        Apply standardized filtering logic consistently across ALL pages
        """
        if df.empty:
            return df
        
        original_count = len(df)
        
        # Ensure required columns exist
        if 'usd_value_numeric' not in df.columns:
            if 'usd_value' in df.columns:
                df['usd_value_numeric'] = df['usd_value'].apply(self._parse_currency)
            else:
                st.warning("No USD value column found for filtering")
                return df
        
        # Apply minimum position value filter
        if filters.get('min_value', 0) > 0:
            df = df[df['usd_value_numeric'] >= filters['min_value']]
        
        # Apply wallet value filter
        if filters.get('min_wallet_value', 0) > 0 and 'wallet_label' in df.columns:
            wallet_totals = df.groupby('wallet_label')['usd_value_numeric'].sum()
            valid_wallets = wallet_totals[wallet_totals >= filters['min_wallet_value']].index
            df = df[df['wallet_label'].isin(valid_wallets)]
        
        # Hide dust positions
        if filters.get('hide_dust', False):
            dust_threshold = 0.01  # $0.01 threshold for dust
            df = df[df['usd_value_numeric'] >= dust_threshold]
        
        # Wallet holdings filter
        if not filters.get('show_wallet_holdings', True) and 'protocol' in df.columns:
            df = df[df['protocol'] != 'Wallet']
        
        # Date filtering
        if filters.get('selected_date') and 'timestamp' in df.columns:
            target_date = filters['selected_date']
            if isinstance(df['timestamp'].iloc[0], str):
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            df['date_only'] = df['timestamp'].dt.date
            df = df[df['date_only'] == target_date]
            
            # If multiple entries for same date, take latest
            if len(df) > 0:
                latest_timestamp = df['timestamp'].max()
                df = df[df['timestamp'] == latest_timestamp]
            
            df = df.drop('date_only', axis=1)
        
        # Date range filtering
        if filters.get('date_range') and 'timestamp' in df.columns:
            start_date, end_date = filters['date_range']
            if isinstance(df['timestamp'].iloc[0], str):
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            df = df[
                (df['timestamp'].dt.date >= start_date) & 
                (df['timestamp'].dt.date <= end_date)
            ]
        
        # Show filtering results
        filtered_count = len(df)
        if original_count != filtered_count:
            st.info(f"🔍 Filtered: {original_count:,} → {filtered_count:,} positions")
        
        return df
    
    def create_standard_header(self, page_title: str, description: str = "", show_refresh: bool = True):
        """
        Create standardized page header with consistent styling
        """
        st.title(page_title)
        
        if description:
            st.markdown(description)
        
        # Add refresh and info buttons
        if show_refresh:
            col1, col2, col3 = st.columns([6, 1, 1])
            
            with col2:
                if st.button("🔄 Refresh", key=f"refresh_{page_title}"):
                    st.cache_data.clear()
                    st.rerun()
            
            with col3:
                with st.popover("ℹ️ Info"):
                    st.markdown(f"""
                    **{page_title}**
                    
                    {description if description else "Portfolio analysis page"}
                    
                    **Standard Filters Applied:**
                    - Minimum position value
                    - Minimum wallet value  
                    - Dust position filtering
                    - Date range selection
                    
                    Filters are consistent across ALL pages.
                    """)
        
        st.markdown("---")
    
    def _parse_currency(self, value):
        """Helper method to parse currency strings"""
        if pd.isna(value) or value == "None":
            return 0.0
        try:
            import re
            cleaned = re.sub(r'[$,]', '', str(value))
            return float(cleaned)
        except:
            return 0.0


class StandardPageTemplate:
    """
    Template for creating standardized pages that ensures consistency
    """
    
    def __init__(self):
        self.components = StandardComponents()
        self.config_manager = ConfigManager()
    
    def create_page(
        self, 
        page_title: str,
        page_description: str,
        content_function: Callable,
        data_loader: Optional[Callable] = None,
        page_key: str = ""
    ):
        """
        Create a standardized page with consistent structure
        
        Args:
            page_title: Title of the page
            page_description: Description shown below title
            content_function: Function that creates page-specific content
            data_loader: Optional custom data loading function
            page_key: Unique key for the page (for widget keys)
        """
        
        # 1. Standard Header
        self.components.create_standard_header(page_title, page_description)
        
        # 2. Standard Sidebar
        filters = self.components.create_standard_sidebar(page_key)
        
        # 3. Data Loading
        try:
            if data_loader:
                raw_data = data_loader()
            else:
                raw_data = self._default_data_loader()
            
            if raw_data is None or raw_data.empty:
                st.error("❌ No data available. Please check data files and run data collection.")
                return
                
        except Exception as e:
            st.error(f"❌ Error loading data: {str(e)}")
            st.info("💡 Try refreshing or check if data files exist.")
            return
        
        # 4. Standard Filtering
        filtered_data = self.components.apply_standard_filters(raw_data, filters)
        
        if filtered_data.empty:
            st.warning("⚠️ No data matches current filters. Try adjusting filter values.")
            st.info(f"Original data: {len(raw_data):,} positions")
            return
        
        # 5. Standard Metrics
        metrics = self.components.create_standard_metrics(filtered_data, "Current Filters")
        
        st.markdown("---")
        
        # 6. Page-Specific Content
        try:
            content_function(filtered_data, filters, metrics)
        except Exception as e:
            st.error(f"❌ Error rendering page content: {str(e)}")
            with st.expander("🐛 Debug Information"):
                st.write("**Data shape:**", filtered_data.shape)
                st.write("**Data columns:**", list(filtered_data.columns))
                st.write("**Filters:**", filters)
                st.write("**Error details:**", str(e))
    
    def _default_data_loader(self) -> pd.DataFrame:
        """Default data loading - looks for standard files"""
        try:
            # Try PnL-enhanced file first
            pnl_file = "portfolio_data/ALL_PORTFOLIOS_HISTORY_WITH_PNL.csv"
            if os.path.exists(pnl_file):
                df = pd.read_csv(pnl_file)
                return self._process_dataframe(df)
            
            # Fallback to standard file
            standard_file = "portfolio_data/ALL_PORTFOLIOS_HISTORY.csv"
            if os.path.exists(standard_file):
                df = pd.read_csv(standard_file)
                return self._process_dataframe(df)
            
            return pd.DataFrame()
            
        except Exception as e:
            st.error(f"Error in data loading: {str(e)}")
            return pd.DataFrame()
    
    def _process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and clean dataframe for standard use"""
        if df.empty:
            return df
        
        # Parse currency values
        if 'usd_value' in df.columns and 'usd_value_numeric' not in df.columns:
            df['usd_value_numeric'] = df['usd_value'].apply(self.components._parse_currency)
        
        # Parse timestamps
        if 'source_file_timestamp' in df.columns and 'timestamp' not in df.columns:
            df['timestamp'] = pd.to_datetime(df['source_file_timestamp'], format='%d-%m-%Y_%H-%M-%S', errors='coerce')
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Filter out zero values
        if 'usd_value_numeric' in df.columns:
            df = df[df['usd_value_numeric'] > 0]
        
        # Sort by timestamp if available
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp')
        
        return df


# Example Usage Functions for Integration

def integrate_existing_page(page_function, page_title: str, page_description: str = ""):
    """
    Wrapper to integrate existing pages with standard template
    """
    def wrapper():
        template = StandardPageTemplate()
        
        def content_wrapper(data, filters, metrics):
            # Call original page function with standardized data
            return page_function(data, filters, metrics)
        
        template.create_page(
            page_title=page_title,
            page_description=page_description,
            content_function=content_wrapper,
            page_key=page_title.lower().replace(" ", "_")
        )
    
    return wrapper

def main():
    """Test the StandardComponents system"""
    st.set_page_config(
        page_title="Standard Components Test",
        page_icon="🧪",
        layout="wide"
    )
    
    st.title("🧪 Standard Components Test")
    
    # Test StandardComponents
    components = StandardComponents()
    
    st.header("🔍 Testing Standard Sidebar")
    filters = components.create_standard_sidebar("test")
    st.json(filters)
    
    st.header("📊 Testing Standard Metrics")
    # Create sample data
    sample_data = pd.DataFrame({
        'wallet_label': ['Wallet1', 'Wallet2', 'Wallet1', 'Wallet2'],
        'coin': ['ETH', 'BTC', 'USDC', 'ETH'],
        'protocol': ['Wallet', 'Wallet', 'Aave', 'Uniswap'],
        'usd_value_numeric': [1000, 2000, 500, 300]
    })
    
    metrics = components.create_standard_metrics(sample_data)
    st.json(metrics)
    
    st.header("🔄 Testing Standard Filtering")
    filtered_data = components.apply_standard_filters(sample_data, filters)
    st.dataframe(filtered_data)

if __name__ == "__main__":
    main()
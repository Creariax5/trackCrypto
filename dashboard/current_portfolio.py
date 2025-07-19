#!/usr/bin/env python3
"""
Page Integration Examples - Shows how to update existing pages to use StandardComponents
This solves the $1 filter consistency issue across ALL pages
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, date
import sys
import os

from helper_functions import apply_asset_combinations, create_wallet_breakdown_chart, create_blockchain_breakdown_chart, create_top_holdings_chart, create_protocol_breakdown_chart

# Add project root for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.ui_components import StandardComponents, StandardPageTemplate
from core.config_manager import ConfigManager


def current_portfolio_page():
    """
    UPDATED version of current_portfolio.py using StandardComponents
    This ensures the $1 filter works consistently across ALL pages
    """
    
    def portfolio_content(data: pd.DataFrame, filters: dict, metrics: dict):
        """
        Page-specific content for current portfolio - same functionality, standardized interface
        """
        
        # === Configuration Integration ===
        config_manager = ConfigManager()
        
        # Asset grouping configuration (if available)
        asset_groups = config_manager.get_asset_groups()
        selected_config = None
        
        if asset_groups:
            st.subheader("⚙️ Asset Grouping")
            config_names = ["None"] + [group.get('name', f'Config {i}') for i, group in enumerate(asset_groups)]
            
            selected_config_name = st.selectbox(
                "Choose Asset Grouping Configuration",
                config_names,
                help="Groups related tokens for cleaner analysis"
            )
            
            if selected_config_name != "None":
                selected_config = next((g for g in asset_groups if g.get('name') == selected_config_name), None)
        
        st.markdown("---")
        
        # === Portfolio Analysis Charts ===
        st.header("📈 Portfolio Analysis")
        
        # Apply asset grouping if selected
        display_data = data.copy()
        if selected_config:
            display_data = apply_asset_combinations(display_data, selected_config)
        
        # Chart Row 1: Wallet Distribution and Blockchain Breakdown
        col1, col2 = st.columns(2)
        
        with col1:
            wallet_fig = create_wallet_breakdown_chart(display_data, filters.get('min_wallet_value', 0))
            if wallet_fig:
                st.plotly_chart(wallet_fig, use_container_width=True)
        
        with col2:
            blockchain_fig = create_blockchain_breakdown_chart(display_data)
            st.plotly_chart(blockchain_fig, use_container_width=True)
        
        # Chart Row 2: Top Holdings and Protocol Analysis
        col1, col2 = st.columns(2)
        
        with col1:
            holdings_fig = create_top_holdings_chart(display_data, selected_config)
            st.plotly_chart(holdings_fig, use_container_width=True)
        
        with col2:
            protocol_fig = create_protocol_breakdown_chart(display_data)
            st.plotly_chart(protocol_fig, use_container_width=True)
        
        # === Detailed Analysis ===
        st.markdown("---")
        st.header("📋 Detailed Holdings")
        
        # Additional filters for detailed view
        col1, col2, col3 = st.columns(3)
        
        with col1:
            wallet_filter = st.selectbox(
                "Filter by Wallet",
                ["All"] + list(display_data['wallet_label'].unique()),
                key="detail_wallet_filter"
            )
        
        with col2:
            blockchain_filter = st.selectbox(
                "Filter by Blockchain", 
                ["All"] + list(display_data['blockchain'].unique()),
                key="detail_blockchain_filter"
            )
        
        with col3:
            protocol_filter = st.selectbox(
                "Filter by Protocol",
                ["All"] + list(display_data['protocol'].unique()),
                key="detail_protocol_filter"
            )
        
        # Apply additional filters
        filtered_detail = display_data.copy()
        
        if wallet_filter != "All":
            filtered_detail = filtered_detail[filtered_detail['wallet_label'] == wallet_filter]
        
        if blockchain_filter != "All":
            filtered_detail = filtered_detail[filtered_detail['blockchain'] == blockchain_filter]
        
        if protocol_filter != "All":
            filtered_detail = filtered_detail[filtered_detail['protocol'] == protocol_filter]
        
        # Sort by value descending
        filtered_detail = filtered_detail.sort_values('usd_value_numeric', ascending=False)
        
        # Display detailed table
        display_columns = [
            'wallet_label', 'blockchain', 'coin', 'token_name', 
            'protocol', 'amount', 'price', 'usd_value'
        ]
        
        available_columns = [col for col in display_columns if col in filtered_detail.columns]
        
        st.dataframe(
            filtered_detail[available_columns],
            use_container_width=True,
            hide_index=True
        )
        
        # Summary of filtered data
        detail_total = filtered_detail['usd_value_numeric'].sum()
        st.info(f"💰 Filtered total: ${detail_total:,.2f} ({len(filtered_detail)} positions)")
    
    # Use StandardPageTemplate for consistency
    template = StandardPageTemplate()
    template.create_page(
        page_title="📊 Current Portfolio Analysis",
        page_description="Real-time portfolio analysis with standardized filtering and asset grouping",
        content_function=portfolio_content,
        page_key="current_portfolio"
    )

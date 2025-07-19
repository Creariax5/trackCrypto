import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, date
import sys
import os

from helper_functions import apply_asset_combinations, get_top_items_by_value, get_top_performing_items, get_available_items, create_performance_comparison_chart, calculate_performance_metrics

# Add project root for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.ui_components import StandardComponents, StandardPageTemplate
from core.config_manager import ConfigManager


def performance_analysis_page():
    """
    UPDATED version of performance_analysis.py using StandardComponents
    Same functionality with consistent $1 filter
    """
    
    def performance_content(data: pd.DataFrame, filters: dict, metrics: dict):
        """
        Page-specific content for performance analysis
        """
        
        config_manager = ConfigManager()
        
        st.header("🎯 Performance Comparison")
        
        # Analysis type selector
        analysis_type = st.selectbox(
            "Analysis Type",
            ["assets", "protocol_positions"],
            format_func=lambda x: {
                "assets": "💰 Asset Performance",
                "protocol_positions": "🏛️ Protocol Position Performance"
            }[x],
            key="perf_analysis_type"
        )
        
        # Period selector
        col1, col2 = st.columns(2)
        
        with col1:
            analysis_period = st.selectbox(
                "Analysis Period",
                [7, 14, 30, 60, 90],
                index=2,
                format_func=lambda x: f"{x} days"
            )
        
        with col2:
            selection_method = st.selectbox(
                f"Selection Method",
                ["top_value", "top_performers", "custom"],
                format_func=lambda x: {
                    "top_value": "🏆 Top 10 by Value",
                    "top_performers": "🚀 Top 10 Performers", 
                    "custom": "🎯 Custom Selection"
                }[x]
            )
        
        # Get asset groups for combinations
        asset_groups = config_manager.get_asset_groups()
        selected_config = None
        
        if asset_groups:
            with st.expander("⚙️ Asset Grouping Configuration"):
                config_names = ["None"] + [group.get('name', f'Config {i}') for i, group in enumerate(asset_groups)]
                selected_config_name = st.selectbox(
                    "Asset Grouping",
                    config_names,
                    key="perf_asset_config"
                )
                
                if selected_config_name != "None":
                    selected_config = next((g for g in asset_groups if g.get('name') == selected_config_name), None)
        
        # Filter data for protocol analysis if needed
        analysis_data = data.copy()
        if analysis_type == "protocol_positions" and 'protocol' in analysis_data.columns:
            analysis_data = analysis_data[analysis_data['protocol'] != 'Wallet']
        
        # Apply asset combinations if selected
        if selected_config:
            analysis_data = apply_asset_combinations(analysis_data, selected_config)
        
        # Performance calculation based on selection method
        if selection_method == "top_value":
            selected_items = get_top_items_by_value(analysis_data, analysis_type, 10)
            st.info(f"Showing top 10 {analysis_type.replace('_', ' ')} by current portfolio value")
            
        elif selection_method == "top_performers":
            selected_items = get_top_performing_items(analysis_data, analysis_type, analysis_period, 10)
            st.info(f"Showing top 10 best performing {analysis_type.replace('_', ' ')} over {analysis_period} days")
            
        else:  # custom
            available_items = get_available_items(analysis_data, analysis_type)
            selected_items = st.multiselect(
                f"Select {analysis_type.replace('_', ' ')}:",
                options=available_items,
                default=available_items[:5] if len(available_items) >= 5 else available_items
            )
        
        # Create performance chart
        if selected_items:
            st.markdown("---")
            
            chart = create_performance_comparison_chart(
                analysis_data, selected_items, analysis_period, analysis_type
            )
            
            if chart:
                st.plotly_chart(chart, use_container_width=True)
            
            # Performance metrics table
            st.subheader("📊 Performance Metrics")
            
            metrics_data = calculate_performance_metrics(
                analysis_data, selected_items, analysis_period, analysis_type
            )
            
            if metrics_data:
                st.dataframe(metrics_data, use_container_width=True, hide_index=True)
            
        else:
            st.warning("No items selected for analysis")
    
    # Use StandardPageTemplate
    template = StandardPageTemplate()
    template.create_page(
        page_title="🎯 Performance Analysis",
        page_description="Compare asset and protocol performance with standardized filtering",
        content_function=performance_content,
        page_key="performance_analysis"
    )

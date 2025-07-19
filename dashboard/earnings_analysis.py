import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, date
import sys
import os

# Add project root for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.ui_components import StandardComponents, StandardPageTemplate
from core.config_manager import ConfigManager


def earnings_analysis_page():
    """
    UPDATED earnings analysis with StandardComponents integration
    """
    
    def earnings_content(data: pd.DataFrame, filters: dict, metrics: dict):
        """
        Simplified earnings analysis content
        """
        
        # Check for PnL data
        has_pnl = 'pnl_since_last_update' in data.columns
        
        if not has_pnl:
            st.warning("⚠️ PnL data not available. Run `python processors/calculate_pnl.py` for enhanced analysis.")
            st.info("Showing basic portfolio analysis instead.")
            
            # Basic analysis without PnL
            st.subheader("📈 Portfolio Growth Analysis")
            
            if 'timestamp' in data.columns:
                timeline = data.groupby('timestamp')['usd_value_numeric'].sum().reset_index()
                timeline = timeline.sort_values('timestamp')
                
                if len(timeline) > 1:
                    fig = px.line(
                        timeline, 
                        x='timestamp', 
                        y='usd_value_numeric',
                        title="Portfolio Value Over Time"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Growth metrics
                if len(timeline) >= 2:
                    start_value = timeline['usd_value_numeric'].iloc[0]
                    end_value = timeline['usd_value_numeric'].iloc[-1]
                    total_return = ((end_value - start_value) / start_value * 100) if start_value > 0 else 0
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Start Value", f"${start_value:,.2f}")
                    with col2:
                        st.metric("Current Value", f"${end_value:,.2f}")
                    with col3:
                        st.metric("Total Return", f"{total_return:+.2f}%")
            
            return
        
        # Enhanced PnL Analysis
        st.header("💰 PnL Analytics")
        
        pnl_data = data[data['pnl_since_last_update'] != 0]
        
        if len(pnl_data) == 0:
            st.info("No PnL data available for analysis")
            return
        
        # PnL Summary Metrics
        total_pnl = pnl_data['pnl_since_last_update'].sum()
        profitable_positions = len(pnl_data[pnl_data['pnl_since_last_update'] > 0])
        losing_positions = len(pnl_data[pnl_data['pnl_since_last_update'] < 0])
        win_rate = (profitable_positions / len(pnl_data) * 100) if len(pnl_data) > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total PnL", f"${total_pnl:+,.2f}")
        with col2:
            st.metric("Win Rate", f"{win_rate:.1f}%")
        with col3:
            st.metric("Profitable", f"{profitable_positions}")
        with col4:
            st.metric("Losing", f"{losing_positions}")
        
        # PnL Distribution Chart
        st.subheader("📊 PnL Distribution")
        
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=pnl_data['pnl_since_last_update'],
            nbinsx=30,
            marker_color='lightblue',
            opacity=0.7
        ))
        fig.add_vline(x=0, line_dash="dash", line_color="red")
        fig.update_layout(
            title="PnL Distribution Across Position Updates",
            xaxis_title="PnL ($)",
            yaxis_title="Frequency"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Top/Bottom Performers
        st.subheader("🏆 Top Performers")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🚀 Best Gains**")
            top_gains = pnl_data.nlargest(5, 'pnl_since_last_update')[
                ['wallet_label', 'coin', 'protocol', 'pnl_since_last_update']
            ]
            top_gains['PnL'] = top_gains['pnl_since_last_update'].apply(lambda x: f"${x:+,.2f}")
            st.dataframe(top_gains[['wallet_label', 'coin', 'protocol', 'PnL']], hide_index=True)
        
        with col2:
            st.markdown("**📉 Biggest Losses**")
            top_losses = pnl_data.nsmallest(5, 'pnl_since_last_update')[
                ['wallet_label', 'coin', 'protocol', 'pnl_since_last_update']
            ]
            top_losses['PnL'] = top_losses['pnl_since_last_update'].apply(lambda x: f"${x:+,.2f}")
            st.dataframe(top_losses[['wallet_label', 'coin', 'protocol', 'PnL']], hide_index=True)
    
    # Use StandardPageTemplate
    template = StandardPageTemplate()
    template.create_page(
        page_title="💰 Earnings & PnL Analysis", 
        page_description="Advanced PnL analytics with position-level tracking",
        content_function=earnings_content,
        page_key="earnings_analysis"
    )
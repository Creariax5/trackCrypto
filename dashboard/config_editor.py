#!/usr/bin/env python3
"""
Visual Configuration Editor - Complete dashboard configuration management
Provides unified interface for all system settings
"""

import streamlit as st
import pandas as pd
import json
import os
import sys
from typing import Dict, List, Any
from datetime import datetime

# Add project root for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.config_manager import ConfigManager


def config_editor_page():
    """
    Complete configuration editor with visual interface for all settings
    This solves the scattered configuration problem
    """
    
    st.title("⚙️ Portfolio Configuration Editor")
    st.markdown("Visual interface for managing ALL dashboard settings and configurations")
    
    # Initialize ConfigManager
    config_manager = ConfigManager()
    config = config_manager.config.copy()  # Work with copy to avoid accidental changes
    
    # Show current configuration status
    with st.expander("📊 Configuration Status", expanded=False):
        summary = config_manager.get_config_summary()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Wallets", summary['wallets_count'])
            st.metric("Friends", summary['friends_count'])
        with col2:
            st.metric("Asset Groups", summary['asset_groups_count'])
            st.metric("Config Source", summary['config_source'])
        with col3:
            st.write("**Legacy Files:**")
            for file, exists in summary['legacy_files'].items():
                status = "✅" if exists else "❌"
                st.write(f"{status} {file}")
    
    st.markdown("---")
    
    # === 1. STANDARD FILTERS SECTION ===
    st.header("🔍 Standard Filters (Applied to ALL Pages)")
    st.markdown("These filters provide consistent behavior across the entire dashboard")
    
    current_filters = config.get('filters', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💰 Value Filters")
        
        min_value = st.number_input(
            "Minimum Position Value ($)",
            min_value=0.0,
            value=current_filters.get('min_value', 1.0),
            step=0.1,
            help="Hide positions below this USD value on ALL pages. This solves the $1 filter consistency issue!"
        )
        
        min_wallet_value = st.number_input(
            "Minimum Wallet Value ($)",
            min_value=0.0,
            value=current_filters.get('min_wallet_value', 10.0),
            step=1.0,
            help="Hide wallets with total value below this amount"
        )
        
        min_pnl_filter = st.number_input(
            "Minimum |PnL| Filter ($)",
            min_value=0.0,
            value=current_filters.get('min_pnl_filter', 0.0),
            step=0.1,
            help="Only show PnL changes above this absolute value"
        )
    
    with col2:
        st.subheader("⚙️ Display Options")
        
        hide_dust = st.checkbox(
            "Hide Dust Positions",
            value=current_filters.get('hide_dust', True),
            help="Automatically hide very small positions (< $0.01)"
        )
        
        show_wallet_holdings = st.checkbox(
            "Show Wallet Holdings",
            value=current_filters.get('show_wallet_holdings', True),
            help="Include direct wallet token holdings (not just DeFi positions)"
        )
        
        show_new_positions_only = st.checkbox(
            "Show Only Position Updates",
            value=current_filters.get('show_new_positions_only', False),
            help="In PnL analysis, exclude brand new positions and show only updates"
        )
    
    # Update filters in config
    config['filters'] = {
        'min_value': min_value,
        'min_wallet_value': min_wallet_value,
        'min_pnl_filter': min_pnl_filter,
        'hide_dust': hide_dust,
        'show_wallet_holdings': show_wallet_holdings,
        'show_new_positions_only': show_new_positions_only
    }
    
    st.markdown("---")
    
    # === 2. WALLET MANAGEMENT SECTION ===
    st.header("💰 Wallet Management")
    st.markdown("Manage your tracked wallet addresses and labels")
    
    current_wallets = config.get('wallets', {})
    
    # Display current wallets
    if current_wallets:
        st.subheader("📋 Current Wallets")
        
        wallets_to_remove = []
        for i, (address, label) in enumerate(current_wallets.items()):
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                new_label = st.text_input(
                    "Wallet Label",
                    value=label,
                    key=f"wallet_label_{i}",
                    placeholder="Enter descriptive name"
                )
                current_wallets[address] = new_label
            
            with col2:
                st.text_input(
                    "Address",
                    value=f"{address[:10]}...{address[-8:]}",
                    disabled=True,
                    key=f"wallet_addr_{i}"
                )
            
            with col3:
                st.write("")  # Spacing
                if st.button("🗑️", key=f"remove_wallet_{i}", help="Remove wallet"):
                    wallets_to_remove.append(address)
        
        # Remove selected wallets
        for addr in wallets_to_remove:
            del current_wallets[addr]
    
    # Add new wallet
    st.subheader("➕ Add New Wallet")
    
    col1, col2, col3 = st.columns([3, 2, 1])
    
    with col1:
        new_wallet_label = st.text_input(
            "New Wallet Label",
            placeholder="e.g., Main Trading Wallet",
            key="new_wallet_label"
        )
    
    with col2:
        new_wallet_address = st.text_input(
            "Wallet Address",
            placeholder="0x1234567890abcdef...",
            key="new_wallet_address"
        )
    
    with col3:
        st.write("")  # Spacing
        if st.button("➕ Add Wallet"):
            if new_wallet_address and new_wallet_label:
                # Validate address format
                if new_wallet_address.startswith('0x') and len(new_wallet_address) == 42:
                    current_wallets[new_wallet_address] = new_wallet_label
                    st.success(f"✅ Added wallet: {new_wallet_label}")
                    st.rerun()
                else:
                    st.error("❌ Invalid address format. Must be 42 characters starting with 0x")
            else:
                st.error("❌ Please provide both label and address")
    
    # Update wallets in config
    config['wallets'] = current_wallets
    
    st.markdown("---")
    
    # === 3. FRIENDS MANAGEMENT SECTION ===
    st.header("👥 Friends & External Addresses")
    st.markdown("Manage known addresses for transaction analysis")
    
    current_friends = config.get('friends', {})
    
    # Display current friends
    if current_friends:
        st.subheader("📋 Current Friends")
        
        friends_to_remove = []
        for friend_id, friend_info in current_friends.items():
            col1, col2, col3, col4 = st.columns([2, 2, 3, 1])
            
            with col1:
                new_name = st.text_input(
                    "Name",
                    value=friend_info.get('name', ''),
                    key=f"friend_name_{friend_id}",
                    placeholder="Friend's name"
                )
            
            with col2:
                new_description = st.text_input(
                    "Description",
                    value=friend_info.get('description', ''),
                    key=f"friend_desc_{friend_id}",
                    placeholder="e.g., Trading partner"
                )
            
            with col3:
                address = friend_info.get('address', '')
                st.text_input(
                    "Address",
                    value=f"{address[:10]}...{address[-8:]}" if address else "No address",
                    disabled=True,
                    key=f"friend_addr_{friend_id}"
                )
            
            with col4:
                st.write("")  # Spacing
                if st.button("🗑️", key=f"remove_friend_{friend_id}", help="Remove friend"):
                    friends_to_remove.append(friend_id)
            
            # Update friend info
            current_friends[friend_id]['name'] = new_name
            current_friends[friend_id]['description'] = new_description
        
        # Remove selected friends
        for friend_id in friends_to_remove:
            del current_friends[friend_id]
    
    # Add new friend
    st.subheader("➕ Add New Friend")
    
    col1, col2, col3, col4 = st.columns([2, 2, 3, 1])
    
    with col1:
        new_friend_name = st.text_input(
            "Friend Name",
            placeholder="e.g., John",
            key="new_friend_name"
        )
    
    with col2:
        new_friend_desc = st.text_input(
            "Description",
            placeholder="e.g., Trading partner",
            key="new_friend_desc"
        )
    
    with col3:
        new_friend_address = st.text_input(
            "Friend Address",
            placeholder="0x1234567890abcdef...",
            key="new_friend_address"
        )
    
    with col4:
        st.write("")  # Spacing
        if st.button("➕ Add Friend"):
            if new_friend_address and new_friend_name:
                if new_friend_address.startswith('0x') and len(new_friend_address) == 42:
                    friend_id = new_friend_name.lower().replace(' ', '_')
                    current_friends[friend_id] = {
                        'address': new_friend_address,
                        'name': new_friend_name,
                        'description': new_friend_desc
                    }
                    st.success(f"✅ Added friend: {new_friend_name}")
                    st.rerun()
                else:
                    st.error("❌ Invalid address format")
            else:
                st.error("❌ Please provide name and address")
    
    # Update friends in config
    config['friends'] = current_friends
    
    st.markdown("---")
    
    # === 4. ASSET GROUPS MANAGEMENT ===
    st.header("🏷️ Asset Groups & Combinations")
    st.markdown("Create custom asset groupings for cleaner analysis")
    
    current_asset_groups = config.get('asset_groups', [])
    
    # Asset group editor
    if current_asset_groups:
        st.subheader("📋 Current Asset Groups")
        
        groups_to_remove = []
        for i, group in enumerate(current_asset_groups):
            with st.expander(f"📁 {group.get('name', f'Group {i+1}')}", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Edit group details
                    group_name = st.text_input(
                        "Group Name",
                        value=group.get('name', ''),
                        key=f"group_name_{i}"
                    )
                    
                    group_desc = st.text_input(
                        "Description",
                        value=group.get('description', ''),
                        key=f"group_desc_{i}"
                    )
                
                with col2:
                    st.write("")  # Spacing
                    if st.button("🗑️ Remove Group", key=f"remove_group_{i}"):
                        groups_to_remove.append(i)
                
                # Asset combinations
                st.markdown("**Asset Combinations:**")
                asset_combinations = group.get('asset_combinations', {})
                
                # Display existing combinations
                combinations_to_remove = []
                for combo_name, tokens in asset_combinations.items():
                    col1, col2, col3 = st.columns([2, 4, 1])
                    
                    with col1:
                        new_combo_name = st.text_input(
                            "Group Name",
                            value=combo_name,
                            key=f"combo_{i}_{combo_name}_name"
                        )
                    
                    with col2:
                        new_tokens = st.text_input(
                            "Tokens (comma separated)",
                            value=", ".join(tokens),
                            key=f"combo_{i}_{combo_name}_tokens"
                        )
                    
                    with col3:
                        if st.button("🗑️", key=f"remove_combo_{i}_{combo_name}"):
                            combinations_to_remove.append(combo_name)
                    
                    # Update combination
                    if new_combo_name != combo_name:
                        del asset_combinations[combo_name]
                        combo_name = new_combo_name
                    
                    asset_combinations[combo_name] = [t.strip() for t in new_tokens.split(',') if t.strip()]
                
                # Remove selected combinations
                for combo_name in combinations_to_remove:
                    del asset_combinations[combo_name]
                
                # Add new combination
                st.markdown("**Add New Combination:**")
                col1, col2, col3 = st.columns([2, 4, 1])
                
                with col1:
                    new_combo_name = st.text_input(
                        "Combination Name",
                        placeholder="e.g., Stablecoins",
                        key=f"new_combo_name_{i}"
                    )
                
                with col2:
                    new_combo_tokens = st.text_input(
                        "Tokens",
                        placeholder="e.g., USDC, USDT, DAI",
                        key=f"new_combo_tokens_{i}"
                    )
                
                with col3:
                    if st.button("➕", key=f"add_combo_{i}"):
                        if new_combo_name and new_combo_tokens:
                            asset_combinations[new_combo_name] = [t.strip() for t in new_combo_tokens.split(',') if t.strip()]
                            st.success(f"✅ Added: {new_combo_name}")
                            st.rerun()
                
                # Update group
                current_asset_groups[i] = {
                    'name': group_name,
                    'description': group_desc,
                    'asset_combinations': asset_combinations,
                    'asset_renames': group.get('asset_renames', {}),
                    'protocol_combinations': group.get('protocol_combinations', {}),
                    'protocol_renames': group.get('protocol_renames', {})
                }
        
        # Remove selected groups
        for i in sorted(groups_to_remove, reverse=True):
            del current_asset_groups[i]
    
    # Add new asset group
    st.subheader("➕ Add New Asset Group")
    
    col1, col2, col3 = st.columns([2, 3, 1])
    
    with col1:
        new_group_name = st.text_input(
            "Group Name",
            placeholder="e.g., DeFi Strategy",
            key="new_group_name"
        )
    
    with col2:
        new_group_desc = st.text_input(
            "Description",
            placeholder="e.g., Tokens for DeFi farming",
            key="new_group_desc"
        )
    
    with col3:
        st.write("")  # Spacing
        if st.button("➕ Add Group"):
            if new_group_name:
                new_group = {
                    'name': new_group_name,
                    'description': new_group_desc,
                    'asset_combinations': {},
                    'asset_renames': {},
                    'protocol_combinations': {},
                    'protocol_renames': {}
                }
                current_asset_groups.append(new_group)
                st.success(f"✅ Added group: {new_group_name}")
                st.rerun()
            else:
                st.error("❌ Please provide group name")
    
    # Update asset groups in config
    config['asset_groups'] = current_asset_groups
    
    st.markdown("---")
    
    # === 5. UI SETTINGS SECTION ===
    st.header("🎨 Dashboard UI Settings")
    st.markdown("Customize the look and behavior of the dashboard")
    
    ui_settings = config.get('ui_settings', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Chart Settings")
        
        default_top_n = st.number_input(
            "Default Top N Items",
            min_value=5,
            max_value=50,
            value=ui_settings.get('charts', {}).get('default_top_n', 10),
            help="Default number of items to show in top charts"
        )
        
        color_scheme = st.selectbox(
            "Chart Color Scheme",
            ["viridis", "plasma", "inferno", "magma", "cividis"],
            index=0,
            help="Color scheme for charts and visualizations"
        )
        
        show_legends = st.checkbox(
            "Show Chart Legends",
            value=ui_settings.get('charts', {}).get('show_legends', True)
        )
    
    with col2:
        st.subheader("📋 Table Settings")
        
        items_per_page = st.number_input(
            "Items Per Page",
            min_value=10,
            max_value=100,
            value=ui_settings.get('tables', {}).get('items_per_page', 25),
            step=5,
            help="Number of items to show per page in tables"
        )
        
        show_index = st.checkbox(
            "Show Table Index",
            value=ui_settings.get('tables', {}).get('show_index', False)
        )
    
    # Update UI settings in config
    config['ui_settings'] = {
        'charts': {
            'default_top_n': default_top_n,
            'color_scheme': color_scheme,
            'show_legends': show_legends
        },
        'tables': {
            'items_per_page': items_per_page,
            'show_index': show_index
        }
    }
    
    st.markdown("---")
    
    # === 6. SAVE CONFIGURATION ===
    st.header("💾 Save Configuration")
    
    # Preview changes
    with st.expander("👀 Preview Changes", expanded=False):
        st.json(config)
    
    # Save buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Configuration", type="primary"):
            try:
                # Update config manager
                config_manager.config = config
                
                # Save to unified config file
                success = config_manager.save_config(backup_existing=True)
                
                if success:
                    st.success("✅ Configuration saved successfully!")
                    st.info("🔄 Refresh other dashboard pages to see changes take effect.")
                else:
                    st.error("❌ Failed to save configuration")
                    
            except Exception as e:
                st.error(f"❌ Error saving configuration: {str(e)}")
    
    with col2:
        if st.button("📤 Export Legacy Configs"):
            try:
                success = config_manager.export_legacy_configs()
                if success:
                    st.success("✅ Legacy config files exported!")
                    st.info("📁 Check config/ folder for updated files")
                else:
                    st.error("❌ Failed to export legacy configs")
            except Exception as e:
                st.error(f"❌ Error exporting: {str(e)}")
    
    with col3:
        if st.button("🔄 Reset to Defaults"):
            if st.session_state.get('confirm_reset', False):
                # Reset config to defaults
                config_manager.config = {
                    "version": "2.0",
                    "created": datetime.now().isoformat(),
                    "wallets": {},
                    "friends": {},
                    "asset_groups": [],
                    "filters": config_manager._get_default_filters(),
                    "ui_settings": config_manager._get_default_ui_settings(),
                    "data_settings": config_manager._get_default_data_settings()
                }
                config_manager.save_config()
                st.success("✅ Configuration reset to defaults")
                st.rerun()
            else:
                st.session_state.confirm_reset = True
                st.warning("⚠️ Click again to confirm reset")
    
    # Configuration validation
    st.markdown("---")
    st.subheader("✅ Configuration Validation")
    
    validation = config_manager.validate_configuration()
    
    if validation['errors']:
        st.error(f"❌ {len(validation['errors'])} errors found:")
        for error in validation['errors']:
            st.write(f"• {error}")
    
    if validation['warnings']:
        st.warning(f"⚠️ {len(validation['warnings'])} warnings:")
        for warning in validation['warnings']:
            st.write(f"• {warning}")
    
    if validation['suggestions']:
        st.info(f"💡 {len(validation['suggestions'])} suggestions:")
        for suggestion in validation['suggestions']:
            st.write(f"• {suggestion}")
    
    if not validation['errors'] and not validation['warnings']:
        st.success("✅ Configuration is valid!")


def main():
    """Main function for standalone testing"""
    st.set_page_config(
        page_title="Configuration Editor",
        page_icon="⚙️",
        layout="wide"
    )
    
    config_editor_page()


if __name__ == "__main__":
    main()
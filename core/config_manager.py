#!/usr/bin/env python3
"""
Unified Configuration Manager
Provides single interface to all configuration while maintaining backward compatibility
"""

import json
import os
import glob
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Unified configuration manager that provides single interface to all configs
    while maintaining backward compatibility with existing config files
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.unified_config_path = os.path.join(config_dir, "config.json")
        self.config = self.load_configuration()
        
    def load_configuration(self) -> Dict[str, Any]:
        """
        Load configuration from unified config.json OR fallback to existing files
        """
        if os.path.exists(self.unified_config_path):
            logger.info("Loading unified configuration from config.json")
            return self.load_unified_config()
        else:
            logger.info("No unified config found, loading from legacy config files")
            return self.load_legacy_configs()
    
    def load_unified_config(self) -> Dict[str, Any]:
        """Load from unified config.json file"""
        try:
            with open(self.unified_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate unified config structure
            self._validate_unified_config(config)
            return config
            
        except Exception as e:
            logger.error(f"Error loading unified config: {e}")
            logger.info("Falling back to legacy configs")
            return self.load_legacy_configs()
    
    def load_legacy_configs(self) -> Dict[str, Any]:
        """
        Combine existing config files into unified structure
        Maintains full backward compatibility
        """
        unified_config = {
            "version": "2.0",
            "created": datetime.now().isoformat(),
            "wallets": {},
            "friends": {},
            "asset_groups": [],
            "filters": self._get_default_filters(),
            "ui_settings": self._get_default_ui_settings(),
            "data_settings": self._get_default_data_settings()
        }
        
        # Load wallets
        wallets_config = self._load_wallets_config()
        if wallets_config:
            unified_config["wallets"] = wallets_config.get("wallets", {})
        
        # Load friends
        friends_config = self._load_friends_config()
        if friends_config:
            unified_config["friends"] = friends_config.get("friends", {})
        
        # Load asset groups from streamlit configs
        asset_groups = self._load_streamlit_configs()
        unified_config["asset_groups"] = asset_groups
        
        return unified_config
    
    def _load_wallets_config(self) -> Optional[Dict]:
        """Load wallets.json if it exists"""
        wallets_path = os.path.join(self.config_dir, "wallets.json")
        if os.path.exists(wallets_path):
            try:
                with open(wallets_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading wallets.json: {e}")
        return None
    
    def _load_friends_config(self) -> Optional[Dict]:
        """Load friends_addresses.json if it exists"""
        friends_path = os.path.join(self.config_dir, "friends_addresses.json")
        if os.path.exists(friends_path):
            try:
                with open(friends_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading friends_addresses.json: {e}")
        return None
    
    def _load_streamlit_configs(self) -> List[Dict]:
        """Load all JSON configs from streamlit/ directory"""
        asset_groups = []
        streamlit_dir = os.path.join(self.config_dir, "streamlit")
        
        if os.path.exists(streamlit_dir):
            json_files = glob.glob(os.path.join(streamlit_dir, "*.json"))
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        
                    # Add metadata
                    config_data["_source_file"] = os.path.basename(json_file)
                    config_data["_loaded_from_legacy"] = True
                    
                    asset_groups.append(config_data)
                    logger.info(f"Loaded asset group config: {config_data.get('name', 'Unnamed')}")
                    
                except Exception as e:
                    logger.error(f"Error loading {json_file}: {e}")
        
        return asset_groups
    
    def _get_default_filters(self) -> Dict[str, Any]:
        """Default filter settings applied across all pages"""
        return {
            "min_value": 1.0,
            "min_wallet_value": 10.0,
            "hide_dust": True,
            "show_wallet_holdings": True,
            "show_new_positions_only": False,
            "min_pnl_filter": 0.0
        }
    
    def _get_default_ui_settings(self) -> Dict[str, Any]:
        """Default UI settings for dashboard"""
        return {
            "theme": "light",
            "charts": {
                "default_top_n": 10,
                "color_scheme": "viridis",
                "show_legends": True
            },
            "tables": {
                "items_per_page": 25,
                "show_index": False
            },
            "sidebar": {
                "expanded": True,
                "show_advanced_filters": False
            }
        }
    
    def _get_default_data_settings(self) -> Dict[str, Any]:
        """Default data processing settings"""
        return {
            "update_frequency": "daily",
            "price_api": {
                "source": "coingecko",
                "cache_duration_hours": 24,
                "rate_limit_per_minute": 45
            },
            "pnl_calculation": {
                "enabled": True,
                "track_new_positions": True,
                "min_position_value": 0.01
            }
        }
    
    def _validate_unified_config(self, config: Dict) -> bool:
        """Validate unified config structure"""
        required_sections = ["wallets", "friends", "asset_groups", "filters"]
        for section in required_sections:
            if section not in config:
                logger.warning(f"Missing required section: {section}")
                config[section] = {}
        return True
    
    # ==================== ACCESS METHODS ====================
    
    def get_wallets(self) -> Dict[str, str]:
        """Get wallet addresses and labels"""
        return self.config.get("wallets", {})
    
    def get_friends(self) -> Dict[str, Dict]:
        """Get friend addresses and information"""
        return self.config.get("friends", {})
    
    def get_asset_groups(self) -> List[Dict]:
        """Get all asset group configurations"""
        return self.config.get("asset_groups", [])
    
    def get_asset_group_by_name(self, name: str) -> Optional[Dict]:
        """Get specific asset group configuration by name"""
        for group in self.get_asset_groups():
            if group.get("name") == name:
                return group
        return None
    
    def get_standard_filters(self) -> Dict[str, Any]:
        """Get standardized filter settings for ALL pages"""
        return self.config.get("filters", self._get_default_filters())
    
    def get_ui_settings(self) -> Dict[str, Any]:
        """Get UI settings"""
        return self.config.get("ui_settings", self._get_default_ui_settings())
    
    def get_data_settings(self) -> Dict[str, Any]:
        """Get data processing settings"""
        return self.config.get("data_settings", self._get_default_data_settings())
    
    # ==================== UTILITY METHODS ====================
    
    def get_wallet_label(self, address: str) -> str:
        """Get wallet label for address, fallback to shortened address"""
        wallets = self.get_wallets()
        return wallets.get(address, f"{address[:10]}...")
    
    def get_friend_name(self, address: str) -> Optional[str]:
        """Get friend name for address"""
        friends = self.get_friends()
        for friend_info in friends.values():
            if friend_info.get("address", "").lower() == address.lower():
                return friend_info.get("name")
        return None
    
    def is_friend_address(self, address: str) -> bool:
        """Check if address belongs to a friend"""
        return self.get_friend_name(address) is not None
    
    def get_all_known_addresses(self) -> Dict[str, str]:
        """Get all known addresses (wallets + friends) with labels"""
        known = {}
        
        # Add wallets
        for addr, label in self.get_wallets().items():
            known[addr.lower()] = f"Wallet: {label}"
        
        # Add friends
        for friend_info in self.get_friends().values():
            addr = friend_info.get("address", "")
            name = friend_info.get("name", "Unknown")
            if addr:
                known[addr.lower()] = f"Friend: {name}"
        
        return known
    
    # ==================== UPDATE METHODS ====================
    
    def update_filter(self, filter_name: str, value: Any) -> bool:
        """Update a specific filter setting"""
        try:
            if "filters" not in self.config:
                self.config["filters"] = self._get_default_filters()
            
            self.config["filters"][filter_name] = value
            return True
        except Exception as e:
            logger.error(f"Error updating filter {filter_name}: {e}")
            return False
    
    def update_filters(self, new_filters: Dict[str, Any]) -> bool:
        """Update multiple filter settings"""
        try:
            if "filters" not in self.config:
                self.config["filters"] = self._get_default_filters()
            
            self.config["filters"].update(new_filters)
            return True
        except Exception as e:
            logger.error(f"Error updating filters: {e}")
            return False
    
    def add_wallet(self, address: str, label: str) -> bool:
        """Add a new wallet"""
        try:
            if "wallets" not in self.config:
                self.config["wallets"] = {}
            
            self.config["wallets"][address] = label
            return True
        except Exception as e:
            logger.error(f"Error adding wallet: {e}")
            return False
    
    def remove_wallet(self, address: str) -> bool:
        """Remove a wallet"""
        try:
            if address in self.config.get("wallets", {}):
                del self.config["wallets"][address]
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing wallet: {e}")
            return False
    
    def add_asset_group(self, asset_group: Dict) -> bool:
        """Add a new asset group configuration"""
        try:
            if "asset_groups" not in self.config:
                self.config["asset_groups"] = []
            
            # Add metadata
            asset_group["_created"] = datetime.now().isoformat()
            asset_group["_source"] = "config_manager"
            
            self.config["asset_groups"].append(asset_group)
            return True
        except Exception as e:
            logger.error(f"Error adding asset group: {e}")
            return False
    
    # ==================== SAVE METHODS ====================
    
    def save_config(self, backup_existing: bool = True) -> bool:
        """
        Save current configuration to unified config.json
        Optionally backup existing file
        """
        try:
            # Create config directory if it doesn't exist
            os.makedirs(self.config_dir, exist_ok=True)
            
            # Backup existing file if requested
            if backup_existing and os.path.exists(self.unified_config_path):
                backup_path = f"{self.unified_config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.unified_config_path, backup_path)
                logger.info(f"Backed up existing config to: {backup_path}")
            
            # Update metadata
            self.config["last_modified"] = datetime.now().isoformat()
            self.config["version"] = "2.0"
            
            # Save unified config
            with open(self.unified_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration saved to: {self.unified_config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def export_legacy_configs(self) -> bool:
        """
        Export current unified config back to legacy format files
        Useful for backup or migration
        """
        try:
            # Export wallets.json
            if self.config.get("wallets"):
                wallets_path = os.path.join(self.config_dir, "wallets.json")
                wallets_data = {"wallets": self.config["wallets"]}
                with open(wallets_path, 'w', encoding='utf-8') as f:
                    json.dump(wallets_data, f, indent=2)
                logger.info(f"Exported wallets to: {wallets_path}")
            
            # Export friends_addresses.json
            if self.config.get("friends"):
                friends_path = os.path.join(self.config_dir, "friends_addresses.json")
                friends_data = {"friends": self.config["friends"]}
                with open(friends_path, 'w', encoding='utf-8') as f:
                    json.dump(friends_data, f, indent=2)
                logger.info(f"Exported friends to: {friends_path}")
            
            # Export asset groups to streamlit directory
            streamlit_dir = os.path.join(self.config_dir, "streamlit")
            os.makedirs(streamlit_dir, exist_ok=True)
            
            for i, group in enumerate(self.get_asset_groups()):
                # Use original filename if available, otherwise generate
                filename = group.get("_source_file", f"asset_group_{i+1}.json")
                file_path = os.path.join(streamlit_dir, filename)
                
                # Remove metadata before saving
                export_group = {k: v for k, v in group.items() if not k.startswith("_")}
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_group, f, indent=2)
                logger.info(f"Exported asset group to: {file_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting legacy configs: {e}")
            return False
    
    # ==================== DEBUG METHODS ====================
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration for debugging"""
        return {
            "config_source": "unified" if os.path.exists(self.unified_config_path) else "legacy",
            "wallets_count": len(self.get_wallets()),
            "friends_count": len(self.get_friends()),
            "asset_groups_count": len(self.get_asset_groups()),
            "filters": self.get_standard_filters(),
            "config_file_exists": os.path.exists(self.unified_config_path),
            "legacy_files": {
                "wallets.json": os.path.exists(os.path.join(self.config_dir, "wallets.json")),
                "friends_addresses.json": os.path.exists(os.path.join(self.config_dir, "friends_addresses.json")),
                "streamlit_configs": len(glob.glob(os.path.join(self.config_dir, "streamlit", "*.json")))
            }
        }
    
    def validate_configuration(self) -> Dict[str, List[str]]:
        """Validate current configuration and return issues"""
        issues = {
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Check wallets
        wallets = self.get_wallets()
        if not wallets:
            issues["warnings"].append("No wallets configured")
        
        for addr, label in wallets.items():
            if not addr.startswith("0x") or len(addr) != 42:
                issues["errors"].append(f"Invalid wallet address format: {addr}")
            if not label or not label.strip():
                issues["warnings"].append(f"Empty label for wallet: {addr}")
        
        # Check friends
        friends = self.get_friends()
        for friend_id, friend_info in friends.items():
            addr = friend_info.get("address", "")
            if addr and (not addr.startswith("0x") or len(addr) != 42):
                issues["errors"].append(f"Invalid friend address format: {addr} ({friend_id})")
        
        # Check asset groups
        asset_groups = self.get_asset_groups()
        group_names = [g.get("name") for g in asset_groups]
        if len(group_names) != len(set(group_names)):
            issues["warnings"].append("Duplicate asset group names found")
        
        # Suggestions
        if not asset_groups:
            issues["suggestions"].append("Consider creating asset groups for better portfolio analysis")
        
        if len(wallets) > 5:
            issues["suggestions"].append("Consider using descriptive wallet labels for easier identification")
        
        return issues


def main():
    """Test the ConfigManager functionality"""
    print("🔧 Testing ConfigManager")
    print("=" * 50)
    
    # Initialize ConfigManager
    config_manager = ConfigManager()
    
    # Print summary
    summary = config_manager.get_config_summary()
    print(f"📊 Configuration Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("\n💰 Wallets:")
    for addr, label in config_manager.get_wallets().items():
        print(f"  {label}: {addr[:10]}...")
    
    print(f"\n👥 Friends: {len(config_manager.get_friends())}")
    
    print(f"\n🏷️ Asset Groups: {len(config_manager.get_asset_groups())}")
    for group in config_manager.get_asset_groups():
        print(f"  - {group.get('name', 'Unnamed')}")
    
    print(f"\n🔍 Standard Filters:")
    filters = config_manager.get_standard_filters()
    for key, value in filters.items():
        print(f"  {key}: {value}")
    
    # Validation
    print(f"\n✅ Configuration Validation:")
    validation = config_manager.validate_configuration()
    for category, items in validation.items():
        if items:
            print(f"  {category.upper()}: {len(items)}")
            for item in items[:3]:  # Show first 3
                print(f"    - {item}")
            if len(items) > 3:
                print(f"    ... and {len(items) - 3} more")


if __name__ == "__main__":
    main()

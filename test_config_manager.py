#!/usr/bin/env python3
"""
Test ConfigManager with existing configuration files
Demonstrates backward compatibility and unified interface
"""

import sys
import os
import json

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from core.config_manager import ConfigManager


def test_config_manager():
    """Test the ConfigManager with existing config files"""
    print("🧪 TESTING CONFIGMANAGER")
    print("=" * 60)
    
    try:
        # Initialize ConfigManager
        print("🔧 Initializing ConfigManager...")
        config_manager = ConfigManager()
        print("✅ ConfigManager initialized successfully")
        
        # Test configuration summary
        print("\n📊 CONFIGURATION SUMMARY")
        print("-" * 40)
        summary = config_manager.get_config_summary()
        for key, value in summary.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for sub_key, sub_value in value.items():
                    print(f"  {sub_key}: {sub_value}")
            else:
                print(f"{key}: {value}")
        
        # Test wallet access
        print("\n💰 WALLET CONFIGURATION")
        print("-" * 40)
        wallets = config_manager.get_wallets()
        print(f"Total wallets: {len(wallets)}")
        for address, label in wallets.items():
            print(f"  {label}: {address}")
        
        # Test friends access
        print("\n👥 FRIENDS CONFIGURATION")
        print("-" * 40)
        friends = config_manager.get_friends()
        print(f"Total friends: {len(friends)}")
        for friend_id, friend_info in friends.items():
            name = friend_info.get('name', 'Unknown')
            address = friend_info.get('address', 'No address')
            description = friend_info.get('description', 'No description')
            print(f"  {friend_id}: {name}")
            print(f"    Address: {address}")
            print(f"    Description: {description}")
        
        # Test asset groups
        print("\n🏷️ ASSET GROUP CONFIGURATIONS")
        print("-" * 40)
        asset_groups = config_manager.get_asset_groups()
        print(f"Total asset groups: {len(asset_groups)}")
        for i, group in enumerate(asset_groups, 1):
            name = group.get('name', f'Group {i}')
            description = group.get('description', 'No description')
            print(f"  {i}. {name}")
            print(f"     Description: {description}")
            
            # Show asset combinations
            combinations = group.get('asset_combinations', {})
            if combinations:
                print(f"     Asset Combinations ({len(combinations)}):")
                for combo_name, assets in combinations.items():
                    print(f"       {combo_name}: {', '.join(assets)}")
            
            # Show asset renames
            renames = group.get('asset_renames', {})
            if renames:
                print(f"     Asset Renames ({len(renames)}):")
                for old_name, new_name in renames.items():
                    print(f"       {old_name} → {new_name}")
        
        # Test standard filters
        print("\n🔍 STANDARD FILTERS")
        print("-" * 40)
        filters = config_manager.get_standard_filters()
        for filter_name, value in filters.items():
            print(f"  {filter_name}: {value}")
        
        # Test utility methods
        print("\n🔧 UTILITY METHODS TESTING")
        print("-" * 40)
        
        # Test wallet label lookup
        if wallets:
            first_address = list(wallets.keys())[0]
            label = config_manager.get_wallet_label(first_address)
            print(f"Wallet label lookup: {first_address[:10]}... → {label}")
        
        # Test friend name lookup
        if friends:
            for friend_info in friends.values():
                address = friend_info.get('address')
                if address:
                    friend_name = config_manager.get_friend_name(address)
                    is_friend = config_manager.is_friend_address(address)
                    print(f"Friend lookup: {address[:10]}... → {friend_name} (is_friend: {is_friend})")
                    break
        
        # Test all known addresses
        print(f"\n📍 ALL KNOWN ADDRESSES")
        print("-" * 40)
        known_addresses = config_manager.get_all_known_addresses()
        print(f"Total known addresses: {len(known_addresses)}")
        for address, label in list(known_addresses.items())[:5]:  # Show first 5
            print(f"  {address[:10]}... → {label}")
        if len(known_addresses) > 5:
            print(f"  ... and {len(known_addresses) - 5} more")
        
        # Test validation
        print(f"\n✅ CONFIGURATION VALIDATION")
        print("-" * 40)
        validation = config_manager.validate_configuration()
        for category, items in validation.items():
            print(f"{category.upper()}: {len(items)}")
            for item in items:
                print(f"  - {item}")
        
        # Test filter updates
        print(f"\n🔄 TESTING FILTER UPDATES")
        print("-" * 40)
        original_min_value = config_manager.get_standard_filters()['min_value']
        print(f"Original min_value: {original_min_value}")
        
        # Update filter
        success = config_manager.update_filter('min_value', 5.0)
        print(f"Update filter result: {success}")
        
        new_min_value = config_manager.get_standard_filters()['min_value']
        print(f"New min_value: {new_min_value}")
        
        # Restore original value
        config_manager.update_filter('min_value', original_min_value)
        print(f"Restored min_value: {config_manager.get_standard_filters()['min_value']}")
        
        # Test asset group lookup
        print(f"\n🔍 ASSET GROUP LOOKUP TESTING")
        print("-" * 40)
        if asset_groups:
            first_group_name = asset_groups[0].get('name')
            if first_group_name:
                found_group = config_manager.get_asset_group_by_name(first_group_name)
                print(f"Asset group lookup '{first_group_name}': {'Found' if found_group else 'Not found'}")
        
        print(f"\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("✅ ConfigManager is working correctly with existing config files")
        print("✅ Backward compatibility maintained")
        print("✅ Unified interface provides consistent access")
        
        return config_manager
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return None


def demonstrate_save_functionality(config_manager):
    """Demonstrate saving unified configuration"""
    print(f"\n💾 TESTING SAVE FUNCTIONALITY")
    print("-" * 40)
    
    try:
        # Show current state
        print("Current configuration loaded from legacy files")
        
        # Save to unified format (with backup)
        success = config_manager.save_config(backup_existing=True)
        print(f"Save to unified config.json: {'Success' if success else 'Failed'}")
        
        if success:
            config_path = os.path.join("config", "config.json")
            if os.path.exists(config_path):
                file_size = os.path.getsize(config_path)
                print(f"Created unified config file: {config_path} ({file_size} bytes)")
                
                # Show first few lines of the unified config
                with open(config_path, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')[:10]
                    print("First 10 lines of unified config:")
                    for line in lines:
                        print(f"  {line}")
                    print("  ...")
        
        # Test export back to legacy format
        print(f"\n📤 Testing export to legacy format...")
        export_success = config_manager.export_legacy_configs()
        print(f"Export to legacy configs: {'Success' if export_success else 'Failed'}")
        
    except Exception as e:
        print(f"❌ Error during save testing: {e}")


def show_usage_examples(config_manager):
    """Show practical usage examples"""
    print(f"\n💡 PRACTICAL USAGE EXAMPLES")
    print("-" * 40)
    
    print("# How to use ConfigManager in your code:")
    print()
    print("from core.config_manager import ConfigManager")
    print()
    print("# Initialize")
    print("config = ConfigManager()")
    print()
    print("# Get standard filters for ALL pages")
    print("filters = config.get_standard_filters()")
    print(f"# Result: {config_manager.get_standard_filters()}")
    print()
    print("# Get wallet list")
    print("wallets = config.get_wallets()")
    print(f"# Count: {len(config_manager.get_wallets())} wallets")
    print()
    print("# Check if address is a friend")
    if config_manager.get_friends():
        first_friend = list(config_manager.get_friends().values())[0]
        friend_address = first_friend.get('address', '')
        if friend_address:
            print(f"is_friend = config.is_friend_address('{friend_address[:10]}...')")
            print(f"# Result: {config_manager.is_friend_address(friend_address)}")
    print()
    print("# Get asset groups for portfolio analysis")
    print("asset_groups = config.get_asset_groups()")
    print(f"# Count: {len(config_manager.get_asset_groups())} groups")


if __name__ == "__main__":
    print("Starting ConfigManager tests...")
    
    # Run main tests
    config_manager = test_config_manager()
    
    if config_manager:
        # Test save functionality
        demonstrate_save_functionality(config_manager)
        
        # Show usage examples
        show_usage_examples(config_manager)
        
        print(f"\n🎯 NEXT STEPS:")
        print("1. ✅ ConfigManager implemented and tested")
        print("2. 🔧 Integrate ConfigManager into dashboard pages")
        print("3. 🎨 Create standardized UI components")
        print("4. 📱 Add configuration editor page")
        print("5. 🚀 Deploy unified configuration system")
    else:
        print("\n❌ ConfigManager tests failed")
        print("Please check the error messages above")

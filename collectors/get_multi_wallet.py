import csv
import os
import json
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from collectors.get_wallet import fetch_wallet_data, process_data

def load_wallets():
    with open('./config/wallets.json', 'r') as f:
        return json.load(f)['wallets']

def create_folders():
    """Create organized folder structure"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    folders = {
        'combined': f"./portfolio_data/{date_str}/combined"
    }
    for folder in folders.values():
        os.makedirs(folder, exist_ok=True)
    return folders

def main():
    """Process all wallets and create combined CSV"""
    print("🚀 Multi-wallet tracker starting...")
    
    WALLETS = load_wallets()
    
    folders = create_folders()
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    
    all_rows = []
    successful = 0
    
    for address, wallet_label in WALLETS.items():
        print(f"📊 Processing {wallet_label}...")
        
        data = fetch_wallet_data(address)
        if data.get('success'):
            rows = process_data(data, address, wallet_label)
            all_rows.extend(rows)
            successful += 1
            print(f"✅ {wallet_label}: {len(rows)} positions")
        else:
            print(f"❌ {wallet_label}: Failed")
    
    # Save combined CSV
    combined_file = f"{folders['combined']}/ALL_WALLETS_COMBINED_{timestamp}.csv"
    with open(combined_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['wallet_label', 'address', 'blockchain', 'coin', 'protocol', 'price', 'amount', 'usd_value', 'token_name', 'is_verified', 'logo_url'])
        writer.writeheader()
        writer.writerows(all_rows)
    
    print(f"🎉 Complete! {successful}/{len(WALLETS)} wallets, {len(all_rows)} total positions")
    print(f"📁 Saved: {combined_file}")
    
    return combined_file

if __name__ == "__main__":
    main()
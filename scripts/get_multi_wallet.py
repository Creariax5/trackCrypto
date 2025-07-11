import csv
import os
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from get_wallet import fetch_wallet_data, process_data

# Wallet addresses to track
WALLETS = {
    "0x3656ff4c11c4c8b4b77402faab8b3387e36f2e77": "Old_Wallet",
    "0x5a2ccb5b0a4dc5b7ca9c0768e6e2082be7bc6229": "Main_Wallet", 
    "0x29ea4918b83223f1eec45f242d2d96a293b2fcf3": "Coinbase_Wallet",
    "0x7ab7528984690d3d8066bac18f38133a0cfba053": "Sonic_Farm",
    "0x2463cc0b87dfc7d563b5f4fee294c49fe0603c62": "ZYF_AI"
}

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
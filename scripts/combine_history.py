import os
import csv
import glob
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from get_multi_wallet import main as get_multi_wallet

def find_combined_files():
    """Find all combined CSV files"""
    pattern = "./portfolio_data/*/combined/ALL_WALLETS_COMBINED_*.csv"
    files = glob.glob(pattern)
    files.sort(key=lambda x: os.path.getmtime(x))
    print(f"🔍 Found {len(files)} historical files")
    return files

def combine_csvs(csv_files, output_file):
    """Combine all CSV files into master file"""
    print(f"📊 Combining {len(csv_files)} files...")
    
    all_data = []
    for csv_file in csv_files:
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                file_data = list(reader)
                
                # Add timestamp from filename
                timestamp = os.path.basename(csv_file).replace('ALL_WALLETS_COMBINED_', '').replace('.csv', '')
                for row in file_data:
                    row['source_file_timestamp'] = timestamp
                
                all_data.extend(file_data)
                print(f"  ✅ {os.path.basename(csv_file)}: {len(file_data)} rows")
        except Exception as e:
            print(f"  ❌ Error reading {csv_file}: {e}")
    
    # Write master file
    headers = ['wallet_label', 'address', 'blockchain', 'coin', 'protocol', 'price', 'amount', 'usd_value', 'token_name', 'is_verified', 'logo_url', 'source_file_timestamp']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(all_data)
    
    print(f"✅ Master file created: {output_file} ({len(all_data):,} total rows)")
    return True

def main():
    """Main function"""
    print("🎯 Historical data combiner starting...")
    
    # Step 1: Get latest data
    get_multi_wallet()
    
    # Step 2: Find all files
    csv_files = find_combined_files()
    if not csv_files:
        print("❌ No files found")
        return False
    
    # Step 3: Combine into master file
    os.makedirs("./portfolio_data", exist_ok=True)
    master_file = "./portfolio_data/ALL_PORTFOLIOS_HISTORY.csv"
    
    # Remove existing master file
    if os.path.exists(master_file):
        os.remove(master_file)
    
    success = combine_csvs(csv_files, master_file)
    if success:
        print("🎉 Historical data combination complete!")
    
    return success

if __name__ == "__main__":
    main()
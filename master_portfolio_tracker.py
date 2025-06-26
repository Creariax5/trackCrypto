import os
import csv
import subprocess
import sys
import glob
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd

import get_multi_wallet_csv
import get_wallet_csv


def find_all_combined_csvs(base_folder: str = "portfolio_data") -> List[str]:
    """Find all ALL_WALLETS_COMBINED_*.csv files in the folder structure"""
    combined_files = []

    if not os.path.exists(base_folder):
        print(f"⚠️  Base folder '{base_folder}' not found")
        return combined_files

    # Search pattern for ALL_WALLETS_COMBINED files in all date folders
    pattern = os.path.join(base_folder, "*", "combined", "ALL_WALLETS_COMBINED_*.csv")
    found_files = glob.glob(pattern)

    # Sort files by modification time (oldest first)
    found_files.sort(key=lambda x: os.path.getmtime(x))

    print(f"🔍 Found {len(found_files)} combined CSV files:")
    for i, file_path in enumerate(found_files, 1):
        file_size = os.path.getsize(file_path)
        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        print(f"  {i}. {os.path.basename(file_path)} ({file_size:,} bytes, {mod_time.strftime('%d/%m/%Y %H:%M:%S')})")

    return found_files


def combine_all_csvs(csv_files: List[str], output_file: str) -> bool:
    """Combine all CSV files into one master file"""
    if not csv_files:
        print("❌ No CSV files to combine")
        return False

    print(f"\n📊 Combining {len(csv_files)} CSV files into master file...")

    all_data = []
    total_rows = 0

    # Expected headers based on the original script
    expected_headers = [
        'wallet_label',
        'address',
        'blockchain',
        'coin',
        'protocol',
        'price',
        'amount',
        'usd_value',
        'token_name',
        'is_verified',
        'logo_url'
    ]

    for i, csv_file in enumerate(csv_files, 1):
        try:
            print(f"  📄 Processing file {i}/{len(csv_files)}: {os.path.basename(csv_file)}")

            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                file_data = list(reader)

                # Add source file info to each row for tracking
                file_timestamp = os.path.basename(csv_file).replace('ALL_WALLETS_COMBINED_', '').replace('.csv', '')
                for row in file_data:
                    row['source_file_timestamp'] = file_timestamp

                all_data.extend(file_data)
                total_rows += len(file_data)
                print(f"    ✅ Added {len(file_data)} rows")

        except Exception as e:
            print(f"    ❌ Error reading {csv_file}: {e}")
            continue

    if not all_data:
        print("❌ No data found in any CSV files")
        return False

    # Update headers to include source tracking
    final_headers = expected_headers + ['source_file_timestamp']

    # Write combined data to master file
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=final_headers)
            writer.writeheader()
            writer.writerows(all_data)

        print(f"✅ Master CSV created successfully!")
        print(f"📊 Total rows combined: {total_rows:,}")
        print(f"💾 File location: {output_file}")
        print(f"📁 File size: {os.path.getsize(output_file):,} bytes")

        return True

    except Exception as e:
        print(f"❌ Error writing master CSV: {e}")
        return False


def create_master_csv_stats(master_file: str):
    """Create statistics about the master CSV file"""
    try:
        print(f"\n📈 MASTER CSV STATISTICS")
        print("=" * 50)

        # Read the master file for analysis
        df = pd.read_csv(master_file)

        # Basic stats
        print(f"Total Records: {len(df):,}")
        print(f"Unique Wallets: {df['wallet_label'].nunique()}")
        print(f"Unique Blockchains: {df['blockchain'].nunique()}")
        print(f"Unique Tokens: {df['coin'].nunique()}")
        print(f"Unique Protocols: {df['protocol'].nunique()}")

        # Date range
        timestamps = df['source_file_timestamp'].unique()
        print(f"Date Range: {len(timestamps)} different snapshots")

        # Top wallets by record count
        print(f"\n📊 Records per Wallet:")
        wallet_counts = df['wallet_label'].value_counts()
        for wallet, count in wallet_counts.head(10).items():
            print(f"  {wallet}: {count:,} records")

        # Top blockchains
        print(f"\n🔗 Records per Blockchain:")
        blockchain_counts = df['blockchain'].value_counts()
        for blockchain, count in blockchain_counts.head(10).items():
            print(f"  {blockchain}: {count:,} records")

    except ImportError:
        print("⚠️  pandas not available for detailed statistics")
    except Exception as e:
        print(f"⚠️  Could not generate statistics: {e}")


def main():
    """Main function"""
    print("🎯 MASTER PORTFOLIO TRACKER")
    print("=" * 60)
    print("This script will:")
    print("1. Run multi-wallet tracker to get latest data")
    print("2. Find all historical combined CSV files")
    print("3. Combine everything into one master CSV file")
    print("=" * 60)

    # Step 1: Run the multi-wallet script
    get_multi_wallet_csv.main()

    # Step 2: Find all combined CSV files
    print(f"\n{'=' * 60}")
    print("🔍 SEARCHING FOR COMBINED CSV FILES")
    print(f"{'=' * 60}")

    csv_files = find_all_combined_csvs()

    if not csv_files:
        print("❌ No combined CSV files found. Exiting...")
        sys.exit(1)

    # Step 3: Create master CSV file
    print(f"\n{'=' * 60}")
    print("📋 CREATING MASTER CSV FILE")
    print(f"{'=' * 60}")

    master_filename = f"portfolio_data/ALL_PORTFOLIOS_HISTORY.csv"

    # Check if master file already exists and delete it
    if os.path.exists(master_filename):
        print(f"🗑️  Deleting existing master file: {master_filename}")
        os.remove(master_filename)

    # Combine all CSV files
    success = combine_all_csvs(csv_files, master_filename)

    if success:
        # Create statistics
        create_master_csv_stats(master_filename)

        print(f"\n{'=' * 60}")
        print("🎉 MASTER PORTFOLIO TRACKER COMPLETED!")
        print(f"{'=' * 60}")
        print(f"✅ Latest data collected from multi-wallet tracker")
        print(f"📊 Combined {len(csv_files)} historical CSV files")
        print(f"💾 Master file created: {master_filename}")
        print(f"📅 Completed at: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    else:
        print("❌ Failed to create master CSV file")
        sys.exit(1)


if __name__ == "__main__":
    main()
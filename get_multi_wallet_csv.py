import csv
import sys
import time
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Import functions from the single wallet script
from get_wallet_csv import (
    fetch_portfolio_data,
    process_wallet_balances,
    process_defi_projects,
    print_summary,
    create_folder_structure
)

# Wallet addresses to track
WALLETS = {
    "0x3656ff4c11c4c8b4b77402faab8b3387e36f2e77": "Old_Wallet",
    "0x5a2ccb5b0a4dc5b7ca9c0768e6e2082be7bc6229": "Main_Wallet",
    "0x29ea4918b83223f1eec45f242d2d96a293b2fcf3": "Coinbase_Wallet",
    "0x7ab7528984690d3d8066bac18f38133a0cfba053": "Sonic_Farm",
    "0x2463cc0b87dfc7d563b5f4fee294c49fe0603c62": "ZYF_AI"
}


def create_individual_csv(rows: List[Dict[str, str]], address: str, wallet_label: str, timestamp: str, output_folder: str) -> str:
    """Create individual CSV file for each wallet"""
    if not rows:
        print(f"⚠️  No data to write for {wallet_label}")
        return ""

    # Create filename with wallet label and timestamp
    safe_label = wallet_label.replace(' ', '_').replace('/', '_')
    filename = f"{safe_label}_{address[:10]}_{timestamp}.csv"
    filepath = os.path.join(output_folder, filename)

    # Define CSV headers (multi-wallet version includes wallet_label)
    headers = [
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

    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        print(f"✅ Individual CSV created: {filepath} ({len(rows)} rows)")
        return filepath

    except Exception as e:
        print(f"❌ Error writing CSV for {wallet_label}: {e}")
        return ""


def create_combined_csv(all_data: List[Tuple[str, str, List[Dict[str, str]]]], timestamp: str, output_folder: str) -> str:
    """Create combined CSV file with all wallets"""
    all_rows = []

    for address, wallet_label, rows in all_data:
        all_rows.extend(rows)

    if not all_rows:
        print("⚠️  No data to write to combined CSV")
        return ""

    filename = f"ALL_WALLETS_COMBINED_{timestamp}.csv"
    filepath = os.path.join(output_folder, filename)

    # Define CSV headers
    headers = [
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

    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(all_rows)

        print(f"✅ Combined CSV created: {filepath} ({len(all_rows)} total rows)")
        return filepath

    except Exception as e:
        print(f"❌ Error writing combined CSV: {e}")
        return ""


def create_summary_csv(wallet_summaries: List[Dict[str, Any]], timestamp: str, output_folder: str) -> str:
    """Create summary CSV with wallet totals"""
    if not wallet_summaries:
        return ""

    filename = f"WALLET_SUMMARY_{timestamp}.csv"
    filepath = os.path.join(output_folder, filename)

    headers = [
        'wallet_label',
        'address',
        'status',
        'total_value',
        'wallet_value',
        'defi_value',
        'token_count',
        'project_count',
        'method'
    ]

    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(wallet_summaries)

        print(f"✅ Summary CSV created: {filepath}")
        return filepath

    except Exception as e:
        print(f"❌ Error writing summary CSV: {e}")
        return ""


def print_wallet_summary(address: str, wallet_label: str, data: Dict[str, Any]):
    """Print individual wallet summary"""
    summary = data.get('summary', {})

    print(f"\n{'=' * 60}")
    print(f"WALLET: {wallet_label}")
    print(f"{'=' * 60}")
    print(f"Address: {address}")
    print(f"Status: {'✅ Success' if data.get('success') else '❌ Failed'}")

    if data.get('success'):
        print(f"Total Value: ${summary.get('total_value', 0):,.2f}")
        print(f"Wallet Value: ${summary.get('wallet_value', 0):,.2f}")
        print(f"DeFi Value: ${summary.get('defi_value', 0):,.2f}")
        print(f"Token Count: {summary.get('token_count', 0)}")
        print(f"Project Count: {summary.get('project_count', 0)}")
        print(f"Method: {data.get('method', 'Unknown')}")
    else:
        print(f"Error: {data.get('error', 'Unknown error')}")


def main():
    """Main function to process all wallets"""
    print("🚀 MULTI-WALLET PORTFOLIO TRACKER")
    print("=" * 60)

    # Create organized folder structure
    folders = create_folder_structure()
    print(f"📁 Created folder structure: {folders['date']}")

    # Generate timestamp for all files
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")

    all_data = []
    wallet_summaries = []
    successful_wallets = 0
    total_portfolio_value = 0

    print(f"📊 Processing {len(WALLETS)} wallets...")

    for i, (address, wallet_label) in enumerate(WALLETS.items(), 1):
        print(f"\n🔍 [{i}/{len(WALLETS)}] Processing {wallet_label}...")

        # Fetch data using imported function
        data = fetch_portfolio_data(address)

        # Print individual summary
        print_wallet_summary(address, wallet_label, data)

        if data.get('success'):
            successful_wallets += 1
            summary = data.get('summary', {})
            total_value = summary.get('total_value', 0)
            total_portfolio_value += total_value

            # Process wallet data using imported functions with wallet_label
            wallet_rows = process_wallet_balances(data, address, wallet_label)
            defi_rows = process_defi_projects(data, address, wallet_label)
            all_rows = wallet_rows + defi_rows

            # Store for combined CSV
            all_data.append((address, wallet_label, all_rows))

            # Create individual CSV in organized folder
            create_individual_csv(all_rows, address, wallet_label, timestamp, folders['individual'])

            # Add to summary
            wallet_summaries.append({
                'wallet_label': wallet_label,
                'address': address,
                'status': 'Success',
                'total_value': f"${total_value:,.2f}",
                'wallet_value': f"${summary.get('wallet_value', 0):,.2f}",
                'defi_value': f"${summary.get('defi_value', 0):,.2f}",
                'token_count': summary.get('token_count', 0),
                'project_count': summary.get('project_count', 0),
                'method': data.get('method', 'Unknown')
            })

            print(f"✅ Processed {len(all_rows)} positions for {wallet_label}")
        else:
            # Add failed wallet to summary
            wallet_summaries.append({
                'wallet_label': wallet_label,
                'address': address,
                'status': 'Failed',
                'total_value': '$0.00',
                'wallet_value': '$0.00',
                'defi_value': '$0.00',
                'token_count': 0,
                'project_count': 0,
                'method': 'Error'
            })

        # Small delay to avoid rate limiting
        if i < len(WALLETS):
            time.sleep(1)

    # Create combined files in organized folders
    print(f"\n{'=' * 60}")
    print("📄 CREATING COMBINED FILES")
    print(f"{'=' * 60}")

    if all_data:
        create_combined_csv(all_data, timestamp, folders['combined'])

    create_summary_csv(wallet_summaries, timestamp, folders['summary'])

    # Final summary
    print(f"\n{'=' * 60}")
    print("🎉 FINAL SUMMARY")
    print(f"{'=' * 60}")
    print(f"✅ Successful wallets: {successful_wallets}/{len(WALLETS)}")
    print(f"💰 Total portfolio value: ${total_portfolio_value:,.2f}")
    print(f"📁 Files organized in: {folders['date']}")
    print(f"📊 Individual CSV files: {successful_wallets} (in {folders['individual']})")
    print(f"📋 Combined CSV: {'Yes' if all_data else 'No'} (in {folders['combined']})")
    print(f"📈 Summary CSV: Yes (in {folders['summary']})")

    print(f"\n🏁 Processing completed at {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")


if __name__ == "__main__":
    main()
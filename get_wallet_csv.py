import requests
import json
import csv
import sys
import os
from datetime import datetime
from typing import Dict, List, Any


def fetch_portfolio_data(address: str) -> Dict[str, Any]:
    """Fetch portfolio data from the webhook API"""
    url = f"https://automation-api-virid.vercel.app/api/webhook?address={address}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return {"success": False, "error": str(e)}


def process_wallet_balances(data: Dict[str, Any], address: str, wallet_label: str = None) -> List[Dict[str, str]]:
    """Process wallet token balances"""
    rows = []

    if not data.get('balances', {}).get('data'):
        return rows

    for token in data['balances']['data']:
        # Calculate USD value
        amount = token.get('amount', 0)
        price = token.get('price', 0)
        usd_value = amount * price if amount and price else 0

        row = {
            'address': address,
            'blockchain': token.get('chain', 'None').upper(),
            'coin': token.get('symbol', 'None'),
            'protocol': 'Wallet',
            'price': f"${price:,.2f}" if price else "None",
            'amount': f"{amount:.6f}" if amount else "None",
            'usd_value': f"${usd_value:,.2f}" if usd_value else "None",
            'token_name': token.get('name', 'None'),
            'is_verified': str(token.get('is_verified', False)),
            'logo_url': token.get('logo_url', 'None')
        }

        # Add wallet_label if provided (for multi-wallet usage)
        if wallet_label is not None:
            row['wallet_label'] = wallet_label

        rows.append(row)

    return rows


def process_defi_projects(data: Dict[str, Any], address: str, wallet_label: str = None) -> List[Dict[str, str]]:
    """Process DeFi project positions"""
    rows = []

    if not data.get('projects', {}).get('data'):
        return rows

    for project in data['projects']['data']:
        project_name = project.get('name', 'Unknown Protocol')
        chain = project.get('chain', 'Unknown').upper()

        for portfolio_item in project.get('portfolio_item_list', []):
            position_type = portfolio_item.get('name', 'Position')

            # Process asset tokens in the position
            for token in portfolio_item.get('asset_token_list', []):
                amount = token.get('amount', 0)
                price = token.get('price', 0)
                usd_value = amount * price if amount and price else 0

                row = {
                    'address': address,
                    'blockchain': chain,
                    'coin': token.get('symbol', 'None'),
                    'protocol': f"{project_name} ({position_type})",
                    'price': f"${price:,.2f}" if price else "None",
                    'amount': f"{amount:.6f}" if amount else "None",
                    'usd_value': f"${usd_value:,.2f}" if usd_value else "None",
                    'token_name': token.get('name', 'None'),
                    'is_verified': str(token.get('is_verified', False)),
                    'logo_url': token.get('logo_url', 'None')
                }

                # Add wallet_label if provided (for multi-wallet usage)
                if wallet_label is not None:
                    row['wallet_label'] = wallet_label

                rows.append(row)

    return rows


def create_folder_structure(base_folder: str = "portfolio_data") -> Dict[str, str]:
    """Create organized folder structure for CSV files"""
    date_str = datetime.now().strftime("%Y-%m-%d")

    folders = {
        'base': base_folder,
        'date': os.path.join(base_folder, date_str),
        'individual': os.path.join(base_folder, date_str, "individual_wallets"),
        'combined': os.path.join(base_folder, date_str, "combined"),
        'summary': os.path.join(base_folder, date_str, "summary")
    }

    # Create all folders if they don't exist
    for folder_path in folders.values():
        os.makedirs(folder_path, exist_ok=True)

    return folders


def create_csv(rows: List[Dict[str, str]], address: str, wallet_label: str = None, output_folder: str = None) -> str:
    """Create CSV file with organized folder structure"""
    if not rows:
        print("No data to write to CSV")
        return ""

    # Create folder structure if not provided
    if output_folder is None:
        folders = create_folder_structure()
        output_folder = folders['individual']

    # Generate filename with current timestamp in DD-MM-YYYY_H-MM-SS format
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")

    if wallet_label:
        safe_label = wallet_label.replace(' ', '_').replace('/', '_')
        filename = f"{safe_label}_{address[:10]}_{timestamp}.csv"
    else:
        filename = f"portfolio_{address[:10]}_{timestamp}.csv"

    # Full file path
    filepath = os.path.join(output_folder, filename)

    # Define CSV headers - include wallet_label if any row has it
    headers = ['address', 'blockchain', 'coin', 'protocol', 'price', 'amount', 'usd_value', 'token_name', 'is_verified',
               'logo_url']
    if rows and 'wallet_label' in rows[0]:
        headers.insert(0, 'wallet_label')

    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        print(f"✅ CSV created successfully: {filepath}")
        print(f"📊 Total rows: {len(rows)}")
        return filepath

    except Exception as e:
        print(f"Error writing CSV: {e}")
        return ""


def print_summary(data: Dict[str, Any], wallet_label: str = None):
    """Print portfolio summary"""
    summary = data.get('summary', {})

    print("\n" + "=" * 50)
    if wallet_label:
        print(f"PORTFOLIO SUMMARY - {wallet_label}")
    else:
        print("PORTFOLIO SUMMARY")
    print("=" * 50)
    print(f"Address: {data.get('address', 'Unknown')}")
    print(f"Total Value: ${summary.get('total_value', 0):,.2f}")
    print(f"Wallet Value: ${summary.get('wallet_value', 0):,.2f}")
    print(f"DeFi Value: ${summary.get('defi_value', 0):,.2f}")
    print(f"Token Count: {summary.get('token_count', 0)}")
    print(f"Project Count: {summary.get('project_count', 0)}")
    print(f"Method: {data.get('method', 'Unknown')}")
    print(f"Timestamp: {data.get('timestamp', 'Unknown')}")
    print("=" * 50)


def main():
    """Main function"""
    # Get address from command line argument or use default
    if len(sys.argv) > 1:
        address = sys.argv[1]
    else:
        address = "0x29ea4918b83223f1eec45f242d2d96a293b2fcf3"  # Default address

    print(f"🔍 Fetching portfolio data for: {address}")

    # Create folder structure
    folders = create_folder_structure()
    print(f"📁 Created folder structure: {folders['date']}")

    # Fetch data from API
    data = fetch_portfolio_data(address)

    if not data.get('success'):
        print(f"❌ API Error: {data.get('error', 'Unknown error')}")
        sys.exit(1)

    # Print summary
    print_summary(data)

    # Process wallet balances
    print("\n📊 Processing wallet balances...")
    wallet_rows = process_wallet_balances(data, address)
    print(f"Found {len(wallet_rows)} wallet tokens")

    # Process DeFi positions
    print("🔄 Processing DeFi positions...")
    defi_rows = process_defi_projects(data, address)
    print(f"Found {len(defi_rows)} DeFi position tokens")

    # Combine all rows
    all_rows = wallet_rows + defi_rows

    if not all_rows:
        print("❌ No portfolio data found")
        sys.exit(1)

    # Create CSV in organized folder
    print(f"\n💾 Creating CSV with {len(all_rows)} total entries...")
    filepath = create_csv(all_rows, address, output_folder=folders['individual'])

    if filepath:
        print(f"\n🎉 Successfully created: {filepath}")

        # Show first few rows as preview
        print("\n📋 Preview (first 5 rows):")
        for i, row in enumerate(all_rows[:5]):
            print(f"{i + 1}. {row['blockchain']} | {row['coin']} | {row['protocol']} | {row['usd_value']}")

    else:
        print("❌ Failed to create CSV file")


if __name__ == "__main__":
    main()
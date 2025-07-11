import requests
import csv
import os
from datetime import datetime

def fetch_wallet_data(address):
    """Fetch portfolio data from API"""
    try:
        response = requests.get(f"https://automation-api-virid.vercel.app/api/webhook?address={address}", timeout=30)
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}

def process_data(data, address, wallet_label=None):
    """Process wallet and DeFi data into CSV rows"""
    rows = []
    
    # Process wallet balances
    for token in data.get('balances', {}).get('data', []):
        rows.append({
            'wallet_label': wallet_label or address[:10],
            'address': address,
            'blockchain': token.get('chain', 'None').upper(),
            'coin': token.get('symbol', 'None'),
            'protocol': 'Wallet',
            'price': token.get('price', 0),
            'amount': token.get('amount', 0),
            'usd_value': token.get('amount', 0) * token.get('price', 0),
            'token_name': token.get('name', 'None'),
            'is_verified': str(token.get('is_verified', False)),
            'logo_url': token.get('logo_url', 'None')
        })
    
    # Process DeFi positions
    for project in data.get('projects', {}).get('data', []):
        for item in project.get('portfolio_item_list', []):
            for token in item.get('asset_token_list', []):
                rows.append({
                    'wallet_label': wallet_label or address[:10],
                    'address': address,
                    'blockchain': project.get('chain', 'None').upper(),
                    'coin': token.get('symbol', 'None'),
                    'protocol': f"{project.get('name', 'Unknown')} ({item.get('name', 'Position')})",
                    'price': token.get('price', 0),
                    'amount': token.get('amount', 0),
                    'usd_value': token.get('amount', 0) * token.get('price', 0),
                    'token_name': token.get('name', 'None'),
                    'is_verified': str(token.get('is_verified', False)),
                    'logo_url': token.get('logo_url', 'None')
                })
    
    return rows

def save_csv(rows, address, wallet_label=None):
    """Save data to CSV with timestamp"""
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    os.makedirs("./portfolio_data", exist_ok=True)
    
    filename = f"./portfolio_data/{wallet_label or address[:10]}_{timestamp}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['wallet_label', 'address', 'blockchain', 'coin', 'protocol', 'price', 'amount', 'usd_value', 'token_name', 'is_verified', 'logo_url'])
        writer.writeheader()
        writer.writerows(rows)
    
    return filename

def main(address=None):
    """Main function"""
    if not address:
        address = "0x29ea4918b83223f1eec45f242d2d96a293b2fcf3"
    
    print(f"🔍 Fetching data for {address}")
    data = fetch_wallet_data(address)
    
    if not data.get('success'):
        print(f"❌ Error: {data.get('error')}")
        return None
    
    rows = process_data(data, address)
    filename = save_csv(rows, address)
    
    print(f"✅ Saved {len(rows)} rows to {filename}")
    return filename

if __name__ == "__main__":
    main()
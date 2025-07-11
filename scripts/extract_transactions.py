import os
import json
import csv
import html
import re
from datetime import datetime
from bs4 import BeautifulSoup

def extract_json_data(soup):
    """Extract data from hidden JSON input"""
    export_input = soup.find('input', class_='export-data')
    if not export_input:
        return []
    
    json_data = html.unescape(export_input.get('value', ''))
    try:
        return json.loads(json_data)
    except json.JSONDecodeError:
        return []

def extract_table_data(soup):
    """Extract detailed data from HTML table"""
    transactions = []
    
    # Find all transaction rows
    tbody = soup.find('tbody')
    if not tbody:
        return []
    
    rows = tbody.find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 6:
            continue
            
        tx_data = {}
        
        # Chain (first cell)
        chain_cell = cells[0]
        chain_img = chain_cell.find('img')
        if chain_img:
            tx_data['chain'] = chain_img.get('aria-label', '').title()
            tx_data['chain_logo'] = chain_img.get('src', '')
        
        # Action and Date (second cell)
        action_cell = cells[1]
        action_link = action_cell.find('a')
        if action_link:
            tx_data['transaction_hash'] = action_link.get('href', '').split('/')[-1]
            action_span = action_link.find('span')
            if action_span:
                tx_data['action'] = action_span.get('title', action_span.text.strip())
        
        # Extract timestamps
        age_div = action_cell.find('div', {'data-dt-format': 'age'})
        if age_div:
            tx_data['time_ago'] = age_div.text.strip()
        
        utc_div = action_cell.find('div', {'data-dt-format': 'utc'})
        if utc_div:
            tx_data['timestamp_utc'] = utc_div.text.strip()
        
        # Asset (third cell)
        asset_cell = cells[2]
        
        # Token image and info
        token_img = asset_cell.find('img', class_='js-image-transaction-token')
        if token_img:
            tx_data['token_logo'] = token_img.get('data-js-img', '')
            tx_data['token_symbol'] = token_img.get('data-tokenalt', '')
        
        # Token link for name
        token_link = asset_cell.find('a')
        if token_link:
            tx_data['token_name'] = token_link.get('title', '')
            tx_data['token_address'] = token_link.get('href', '').split('/')[-1] if '/token/' in token_link.get('href', '') else ''
        
        # Amount and USD value
        amount_spans = asset_cell.find_all('span', class_='hash-tag')
        for span in amount_spans:
            span_title = span.get('title', span.text.strip())
            if any(symbol in span_title for symbol in ['ETH', 'USDC', 'WETH', 'WGC', 'CBBTC']):
                tx_data['amount_full'] = span_title
                tx_data['amount_display'] = span.text.strip()
                # Check if it's positive or negative
                if 'text-success' in span.get('class', []):
                    tx_data['amount_direction'] = 'positive'
                elif span_title.startswith('-'):
                    tx_data['amount_direction'] = 'negative'
                else:
                    tx_data['amount_direction'] = 'neutral'
        
        # USD value
        usd_div = asset_cell.find('div', class_='small')
        if usd_div:
            usd_title = usd_div.get('title', usd_div.text.strip())
            if '$' in usd_title:
                tx_data['usd_value_full'] = usd_title
                tx_data['usd_value_display'] = usd_div.text.strip()
        
        # From (fourth cell)
        from_cell = cells[3]
        from_spans = from_cell.find_all('span')
        for span in from_spans:
            address = span.get('title', '')
            if address.startswith('0x'):
                tx_data['from_address'] = address
                tx_data['from_address_short'] = span.text.strip()
                break
        
        from_info_div = from_cell.find('div', class_='small')
        if from_info_div:
            tx_data['from_info'] = from_info_div.get('title', from_info_div.text.strip())
        
        # To (fifth cell)
        to_cell = cells[4]
        to_links = to_cell.find_all('a')
        to_spans = to_cell.find_all('span')
        
        for link in to_links:
            address = link.get('title', '')
            if address.startswith('0x'):
                tx_data['to_address'] = address
                tx_data['to_address_short'] = link.text.strip()
                break
        
        for span in to_spans:
            address = span.get('title', '')
            if address.startswith('0x'):
                tx_data['to_address'] = address
                tx_data['to_address_short'] = span.text.strip()
                break
        
        to_info_div = to_cell.find('div', class_='small')
        if to_info_div:
            tx_data['to_info'] = to_info_div.get('title', to_info_div.text.strip())
        
        transactions.append(tx_data)
    
    return transactions

def merge_transaction_data(json_data, table_data):
    """Merge JSON and table data"""
    merged = []
    
    # Create lookup by hash for JSON data
    json_lookup = {}
    for tx in json_data:
        # Clean hash (remove 0x0x prefix if present)
        hash_key = tx.get('Hash', '').replace('0x0x', '0x')
        json_lookup[hash_key] = tx
    
    for table_tx in table_data:
        # Clean hash for lookup
        hash_key = table_tx.get('transaction_hash', '').replace('0x0x', '0x')
        
        # Start with table data (more detailed)
        merged_tx = table_tx.copy()
        
        # Add JSON data if available
        if hash_key in json_lookup:
            json_tx = json_lookup[hash_key]
            for key, value in json_tx.items():
                # Use json_ prefix for JSON-specific fields to avoid conflicts
                merged_tx[f'json_{key.lower().replace(" ", "_")}'] = value
        
        merged.append(merged_tx)
    
    return merged

def extract_transactions_from_html(html_file_path):
    """Extract all transaction data from HTML file"""
    with open(html_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # Extract from both sources
    json_data = extract_json_data(soup)
    table_data = extract_table_data(soup)
    
    # Merge the data
    merged_data = merge_transaction_data(json_data, table_data)
    
    print(f"   📊 JSON records: {len(json_data)}, Table records: {len(table_data)}, Merged: {len(merged_data)}")
    
    return merged_data

def process_transactions():
    """Process all HTML files and create CSV"""
    print("🔄 Processing transaction HTML files...")
    
    # Create output directory
    output_dir = "./portfolio_data/transactions/processed"
    os.makedirs(output_dir, exist_ok=True)
    
    # Source directory
    source_dir = "./portfolio_data/transactions/download"
    
    if not os.path.exists(source_dir):
        print(f"❌ Source directory not found: {source_dir}")
        return
    
    all_transactions = []
    processed_files = 0
    
    # Process each HTML file
    for filename in os.listdir(source_dir):
        if filename.endswith('.html'):
            wallet_address = filename.replace('.html', '')
            file_path = os.path.join(source_dir, filename)
            
            print(f"📄 Processing {filename}...")
            transactions = extract_transactions_from_html(file_path)
            
            if transactions:
                # Add wallet info to each transaction
                for tx in transactions:
                    tx['wallet_address'] = wallet_address
                    tx['source_file'] = filename
                    tx['extraction_timestamp'] = datetime.now().isoformat()
                
                all_transactions.extend(transactions)
                processed_files += 1
                print(f"✅ Extracted {len(transactions)} transactions")
            else:
                print(f"⚠️  No transactions found in {filename}")
    
    if all_transactions:
        # Create CSV with all fields
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        csv_file = os.path.join(output_dir, f"ALL_TRANSACTIONS_{timestamp}.csv")
        
        # Get all possible field names
        fieldnames = set()
        for tx in all_transactions:
            fieldnames.update(tx.keys())
        
        # Sort fieldnames for better organization
        priority_fields = [
            'wallet_address', 'transaction_hash', 'chain', 'action', 
            'timestamp_utc', 'time_ago', 'token_symbol', 'token_name',
            'amount_full', 'amount_display', 'amount_direction', 
            'usd_value_full', 'usd_value_display',
            'from_address', 'from_address_short', 'from_info',
            'to_address', 'to_address_short', 'to_info'
        ]
        
        # Start with priority fields, then add remaining ones
        fieldnames = priority_fields + [f for f in sorted(fieldnames) if f not in priority_fields]
        
        # Write CSV
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_transactions)
        
        print(f"🎉 Success! Processed {processed_files} files")
        print(f"📊 Total transactions: {len(all_transactions)}")
        print(f"💾 Saved: {csv_file}")
        print(f"🔢 CSV columns: {len(fieldnames)}")
        
        return csv_file
    else:
        print("❌ No transactions found in any file")
        return None

def main():
    """Main function"""
    return process_transactions()

if __name__ == "__main__":
    main()
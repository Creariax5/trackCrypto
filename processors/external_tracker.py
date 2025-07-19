#!/usr/bin/env python3
"""
Fixed Simple Tracker - Auto-detects latest CSV file and exports external transactions
"""
import pandas as pd
import glob
import os
import re
import json
from datetime import datetime

# Add project root to Python path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_friends_addresses():
    """Load friends addresses from JSON file"""
    try:
        with open('./config/friends_addresses.json', 'r') as f:
            data = json.load(f)
            friends_map = {}
            for friend_id, info in data.get('friends', {}).items():
                address = info.get('address', '').lower()
                name = info.get('name', friend_id)
                friends_map[address] = name
            return friends_map
    except FileNotFoundError:
        print("ℹ️  No friends_addresses.json found")
        return {}
    except Exception as e:
        print(f"⚠️  Error loading friends addresses: {e}")
        return {}

def find_latest_csv():
    """Find the latest CSV file with historical data"""
    folder = './portfolio_data/transactions/processed/'
    pattern = os.path.join(folder, '*_with_historical.csv')
    csv_files = glob.glob(pattern)
    
    if not csv_files:
        print("❌ No CSV files found!")
        return None
    
    # Get the most recent file
    latest_file = max(csv_files, key=os.path.getmtime)
    return latest_file

def simple_tracker():
    print("🚀 FIXED SIMPLE TRACKER")
    print("=" * 40)
    
    # Find the CSV file
    csv_file = find_latest_csv()
    if not csv_file:
        return
    
    print(f"📄 Using: {os.path.basename(csv_file)}")
    
    # Load data
    df = pd.read_csv(csv_file)
    print(f"📊 Total transactions: {len(df)}")
    
    # Debug: Print column names to verify
    print(f"🔍 Available columns: {list(df.columns)}")
    
    # Clean USD values
    def clean_usd(val):
        if pd.isna(val) or val == '':
            return 0.0
        try:
            return float(str(val).replace('$', '').replace(',', ''))
        except:
            return 0.0
    
    # Use historical price first, then fallback
    df['usd'] = df['historical_value_usd'].apply(clean_usd)
    df.loc[df['usd'] == 0, 'usd'] = df['usd_value_full'].apply(clean_usd)
    
    # Clean direction
    df['dir'] = df['amount_direction'].map({'positive': 'IN', 'negative': 'OUT'})
    
    # Filter to transactions with value
    df_value = df[(df['usd'] > 0) & (df['dir'].notna())].copy()
    print(f"📊 With USD value: {len(df_value)}")
    
    # Load friends addresses
    friends_map = load_friends_addresses()
    print(f"👥 Loaded {len(friends_map)} friend addresses")
    
    # Find external transactions with BETTER patterns
    def find_exchange(text, address, direction):
        if pd.isna(text):
            text = ""
        else:
            text = str(text).lower()
        
        # Check if it's a friend's address
        if pd.notna(address):
            address_clean = str(address).lower()
            if address_clean in friends_map:
                friend_name = friends_map[address_clean]
                return f"friend_{friend_name.lower()}"
        
        # EXCLUDE fees and proxy wallets
        if 'fees' in text or 'fee' in text or 'proxy' in text or 'flash' in text:
            return None
        
        # Real exchange patterns
        if re.search(r'coinbase\s+\d+', text):
            return 'coinbase'
        if 'bybit' in text and 'hot' in text:
            return 'bybit'
        if re.search(r'binance\s+\d+', text):
            return 'binance'
        
        return None
    
    # Find ALL external transactions
    external_in = 0
    external_out = 0
    external_details = []
    
    for _, row in df_value.iterrows():
        direction = row['dir']
        amount = row['usd']
        
        exchange = None
        info_source = ""
        info_text = ""
        address_used = ""
        
        if direction == 'IN':
            # Check FROM fields for where money came from
            for field in ['from_info', 'json_from_info']:
                info = row.get(field, '')
                address = row.get('from_address', '')
                exchange = find_exchange(info, address, direction)
                if exchange:
                    info_source = field
                    info_text = str(info) if pd.notna(info) else ""
                    address_used = str(address) if pd.notna(address) else ""
                    break
        
        elif direction == 'OUT':
            # Check TO fields for where money went
            for field in ['to_info', 'json_to_info']:
                info = row.get(field, '')
                address = row.get('to_address', '')
                exchange = find_exchange(info, address, direction)
                if exchange:
                    info_source = field
                    info_text = str(info) if pd.notna(info) else ""
                    address_used = str(address) if pd.notna(address) else ""
                    break
        
        if exchange:
            if direction == 'IN':
                external_in += amount
            else:
                external_out += amount
            
            # FIXED: Extract and clean token amount using correct column names
            token_amount = ''
            # Try amount_full first, then amount_display
            for amt_col in ['amount_full', 'amount_display']:
                if amt_col in row and pd.notna(row[amt_col]):
                    try:
                        # Clean token amount (remove any non-numeric characters except decimal point and minus)
                        token_amount_clean = re.sub(r'[^\d.-]', '', str(row[amt_col]))
                        token_amount = float(token_amount_clean) if token_amount_clean else ''
                        break
                    except:
                        token_amount = str(row[amt_col])
                        break
            
            # FIXED: Extract timestamp and date using correct column names
            timestamp_val = row.get('timestamp_utc', '')  # Fixed: was 'timestamp'
            
            # Convert timestamp_utc to readable date if needed
            date_val = ''
            if pd.notna(timestamp_val) and timestamp_val != '':
                try:
                    # If it's already a formatted date string, use it
                    if isinstance(timestamp_val, str) and any(x in timestamp_val for x in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                                                                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                        date_val = timestamp_val
                    else:
                        # Try to parse as timestamp
                        if str(timestamp_val).replace('.', '').isdigit():
                            ts_num = float(timestamp_val)
                            # Handle both seconds and milliseconds timestamps
                            if ts_num > 1e12:  # milliseconds
                                ts_num = ts_num / 1000
                            date_val = datetime.fromtimestamp(ts_num).strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            date_val = str(timestamp_val)
                except Exception as e:
                    print(f"⚠️  Could not parse timestamp {timestamp_val}: {e}")
                    date_val = str(timestamp_val)
            
            # FIXED: Try to get block number from transaction hash or other fields
            block_number = ''
            # Check if there's a block-related field, or use transaction_hash as identifier
            for block_field in ['block_number', 'json_hash', 'transaction_hash']:
                if block_field in row and pd.notna(row[block_field]):
                    block_number = str(row[block_field])
                    break
            
            external_details.append({
                'direction': direction,
                'amount_usd': round(amount, 2),
                'token_symbol': row.get('token_symbol', ''),
                'token_amount': token_amount,  # Now properly extracted
                'exchange_or_friend': exchange,
                'info_source_field': info_source,
                'info_text': info_text,
                'address': address_used,
                'wallet_address': row.get('wallet_address', ''),
                'transaction_hash': row.get('transaction_hash', ''),
                'block_number': block_number,  # Now properly extracted
                'timestamp': timestamp_val,  # Now using timestamp_utc
                'date': date_val,  # Now properly converted
                'chain': row.get('chain', ''),  # Added chain info
                'action': row.get('action', ''),  # Added action info
                'original_row_index': row.name
            })
    
    # Show results
    net = external_in - external_out
    
    print(f"\n💰 RESULTS:")
    print(f"External IN:  ${external_in:>10,.2f}")
    print(f"External OUT: ${external_out:>10,.2f}")
    print(f"NET:          ${net:>10,.2f}")
    
    # Create DataFrame from external transactions
    if external_details:
        external_df = pd.DataFrame(external_details)
        
        # Generate output filename in processed folder
        output_folder = './portfolio_data/transactions/processed/'
        os.makedirs(output_folder, exist_ok=True)  # Ensure folder exists
        output_file = os.path.join(output_folder, f"external_transactions.csv")
        
        # Save to CSV
        external_df.to_csv(output_file, index=False)
        print(f"\n💾 External transactions saved to: {output_file}")
        print(f"📊 Total external transactions exported: {len(external_details)}")
        
        # Debug: Show sample of extracted data
        print(f"\n🔍 SAMPLE EXTRACTED DATA:")
        for i, tx in enumerate(external_details[:3]):  # Show first 3
            print(f"Transaction {i+1}:")
            print(f"  Token Amount: {tx['token_amount']}")
            print(f"  Timestamp: {tx['timestamp']}")
            print(f"  Date: {tx['date']}")
            print(f"  Block: {tx['block_number']}")
            print()
        
        # Show summary by exchange
        print(f"\n🔍 SUMMARY BY EXCHANGE/FRIEND:")
        by_exchange = external_df.groupby('exchange_or_friend').agg({
            'amount_usd': ['sum', 'count'],
            'direction': lambda x: f"IN: {sum(x=='IN')}, OUT: {sum(x=='OUT')}"
        }).round(2)
        
        by_exchange.columns = ['total_usd', 'transaction_count', 'direction_breakdown']
        print(by_exchange.to_string())
        
    else:
        print("\n❌ No external transactions found to export")
    
    # Show all external transactions
    print(f"\n🔍 ALL EXTERNAL TRANSACTIONS ({len(external_details)}):")
    
    # Group by exchange
    by_exchange = {}
    for tx in external_details:
        exchange = tx['exchange_or_friend']
        if exchange not in by_exchange:
            by_exchange[exchange] = {'in': 0, 'out': 0, 'transactions': []}
        
        if tx['direction'] == 'IN':
            by_exchange[exchange]['in'] += tx['amount_usd']
        else:
            by_exchange[exchange]['out'] += tx['amount_usd']
        
        by_exchange[exchange]['transactions'].append(tx)
    
    for exchange, data in by_exchange.items():
        exchange_net = data['in'] - data['out']
        print(f"\n{exchange.upper()}:")
        print(f"   IN:  ${data['in']:>10,.2f}")
        print(f"   OUT: ${data['out']:>10,.2f}")
        print(f"   NET: ${exchange_net:>10,.2f}")
        
        # Show top transactions
        for tx in sorted(data['transactions'], key=lambda x: x['amount_usd'], reverse=True)[:5]:
            print(f"     {tx['direction']}: ${tx['amount_usd']:>8.2f} {tx['token_symbol']:<8} ({tx['token_amount']})")
        
        if len(data['transactions']) > 5:
            print(f"     ... and {len(data['transactions']) - 5} more transactions")

def main():
    simple_tracker()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Final Simple Tracker - Auto-detects latest CSV file
"""
import pandas as pd
import glob
import os
import re

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
    print("🚀 FINAL SIMPLE TRACKER")
    print("=" * 40)
    
    # Find the CSV file
    csv_file = find_latest_csv()
    if not csv_file:
        return
    
    print(f"📄 Using: {os.path.basename(csv_file)}")
    
    # Load data
    df = pd.read_csv(csv_file)
    print(f"📊 Total transactions: {len(df)}")
    
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
    
    # Find external transactions with BETTER patterns
    def find_exchange(text, direction):
        if pd.isna(text):
            return None
        
        text = str(text).lower()
        
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
        
        if direction == 'IN':
            # Check FROM fields for where money came from
            for field in ['from_info', 'json_from_info']:
                info = row.get(field, '')
                exchange = find_exchange(info, direction)
                if exchange:
                    info_source = f"{field}: {info}"
                    break
        
        elif direction == 'OUT':
            # Check TO fields for where money went
            for field in ['to_info', 'json_to_info']:
                info = row.get(field, '')
                exchange = find_exchange(info, direction)
                if exchange:
                    info_source = f"{field}: {info}"
                    break
        
        if exchange:
            if direction == 'IN':
                external_in += amount
            else:
                external_out += amount
            
            external_details.append({
                'direction': direction,
                'amount': amount,
                'token': row['token_symbol'],
                'exchange': exchange,
                'info': info_source,
                'wallet': row['wallet_address']
            })
    
    # Show results
    net = external_in - external_out
    
    print(f"\n💰 RESULTS:")
    print(f"External IN:  ${external_in:>10,.2f}")
    print(f"External OUT: ${external_out:>10,.2f}")
    print(f"NET:          ${net:>10,.2f}")
    
    print(f"\n✅ TARGET: $2,100 - $2,400")
    success = 2000 <= net <= 2500
    print(f"STATUS: {'🎉 SUCCESS!' if success else '⚠️ Still missing money'}")
    
    # Show all external transactions
    print(f"\n🔍 ALL EXTERNAL TRANSACTIONS ({len(external_details)}):")
    
    # Group by exchange
    by_exchange = {}
    for tx in external_details:
        exchange = tx['exchange']
        if exchange not in by_exchange:
            by_exchange[exchange] = {'in': 0, 'out': 0, 'transactions': []}
        
        if tx['direction'] == 'IN':
            by_exchange[exchange]['in'] += tx['amount']
        else:
            by_exchange[exchange]['out'] += tx['amount']
        
        by_exchange[exchange]['transactions'].append(tx)
    
    for exchange, data in by_exchange.items():
        exchange_net = data['in'] - data['out']
        print(f"\n{exchange.upper()}:")
        print(f"   IN:  ${data['in']:>10,.2f}")
        print(f"   OUT: ${data['out']:>10,.2f}")
        print(f"   NET: ${exchange_net:>10,.2f}")
        
        # Show transactions
        for tx in sorted(data['transactions'], key=lambda x: x['amount'], reverse=True):
            print(f"     {tx['direction']}: ${tx['amount']:>8.2f} {tx['token']:<8}")
    
    # If not successful, show debug info
    if not success:
        print(f"\n🔍 MISSING MONEY ANALYSIS:")
        missing = 2200 - net
        print(f"Missing: ~${missing:,.2f}")
        
        # Look for large inflows without exchange labels
        print(f"\n💰 LARGE INFLOWS (>$100) WITHOUT EXCHANGE LABELS:")
        large_inflows = df_value[(df_value['dir'] == 'IN') & (df_value['usd'] > 100)].copy()
        large_inflows = large_inflows.sort_values('usd', ascending=False)
        
        found_unlabeled = 0
        for _, row in large_inflows.head(20).iterrows():
            # Check if this already has exchange label
            has_exchange = False
            for field in ['from_info', 'json_from_info']:
                info = row.get(field, '')
                if find_exchange(info, 'IN'):
                    has_exchange = True
                    break
            
            if not has_exchange:
                amount = row['usd']
                token = row['token_symbol']
                from_info = row.get('from_info', '')
                json_from_info = row.get('json_from_info', '')
                
                print(f"   ${amount:>8.2f} {token:<8} | from_info: {from_info} | json_from_info: {json_from_info}")
                found_unlabeled += amount
        
        print(f"\nUnlabeled large inflows: ${found_unlabeled:,.2f}")
        if found_unlabeled > missing * 0.8:
            print(f"💡 Most missing money is in unlabeled large inflows!")
            print(f"💡 Need to improve exchange pattern detection")

def main():
    simple_tracker()

if __name__ == "__main__":
    main()
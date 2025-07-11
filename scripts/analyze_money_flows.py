#!/usr/bin/env python3
"""
🏦 Crypto Money Flow Analyzer

Analyzes transaction data to calculate TRUE money in/out flows.
Detects swaps, cross-wallet transfers, and external deposits/withdrawals.

Usage: python scripts/analyze_money_flows.py
"""

import pandas as pd
import json
import os
from datetime import datetime, timedelta

def load_wallet_config():
    """Load wallet addresses from config file"""
    try:
        with open('./config/wallets.json', 'r') as f:
            config = json.load(f)
        return config['wallets']
    except FileNotFoundError:
        print("❌ Config file not found: ./config/wallets.json")
        return {}

def parse_usd_value(usd_str):
    """Extract numeric value from USD string like '$1,234.56'"""
    if pd.isna(usd_str) or usd_str == '' or usd_str == 'N/A':
        return 0.0
    
    # Clean string: remove $, commas, spaces
    clean_str = str(usd_str).replace('$', '').replace(',', '').replace(' ', '')
    try:
        return float(clean_str)
    except:
        return 0.0

def parse_amount_direction(direction_str, amount_full_str):
    """Standardize amount direction"""
    # First try the direction column
    if pd.notna(direction_str):
        direction = str(direction_str).strip().lower()
        if direction in ['positive', '+', 'in']:
            return 'IN'
        elif direction in ['negative', '-', 'out']:
            return 'OUT'
        elif direction in ['neutral', '0']:
            return 'NEUTRAL'
    
    # If direction is NaN, try to extract from amount_full
    if pd.notna(amount_full_str):
        amount_str = str(amount_full_str).strip()
        if amount_str.startswith('+'):
            return 'IN'
        elif amount_str.startswith('-'):
            return 'OUT'
        elif amount_str.startswith('0 ') or amount_str == '0':
            return 'NEUTRAL'
    
    return 'UNKNOWN'

def is_cross_wallet_transfer(row, wallet_addresses):
    """Check if transaction is between user's own wallets"""
    wallet_set = set(addr.lower() for addr in wallet_addresses)
    
    to_addr = str(row.to_address).lower() if pd.notna(row.to_address) else ''
    from_addr = str(row.from_address).lower() if pd.notna(row.from_address) else ''
    
    # If either to or from address is one of user's wallets (excluding current wallet)
    current_wallet = row.wallet_address.lower()
    other_wallets = wallet_set - {current_wallet}
    
    return to_addr in other_wallets or from_addr in other_wallets

def values_are_similar(val1, val2, tolerance=0.15):
    """Check if two USD values are similar (within tolerance for slippage/fees)"""
    if val1 == 0 and val2 == 0:
        return True
    if val1 == 0 or val2 == 0:
        return abs(val1 - val2) < 10  # Allow $10 difference if one is zero
    
    # Calculate percentage difference
    avg_value = (val1 + val2) / 2
    diff_pct = abs(val1 - val2) / avg_value
    return diff_pct <= tolerance

def calculate_confidence_score(out_row, in_row, time_diff_minutes):
    """Calculate confidence that two transactions are a swap pair"""
    confidence = 50  # Base confidence
    
    # Time factor (closer = higher confidence)
    if time_diff_minutes <= 1:
        confidence += 30
    elif time_diff_minutes <= 5:
        confidence += 20
    elif time_diff_minutes <= 15:
        confidence += 10
    
    # Value similarity factor
    out_val = out_row.final_usd_value
    in_val = in_row.final_usd_value
    
    if out_val > 0 and in_val > 0:
        diff_pct = abs(out_val - in_val) / ((out_val + in_val) / 2)
        if diff_pct <= 0.02:  # Within 2%
            confidence += 25
        elif diff_pct <= 0.05:  # Within 5%
            confidence += 15
        elif diff_pct <= 0.15:  # Within 15%
            confidence += 10
    
    # Both have historical prices
    if (out_row.historical_price_usd != 'N/A' and 
        in_row.historical_price_usd != 'N/A'):
        confidence += 15
    
    return min(confidence, 95)

def detect_transaction_flows(df, wallets):
    """Main function to analyze transaction flows"""
    print(f"🔄 Analyzing {len(df)} transactions...")
    
    # Add wallet labels
    wallet_map = {addr.lower(): label for addr, label in wallets.items()}
    df['wallet_label'] = df['wallet_address'].str.lower().map(wallet_map)
    
    # Convert timestamp to datetime
    try:
        df['timestamp_dt'] = pd.to_datetime(df['timestamp_utc'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    except:
        df['timestamp_dt'] = pd.to_datetime(df['timestamp_utc'], errors='coerce')
    
    # Parse USD values - use historical if available, otherwise original
    df['usd_value_numeric'] = df['usd_value_full'].apply(parse_usd_value)
    df['historical_usd_numeric'] = df['historical_value_usd'].apply(parse_usd_value)
    df['final_usd_value'] = df.apply(
        lambda row: row['historical_usd_numeric'] if row['historical_usd_numeric'] > 0 
        else row['usd_value_numeric'], axis=1
    )
    
    # Standardize amount direction
    df['direction_clean'] = df.apply(
        lambda row: parse_amount_direction(row['amount_direction'], row['amount_full']), axis=1
    )
    
    # Initialize flow analysis columns
    df['flow_type'] = 'UNKNOWN'
    df['paired_with_hash'] = ''
    df['net_money_flow'] = 0.0
    df['is_external_flow'] = True
    df['confidence_score'] = 0
    df['notes'] = ''
    
    # Sort by wallet and timestamp
    df = df.sort_values(['wallet_address', 'timestamp_dt']).reset_index(drop=True)
    
    processed_hashes = set()
    wallet_addresses = list(wallets.keys())
    
    # Process each wallet separately
    for wallet_addr in df['wallet_address'].unique():
        wallet_df = df[df['wallet_address'] == wallet_addr].copy().reset_index(drop=True)
        wallet_indices = df[df['wallet_address'] == wallet_addr].index
        
        print(f"   📱 Processing {len(wallet_df)} transactions for {wallet_map.get(wallet_addr.lower(), wallet_addr)}")
        
        for i, (orig_idx, row) in enumerate(zip(wallet_indices, wallet_df.itertuples())):
            if row.transaction_hash in processed_hashes:
                continue
            
            # Skip neutral/zero-value transactions
            if row.direction_clean == 'NEUTRAL' or row.final_usd_value == 0:
                df.loc[orig_idx, 'flow_type'] = 'NEUTRAL'
                df.loc[orig_idx, 'is_external_flow'] = False
                df.loc[orig_idx, 'net_money_flow'] = 0.0
                df.loc[orig_idx, 'confidence_score'] = 95
                df.loc[orig_idx, 'notes'] = 'Zero-value or neutral transaction'
                processed_hashes.add(row.transaction_hash)
                continue
            
            # Skip unknown direction transactions with no value
            if row.direction_clean == 'UNKNOWN':
                df.loc[orig_idx, 'flow_type'] = 'UNKNOWN'
                df.loc[orig_idx, 'net_money_flow'] = 0.0
                df.loc[orig_idx, 'confidence_score'] = 0
                df.loc[orig_idx, 'notes'] = 'Unable to determine transaction direction'
                processed_hashes.add(row.transaction_hash)
                continue
            
            # Check for cross-wallet transfer
            if is_cross_wallet_transfer(row, wallet_addresses):
                df.loc[orig_idx, 'flow_type'] = 'CROSS_WALLET'
                df.loc[orig_idx, 'is_external_flow'] = False
                df.loc[orig_idx, 'net_money_flow'] = 0.0
                df.loc[orig_idx, 'confidence_score'] = 95
                df.loc[orig_idx, 'notes'] = 'Transfer between own wallets'
                processed_hashes.add(row.transaction_hash)
                continue
            
            # Look for swap pairs (OUT followed by IN within time window)
            if row.direction_clean == 'OUT':
                pair_found = False
                time_window_end = row.timestamp_dt + timedelta(minutes=15)
                
                # Look for matching IN transaction
                for j in range(i + 1, len(wallet_df)):
                    if j >= len(wallet_indices):
                        break
                        
                    potential_pair = wallet_df.iloc[j]
                    pair_orig_idx = wallet_indices[j]
                    
                    if potential_pair.transaction_hash in processed_hashes:
                        continue
                    if potential_pair.timestamp_dt > time_window_end:
                        break
                    
                    if potential_pair.direction_clean == 'IN':
                        # Check if values are similar
                        if values_are_similar(row.final_usd_value, potential_pair.final_usd_value):
                            # Found swap pair!
                            time_diff = (potential_pair.timestamp_dt - row.timestamp_dt).total_seconds() / 60
                            confidence = calculate_confidence_score(row, potential_pair, time_diff)
                            
                            # Handle unknown token values
                            if row.final_usd_value == 0 and potential_pair.final_usd_value > 0:
                                # Use IN value for both
                                swap_value = potential_pair.final_usd_value
                            elif potential_pair.final_usd_value == 0 and row.final_usd_value > 0:
                                # Use OUT value for both
                                swap_value = row.final_usd_value
                            else:
                                swap_value = (row.final_usd_value + potential_pair.final_usd_value) / 2
                            
                            # Mark as swap pair
                            df.loc[orig_idx, 'flow_type'] = 'SWAP_OUT'
                            df.loc[pair_orig_idx, 'flow_type'] = 'SWAP_IN'
                            df.loc[orig_idx, 'paired_with_hash'] = potential_pair.transaction_hash
                            df.loc[pair_orig_idx, 'paired_with_hash'] = row.transaction_hash
                            df.loc[orig_idx, 'is_external_flow'] = False
                            df.loc[pair_orig_idx, 'is_external_flow'] = False
                            df.loc[orig_idx, 'net_money_flow'] = 0.0
                            df.loc[pair_orig_idx, 'net_money_flow'] = 0.0
                            df.loc[orig_idx, 'confidence_score'] = confidence
                            df.loc[pair_orig_idx, 'confidence_score'] = confidence
                            df.loc[orig_idx, 'notes'] = f"Swapped ${swap_value:.2f} to {potential_pair.token_symbol}"
                            df.loc[pair_orig_idx, 'notes'] = f"Swapped ${swap_value:.2f} from {row.token_symbol}"
                            
                            processed_hashes.add(row.transaction_hash)
                            processed_hashes.add(potential_pair.transaction_hash)
                            pair_found = True
                            break
                
                if not pair_found:
                    # External money out
                    df.loc[orig_idx, 'flow_type'] = 'MONEY_OUT'
                    df.loc[orig_idx, 'net_money_flow'] = -row.final_usd_value
                    df.loc[orig_idx, 'confidence_score'] = 85
                    df.loc[orig_idx, 'notes'] = f"External withdrawal: {row.token_symbol}"
                    processed_hashes.add(row.transaction_hash)
            
            elif row.direction_clean == 'IN':
                if row.transaction_hash not in processed_hashes:
                    # External money in
                    df.loc[orig_idx, 'flow_type'] = 'MONEY_IN'
                    df.loc[orig_idx, 'net_money_flow'] = row.final_usd_value
                    df.loc[orig_idx, 'confidence_score'] = 85
                    df.loc[orig_idx, 'notes'] = f"External deposit: {row.token_symbol}"
                    processed_hashes.add(row.transaction_hash)
    
    return df

def create_wallet_summary(flow_df, wallets):
    """Create summary of money flows per wallet"""
    summaries = []
    
    for wallet_addr, wallet_label in wallets.items():
        wallet_df = flow_df[flow_df['wallet_address'].str.lower() == wallet_addr.lower()]
        
        if wallet_df.empty:
            continue
        
        # Calculate flows
        money_in = wallet_df[wallet_df['flow_type'] == 'MONEY_IN']['net_money_flow'].sum()
        money_out = abs(wallet_df[wallet_df['flow_type'] == 'MONEY_OUT']['net_money_flow'].sum())
        net_investment = money_in - money_out
        
        # Count transactions
        total_txns = len(wallet_df)
        swaps = len(wallet_df[wallet_df['flow_type'].isin(['SWAP_IN', 'SWAP_OUT'])]) // 2
        cross_wallet = len(wallet_df[wallet_df['flow_type'] == 'CROSS_WALLET'])
        neutral = len(wallet_df[wallet_df['flow_type'] == 'NEUTRAL'])
        unknown = len(wallet_df[wallet_df['flow_type'] == 'UNKNOWN'])
        unknown_value = len(wallet_df[wallet_df['final_usd_value'] == 0])
        
        summary = {
            'wallet_address': wallet_addr,
            'wallet_label': wallet_label,
            'total_money_deposited': money_in,
            'total_money_withdrawn': money_out,
            'net_investment': net_investment,
            'current_wallet_value': 0,  # To be filled from portfolio data
            'true_pnl': 0,  # current_value - net_investment
            'true_pnl_percentage': 0,
            'first_activity_date': wallet_df['timestamp_utc'].min() if not wallet_df.empty else '',
            'last_activity_date': wallet_df['timestamp_utc'].max() if not wallet_df.empty else '',
            'total_transactions': total_txns,
            'external_deposits': len(wallet_df[wallet_df['flow_type'] == 'MONEY_IN']),
            'external_withdrawals': len(wallet_df[wallet_df['flow_type'] == 'MONEY_OUT']),
            'swaps_detected': swaps,
            'cross_wallet_transfers': cross_wallet,
            'neutral_transactions': neutral,
            'unknown_transactions': unknown,
            'unknown_value_transactions': unknown_value
        }
        summaries.append(summary)
    
    return pd.DataFrame(summaries)

def load_latest_transaction_file():
    """Find the latest transaction file with historical prices"""
    transactions_dir = './portfolio_data/transactions/processed/'
    
    if not os.path.exists(transactions_dir):
        print(f"❌ Directory not found: {transactions_dir}")
        return None
    
    # Look for files with historical prices
    files = [f for f in os.listdir(transactions_dir) 
             if f.endswith('_with_historical.csv') and f.startswith('ALL_TRANSACTIONS')]
    
    if not files:
        print(f"❌ No transaction files found in {transactions_dir}")
        return None
    
    # Get the latest file
    latest_file = sorted(files)[-1]
    filepath = os.path.join(transactions_dir, latest_file)
    print(f"📄 Loading: {latest_file}")
    return filepath

def main():
    """Main execution function"""
    print("🏦 Crypto Money Flow Analyzer Starting...")
    print("=" * 50)
    
    # Load wallet configuration
    wallets = load_wallet_config()
    if not wallets:
        print("❌ No wallets found in configuration")
        return
    
    print(f"💰 Tracking {len(wallets)} wallets:")
    for addr, label in wallets.items():
        print(f"   • {label}: {addr}")
    print()
    
    # Load transaction data
    transaction_file = load_latest_transaction_file()
    if not transaction_file:
        return
    
    try:
        df = pd.read_csv(transaction_file)
        print(f"📊 Loaded {len(df)} transactions")
    except Exception as e:
        print(f"❌ Error loading transaction file: {e}")
        return
    
    # Analyze flows
    flow_df = detect_transaction_flows(df, wallets)
    
    # Create wallet summary
    summary_df = create_wallet_summary(flow_df, wallets)
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = './portfolio_data/transactions/processed/'
    
    flow_file = os.path.join(output_dir, f'transaction_flows_{timestamp}.csv')
    summary_file = os.path.join(output_dir, f'wallet_money_summary_{timestamp}.csv')
    
    flow_df.to_csv(flow_file, index=False)
    summary_df.to_csv(summary_file, index=False)
    
    print(f"\n💾 Results saved:")
    print(f"   📄 Transaction flows: {flow_file}")
    print(f"   📄 Wallet summary: {summary_file}")
    
    # Display summary statistics
    print("\n" + "=" * 50)
    print("📊 MONEY FLOW ANALYSIS RESULTS")
    print("=" * 50)
    
    total_deposited = summary_df['total_money_deposited'].sum()
    total_withdrawn = summary_df['total_money_withdrawn'].sum()
    net_investment = summary_df['net_investment'].sum()
    total_swaps = summary_df['swaps_detected'].sum()
    
    print(f"💵 Total Money Deposited: ${total_deposited:,.2f}")
    print(f"💸 Total Money Withdrawn: ${total_withdrawn:,.2f}")
    print(f"💰 Net Investment: ${net_investment:,.2f}")
    print(f"🔄 Total Swaps Detected: {total_swaps}")
    print()
    
    print("🏦 Per Wallet Breakdown:")
    for _, row in summary_df.iterrows():
        print(f"   {row['wallet_label']:<15}: ${row['net_investment']:>10,.2f} net invested")
        print(f"   {'':15}   (${row['total_money_deposited']:,.2f} in, ${row['total_money_withdrawn']:,.2f} out)")
    
    # Flow type breakdown
    print(f"\n🔍 Transaction Flow Types:")
    flow_counts = flow_df['flow_type'].value_counts()
    for flow_type, count in flow_counts.items():
        print(f"   {flow_type:<15}: {count:>4} transactions")
    
    print(f"\n📊 Detection Summary:")
    print(f"   Money IN transactions: {len(flow_df[flow_df['flow_type'] == 'MONEY_IN'])}")
    print(f"   Money OUT transactions: {len(flow_df[flow_df['flow_type'] == 'MONEY_OUT'])}")
    print(f"   Swap pairs detected: {len(flow_df[flow_df['flow_type'].isin(['SWAP_IN', 'SWAP_OUT'])]) // 2}")
    print(f"   Cross-wallet transfers: {len(flow_df[flow_df['flow_type'] == 'CROSS_WALLET'])}")
    print(f"   Neutral/zero transactions: {len(flow_df[flow_df['flow_type'] == 'NEUTRAL'])}")
    print(f"   Unknown transactions: {len(flow_df[flow_df['flow_type'] == 'UNKNOWN'])}")
    
    print("\n✅ Analysis complete! Use these files to calculate true P&L.")

if __name__ == "__main__":
    main()
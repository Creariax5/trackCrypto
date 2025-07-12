#!/usr/bin/env python3
"""
Portfolio Ownership Analyzer - Shows who contributed how much and their percentage
"""
import pandas as pd
import os
from collections import defaultdict

def analyze_ownership():
    print("💰 PORTFOLIO OWNERSHIP ANALYZER")
    print("=" * 50)
    
    # Handle special owners like "2/3:ilan 1/3:yannick"
    def parse_owner(owner_str):
        """Parse owner string and return list of (name, fraction) tuples"""
        if pd.isna(owner_str):
            return []
        
        owner_str = str(owner_str).strip()
        
        # Check if it contains fractions (like "2/3:ilan 1/3:yannick")
        if ':' in owner_str and '/' in owner_str:
            owners = []
            
            # Split by spaces to get individual "fraction:name" pairs
            parts = owner_str.split()
            
            for part in parts:
                if ':' in part and '/' in part:
                    try:
                        # Split "fraction:name" format
                        fraction_str, name = part.split(':', 1)
                        numerator, denominator = fraction_str.split('/')
                        fraction = float(numerator) / float(denominator)
                        owners.append((name, fraction))
                    except Exception as e:
                        print(f"⚠️  Could not parse owner part '{part}': {e}")
                        # Fallback: treat as single owner
                        clean_name = part.replace(':', '').replace('/', '_')
                        owners.append((clean_name, 1.0))
                elif part:  # Non-empty part without proper format
                    # Treat as single owner
                    owners.append((part, 1.0))
            
            return owners
        else:
            # Single owner
            return [(owner_str, 1.0)]
    
    # Load the external transactions file
    file_path = './portfolio_data/transactions/processed/external_transactions_manual.csv'
    
    if not os.path.exists(file_path):
        print("❌ external_transactions_manual.csv not found!")
        print(f"Expected location: {file_path}")
        return
    
    # Read the data
    df = pd.read_csv(file_path)
    print(f"📊 Loaded {len(df)} external transactions")
    
    # Check if owner column exists
    if 'owner' not in df.columns:
        print("❌ 'owner' column not found in the CSV!")
        print(f"Available columns: {list(df.columns)}")
        return
    
    # Clean the data
    df = df.dropna(subset=['owner', 'amount_usd'])
    print(f"📊 Transactions with owner data: {len(df)}")
    
    # Debug: Show unique owner formats
    unique_owners = df['owner'].unique()
    print(f"\n🔍 UNIQUE OWNER FORMATS FOUND:")
    for owner in unique_owners[:10]:  # Show first 10
        parsed = parse_owner(owner)
        print(f"  '{owner}' → {parsed}")
    if len(unique_owners) > 10:
        print(f"  ... and {len(unique_owners) - 10} more")
    # Expand transactions with fractional ownership
    expanded_transactions = []
    
    for _, row in df.iterrows():
        owners = parse_owner(row['owner'])
        
        if not owners:
            continue
        
        for owner_name, fraction in owners:
            expanded_row = row.copy()
            expanded_row['owner'] = owner_name
            expanded_row['amount_usd'] = row['amount_usd'] * fraction
            expanded_transactions.append(expanded_row)
    
    # Create expanded DataFrame
    df_expanded = pd.DataFrame(expanded_transactions)
    print(f"📊 Expanded to {len(df_expanded)} ownership records")
    
    # Calculate by owner
    owner_stats = defaultdict(lambda: {'in': 0, 'out': 0, 'net': 0, 'transactions': []})
    
    for _, row in df_expanded.iterrows():
        owner = row['owner']
        amount = row['amount_usd']
        direction = row['direction']
        
        owner_stats[owner]['transactions'].append({
            'direction': direction,
            'amount': amount,
            'exchange': row.get('exchange_or_friend', ''),
            'token': row.get('token_symbol', ''),
            'date': row.get('date', '')
        })
        
        if direction == 'IN':
            owner_stats[owner]['in'] += amount
        elif direction == 'OUT':
            owner_stats[owner]['out'] += amount
        
        owner_stats[owner]['net'] = owner_stats[owner]['in'] - owner_stats[owner]['out']
    
    # Calculate totals
    total_in = sum(stats['in'] for stats in owner_stats.values())
    total_out = sum(stats['out'] for stats in owner_stats.values())
    total_net = total_in - total_out
    
    print(f"\n💰 PORTFOLIO TOTALS:")
    print(f"Total IN:  ${total_in:>10,.2f}")
    print(f"Total OUT: ${total_out:>10,.2f}")
    print(f"Total NET: ${total_net:>10,.2f}")
    
    # Sort owners by net contribution
    sorted_owners = sorted(owner_stats.items(), key=lambda x: x[1]['net'], reverse=True)
    
    print(f"\n👥 OWNERSHIP BREAKDOWN:")
    print("=" * 70)
    print(f"{'Owner':<12} {'IN':<12} {'OUT':<12} {'NET':<12} {'% of Total':<10}")
    print("-" * 70)
    
    for owner, stats in sorted_owners:
        net_amount = stats['net']
        percentage = (net_amount / total_net * 100) if total_net != 0 else 0
        
        print(f"{owner:<12} ${stats['in']:>10,.2f} ${stats['out']:>10,.2f} ${net_amount:>10,.2f} {percentage:>8.1f}%")
    
    # Show detailed breakdown for each owner
    print(f"\n🔍 DETAILED BREAKDOWN BY OWNER:")
    print("=" * 70)
    
    for owner, stats in sorted_owners:
        if stats['net'] != 0:  # Only show owners with non-zero contributions
            print(f"\n{owner.upper()}:")
            print(f"   Net Contribution: ${stats['net']:,.2f} ({(stats['net']/total_net*100):+.1f}% of total)")
            print(f"   Total IN:  ${stats['in']:,.2f}")
            print(f"   Total OUT: ${stats['out']:,.2f}")
            print(f"   Transactions: {len(stats['transactions'])}")
            
            # Show breakdown by exchange
            exchange_breakdown = defaultdict(lambda: {'in': 0, 'out': 0, 'count': 0})
            for tx in stats['transactions']:
                exchange = tx['exchange'] if tx['exchange'] else 'unknown'
                exchange_breakdown[exchange]['count'] += 1
                if tx['direction'] == 'IN':
                    exchange_breakdown[exchange]['in'] += tx['amount']
                else:
                    exchange_breakdown[exchange]['out'] += tx['amount']
            
            print(f"   By Exchange:")
            for exchange, ex_stats in exchange_breakdown.items():
                ex_net = ex_stats['in'] - ex_stats['out']
                print(f"     {exchange}: ${ex_net:>8,.2f} ({ex_stats['count']} txs)")
    
    # Investment summary
    print(f"\n📈 INVESTMENT SUMMARY:")
    print("=" * 50)
    
    # Current portfolio value (this would need to be calculated separately)
    print(f"Total Invested (NET): ${total_net:,.2f}")
    print(f"Number of Investors: {len([s for s in owner_stats.values() if s['net'] > 0])}")
    
    # Top contributors
    top_contributors = [(owner, stats['net']) for owner, stats in sorted_owners if stats['net'] > 0][:5]
    print(f"\nTop 5 Contributors:")
    for i, (owner, amount) in enumerate(top_contributors, 1):
        percentage = (amount / total_net * 100) if total_net != 0 else 0
        print(f"  {i}. {owner}: ${amount:,.2f} ({percentage:.1f}%)")
    
    # Save summary to file
    output_folder = './portfolio_data/transactions/processed/'
    summary_file = os.path.join(output_folder, 'ownership_summary.csv')
    
    summary_data = []
    for owner, stats in owner_stats.items():
        percentage = (stats['net'] / total_net * 100) if total_net != 0 else 0
        summary_data.append({
            'owner': owner,
            'amount_in': stats['in'],
            'amount_out': stats['out'],
            'net_contribution': stats['net'],
            'percentage_of_total': round(percentage, 2),
            'transaction_count': len(stats['transactions'])
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values('net_contribution', ascending=False)
    summary_df.to_csv(summary_file, index=False)
    
    print(f"\n💾 Ownership summary saved to: {summary_file}")

def main():
    analyze_ownership()

if __name__ == "__main__":
    main()
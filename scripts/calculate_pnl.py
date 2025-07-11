import pandas as pd
import numpy as np
import os
import re

def parse_currency(value):
    """Parse currency string to float"""
    if pd.isna(value) or value == "None":
        return 0.0
    # Remove currency symbols and commas
    cleaned = re.sub(r'[$,]', '', str(value))
    try:
        return float(cleaned)
    except:
        return 0.0

def parse_timestamp(timestamp_str):
    """Parse timestamp from filename"""
    try:
        return pd.to_datetime(str(timestamp_str).replace('.csv', ''), format='%d-%m-%Y_%H-%M-%S')
    except:
        return pd.NaT

def calculate_pnl(df):
    """Calculate PnL since last update for each position"""
    print("📊 Calculating PnL...")
    
    # Clean and prepare data
    df['timestamp'] = df['source_file_timestamp'].apply(parse_timestamp)
    df = df.dropna(subset=['timestamp'])
    
    # Convert usd_value to numeric (handle currency formatting)
    df['usd_value_numeric'] = df['usd_value'].apply(parse_currency)
    df = df[df['usd_value_numeric'] > 0]
    
    # Create position identifier
    df['position_id'] = (df['wallet_label'] + '|' + df['address'] + '|' + 
                        df['blockchain'] + '|' + df['coin'] + '|' + df['protocol'])
    
    # Sort by position and time
    df = df.sort_values(['position_id', 'timestamp'])
    
    # Initialize PnL columns
    df['pnl_since_last_update'] = 0.0
    df['pnl_percentage'] = 0.0
    df['previous_value'] = np.nan
    df['is_new_position'] = True
    df['days_since_last_update'] = 0
    df['update_sequence'] = 0
    
    # Calculate PnL for each position
    for position_id in df['position_id'].unique():
        mask = df['position_id'] == position_id
        position_data = df[mask].copy()
        
        if len(position_data) > 1:
            # Mark as not new (except first) and add sequence numbers
            df.loc[position_data.index[1:], 'is_new_position'] = False
            df.loc[position_data.index, 'update_sequence'] = range(len(position_data))
            
            # Calculate PnL
            for i in range(1, len(position_data)):
                current_idx = position_data.index[i]
                prev_idx = position_data.index[i-1]
                
                current_val = position_data.loc[current_idx, 'usd_value_numeric']
                prev_val = position_data.loc[prev_idx, 'usd_value_numeric']
                
                # Calculate days between updates
                current_time = position_data.loc[current_idx, 'timestamp']
                prev_time = position_data.loc[prev_idx, 'timestamp']
                days_diff = (current_time - prev_time).days
                
                pnl = current_val - prev_val
                pnl_pct = (pnl / prev_val * 100) if prev_val > 0 else 0
                
                df.loc[current_idx, 'pnl_since_last_update'] = pnl
                df.loc[current_idx, 'pnl_percentage'] = pnl_pct
                df.loc[current_idx, 'previous_value'] = prev_val
                df.loc[current_idx, 'days_since_last_update'] = days_diff
    
    return df

def display_summary(df):
    """Display PnL summary"""
    print("\n📈 PnL SUMMARY")
    print("=" * 40)
    
    total_positions = len(df)
    pnl_positions = len(df[df['pnl_since_last_update'] != 0])
    profitable = len(df[df['pnl_since_last_update'] > 0])
    
    print(f"Total positions: {total_positions:,}")
    print(f"With PnL data: {pnl_positions:,}")
    print(f"Profitable: {profitable:,}")
    
    if pnl_positions > 0:
        total_pnl = df['pnl_since_last_update'].sum()
        win_rate = (profitable / pnl_positions) * 100
        
        print(f"Total PnL: ${total_pnl:+,.2f}")
        print(f"Win rate: {win_rate:.1f}%")
        
        # Top gains/losses
        print(f"\n🏆 Top 5 Gains:")
        top_gains = df[df['pnl_since_last_update'] > 0].nlargest(5, 'pnl_since_last_update')
        for _, row in top_gains.iterrows():
            print(f"  {row['wallet_label']} | {row['coin']} | ${row['pnl_since_last_update']:+,.2f} ({row['pnl_percentage']:+.1f}%)")
        
        print(f"\n📉 Top 5 Losses:")
        top_losses = df[df['pnl_since_last_update'] < 0].nsmallest(5, 'pnl_since_last_update')
        for _, row in top_losses.iterrows():
            print(f"  {row['wallet_label']} | {row['coin']} | ${row['pnl_since_last_update']:+,.2f} ({row['pnl_percentage']:+.1f}%)")
            
        # Wallet summary
        print(f"\n🏦 PnL by Wallet:")
        wallet_pnl = df[df['pnl_since_last_update'] != 0].groupby('wallet_label')['pnl_since_last_update'].sum().sort_values(ascending=False)
        for wallet, pnl in wallet_pnl.items():
            print(f"  {wallet}: ${pnl:+,.2f}")

def main():
    """Main PnL calculation function"""
    print("💹 PnL Calculator starting...")
    
    input_file = "./portfolio_data/ALL_PORTFOLIOS_HISTORY.csv"
    output_file = "./portfolio_data/ALL_PORTFOLIOS_HISTORY_WITH_PNL.csv"
    
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        return False
    
    # Load and process data
    print("🔍 Loading data...")
    df = pd.read_csv(input_file)
    print(f"✅ Loaded {len(df):,} records")
    
    # Add timestamp column from source_file_timestamp
    df['timestamp'] = df['source_file_timestamp'].apply(parse_timestamp)
    
    # Calculate PnL
    df_with_pnl = calculate_pnl(df)
    
    # Add formatted columns to match original format
    df_with_pnl['pnl_formatted'] = df_with_pnl['pnl_since_last_update'].apply(lambda x: f"${x:+,.2f}")
    df_with_pnl['pnl_percentage_formatted'] = df_with_pnl['pnl_percentage'].apply(lambda x: f"{x:+.2f}%")
    df_with_pnl['previous_value_formatted'] = df_with_pnl['previous_value'].apply(lambda x: f"${x:,.2f}" if not pd.isna(x) else "N/A")
    
    # Display summary
    display_summary(df_with_pnl)
    
    # Save enhanced data with proper column order
    print(f"\n💾 Saving to {output_file}...")
    
    # Define column order to match original format
    column_order = [
        'wallet_label', 'address', 'blockchain', 'coin', 'protocol', 'price', 'amount', 'usd_value',
        'usd_value_numeric', 'pnl_since_last_update', 'pnl_percentage', 'previous_value', 
        'days_since_last_update', 'is_new_position', 'update_sequence',
        'pnl_formatted', 'pnl_percentage_formatted', 'previous_value_formatted',
        'token_name', 'is_verified', 'logo_url', 'source_file_timestamp', 'timestamp', 'position_id'
    ]
    
    # Only include columns that exist
    final_columns = [col for col in column_order if col in df_with_pnl.columns]
    df_with_pnl = df_with_pnl[final_columns]
    df_with_pnl.to_csv(output_file, index=False)
    print("✅ PnL calculation complete!")
    
    return True

if __name__ == "__main__":
    main()
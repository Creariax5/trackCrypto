import pandas as pd
import numpy as np
from datetime import datetime
import sys
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
    """Parse timestamp from filename format"""
    try:
        # Remove .csv extension if present
        timestamp_str = str(timestamp_str).replace('.csv', '')
        # Parse DD-MM-YYYY_HH-MM-SS format
        return pd.to_datetime(timestamp_str, format='%d-%m-%Y_%H-%M-%S')
    except:
        try:
            # Try alternative format
            return pd.to_datetime(timestamp_str)
        except:
            return pd.NaT

def calculate_pnl_since_last_update(df):
    """Calculate PnL since last update for each position"""
    
    print("  📊 Processing portfolio data...")
    
    # Parse numeric columns if not already done
    if 'usd_value_numeric' not in df.columns:
        df['usd_value_numeric'] = df['usd_value'].apply(parse_currency)
    
    # Parse timestamps if not already done
    if df['source_file_timestamp'].dtype == 'object':
        df['timestamp'] = df['source_file_timestamp'].apply(parse_timestamp)
    else:
        df['timestamp'] = pd.to_datetime(df['source_file_timestamp'])
    
    # Remove rows with invalid timestamps or zero values
    df = df.dropna(subset=['timestamp'])
    df = df[df['usd_value_numeric'] > 0]
    
    # Sort by identifier columns and timestamp
    identifier_cols = ['wallet_label', 'address', 'blockchain', 'coin', 'protocol']
    df = df.sort_values(identifier_cols + ['timestamp'])
    
    print("  🔍 Creating position identifiers...")
    
    # Create a unique position identifier
    df['position_id'] = df[identifier_cols].apply(lambda x: '|'.join(x.astype(str)), axis=1)
    
    # Initialize PnL columns
    df['pnl_since_last_update'] = 0.0
    df['pnl_percentage'] = 0.0
    df['previous_value'] = np.nan
    df['days_since_last_update'] = 0
    df['is_new_position'] = True
    df['update_sequence'] = 0
    
    print("  💹 Calculating PnL for each position...")
    
    # Process each unique position
    unique_positions = df['position_id'].unique()
    processed_count = 0
    
    for position_id in unique_positions:
        processed_count += 1
        if processed_count % 1000 == 0:
            print(f"    Processed {processed_count:,}/{len(unique_positions):,} positions...")
        
        position_mask = df['position_id'] == position_id
        position_data = df[position_mask].copy().sort_values('timestamp')
        
        # Add sequence numbers
        df.loc[position_mask, 'update_sequence'] = range(len(position_data))
        
        if len(position_data) > 1:
            # Mark all but first as not new
            df.loc[position_data.index[1:], 'is_new_position'] = False
            
            # Calculate PnL for each update after the first
            for i in range(1, len(position_data)):
                current_idx = position_data.index[i]
                previous_idx = position_data.index[i-1]
                
                current_value = position_data.loc[current_idx, 'usd_value_numeric']
                previous_value = position_data.loc[previous_idx, 'usd_value_numeric']
                
                pnl = current_value - previous_value
                pnl_pct = (pnl / previous_value * 100) if previous_value > 0 else 0
                
                # Calculate days since last update
                current_time = position_data.loc[current_idx, 'timestamp']
                previous_time = position_data.loc[previous_idx, 'timestamp']
                days_diff = (current_time - previous_time).days
                
                df.loc[current_idx, 'pnl_since_last_update'] = pnl
                df.loc[current_idx, 'pnl_percentage'] = pnl_pct
                df.loc[current_idx, 'previous_value'] = previous_value
                df.loc[current_idx, 'days_since_last_update'] = days_diff
    
    print(f"  ✅ Processed {len(unique_positions):,} unique positions")
    return df

def format_currency(value):
    """Format currency value for display"""
    if pd.isna(value) or value == 0:
        return "$0.00"
    return f"${value:+,.2f}"

def format_percentage(value):
    """Format percentage value for display"""
    if pd.isna(value) or value == 0:
        return "0.00%"
    return f"{value:+.2f}%"

def calculate_daily_pnl_summary(df):
    """Calculate daily PnL summary by timestamp"""
    daily_summary = df[df['pnl_since_last_update'] != 0].groupby('source_file_timestamp').agg({
        'pnl_since_last_update': ['sum', 'count', 'mean'],
        'timestamp': 'first'
    }).round(2)
    
    daily_summary.columns = ['total_pnl', 'position_count', 'avg_pnl', 'date']
    daily_summary = daily_summary.reset_index()
    daily_summary = daily_summary.sort_values('date')
    
    return daily_summary

def display_summary_statistics(df):
    """Display comprehensive summary statistics"""
    print("\n📈 COMPREHENSIVE PnL ANALYSIS")
    print("=" * 60)
    
    # Basic statistics
    total_positions = len(df)
    new_positions = len(df[df['is_new_position'] == True])
    positions_with_pnl = len(df[df['pnl_since_last_update'] != 0])
    profitable_positions = len(df[df['pnl_since_last_update'] > 0])
    losing_positions = len(df[df['pnl_since_last_update'] < 0])
    
    print(f"📊 Position Statistics:")
    print(f"  Total positions: {total_positions:,}")
    print(f"  New positions: {new_positions:,}")
    print(f"  Positions with PnL data: {positions_with_pnl:,}")
    print(f"  Profitable positions: {profitable_positions:,}")
    print(f"  Losing positions: {losing_positions:,}")
    
    if positions_with_pnl > 0:
        win_rate = (profitable_positions / positions_with_pnl) * 100
        print(f"  Win rate: {win_rate:.1f}%")
        
        # PnL statistics
        total_pnl = df['pnl_since_last_update'].sum()
        avg_pnl = df[df['pnl_since_last_update'] != 0]['pnl_since_last_update'].mean()
        max_gain = df['pnl_since_last_update'].max()
        max_loss = df['pnl_since_last_update'].min()
        
        print(f"\n💰 PnL Statistics:")
        print(f"  Total PnL: {format_currency(total_pnl)}")
        print(f"  Average PnL per position: {format_currency(avg_pnl)}")
        print(f"  Biggest gain: {format_currency(max_gain)}")
        print(f"  Biggest loss: {format_currency(max_loss)}")
        
        # Time-based statistics
        avg_days = df[df['days_since_last_update'] > 0]['days_since_last_update'].mean()
        print(f"  Average days between updates: {avg_days:.1f}")
    
    # Daily summary
    daily_summary = calculate_daily_pnl_summary(df)
    if len(daily_summary) > 0:
        print(f"\n📅 Daily PnL Summary (Last 10 Days):")
        for _, row in daily_summary.tail(10).iterrows():
            date_str = row['date'].strftime('%Y-%m-%d %H:%M')
            print(f"  {date_str}: {format_currency(row['total_pnl'])} ({row['position_count']} positions)")

def display_top_performers(df, top_n=10):
    """Display top performing positions"""
    print(f"\n🏆 Top {top_n} Biggest Gains:")
    top_gains = df[df['pnl_since_last_update'] > 0].nlargest(top_n, 'pnl_since_last_update')
    if len(top_gains) > 0:
        for _, row in top_gains.iterrows():
            days_info = f"({row['days_since_last_update']}d)" if row['days_since_last_update'] > 0 else ""
            print(f"  {row['wallet_label']} | {row['coin']} | {row['protocol']} | {format_currency(row['pnl_since_last_update'])} ({format_percentage(row['pnl_percentage'])}) {days_info}")
    else:
        print("  No profitable positions found")
    
    print(f"\n📉 Top {top_n} Biggest Losses:")
    top_losses = df[df['pnl_since_last_update'] < 0].nsmallest(top_n, 'pnl_since_last_update')
    if len(top_losses) > 0:
        for _, row in top_losses.iterrows():
            days_info = f"({row['days_since_last_update']}d)" if row['days_since_last_update'] > 0 else ""
            print(f"  {row['wallet_label']} | {row['coin']} | {row['protocol']} | {format_currency(row['pnl_since_last_update'])} ({format_percentage(row['pnl_percentage'])}) {days_info}")
    else:
        print("  No losing positions found")

def display_wallet_summary(df):
    """Display PnL summary by wallet"""
    print(f"\n🏦 PnL Summary by Wallet:")
    wallet_summary = df[df['pnl_since_last_update'] != 0].groupby('wallet_label').agg({
        'pnl_since_last_update': ['sum', 'count', 'mean']
    }).round(2)
    
    wallet_summary.columns = ['total_pnl', 'position_count', 'avg_pnl']
    wallet_summary = wallet_summary.sort_values('total_pnl', ascending=False)
    
    for wallet, row in wallet_summary.iterrows():
        print(f"  {wallet}: {format_currency(row['total_pnl'])} ({row['position_count']} positions, avg: {format_currency(row['avg_pnl'])})")

def main():
    print("🚀 PORTFOLIO PnL CALCULATOR")
    print("=" * 60)
    
    # File paths
    input_file = "portfolio_data/ALL_PORTFOLIOS_HISTORY.csv"
    output_file = "portfolio_data/ALL_PORTFOLIOS_HISTORY_WITH_PNL.csv"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file '{input_file}' not found.")
        print("Please make sure the file exists and run the master portfolio tracker first.")
        sys.exit(1)
    
    print("🔍 Loading portfolio history data...")
    
    try:
        # Load the data
        df = pd.read_csv(input_file)
        print(f"✅ Loaded {len(df):,} records from {input_file}")
        
        # Display basic info
        date_range = f"{df['source_file_timestamp'].min()} to {df['source_file_timestamp'].max()}"
        print(f"📊 Data range: {date_range}")
        print(f"🏦 Unique wallets: {df['wallet_label'].nunique()}")
        print(f"🪙 Unique tokens: {df['coin'].nunique()}")
        print(f"📅 Unique timestamps: {df['source_file_timestamp'].nunique()}")
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        sys.exit(1)
    
    print("\n💹 Calculating PnL since last update...")
    
    try:
        # Calculate PnL
        df_with_pnl = calculate_pnl_since_last_update(df)
        
        # Format currency columns for better readability
        df_with_pnl['pnl_formatted'] = df_with_pnl['pnl_since_last_update'].apply(format_currency)
        df_with_pnl['pnl_percentage_formatted'] = df_with_pnl['pnl_percentage'].apply(format_percentage)
        df_with_pnl['previous_value_formatted'] = df_with_pnl['previous_value'].apply(lambda x: f"${x:,.2f}" if not pd.isna(x) else "N/A")
        
        print(f"✅ PnL calculations completed!")
        
    except Exception as e:
        print(f"❌ Error calculating PnL: {e}")
        sys.exit(1)
    
    # Display comprehensive analysis
    display_summary_statistics(df_with_pnl)
    display_top_performers(df_with_pnl)
    display_wallet_summary(df_with_pnl)
    
    print(f"\n💾 Saving enhanced data to {output_file}...")
    
    try:
        # Reorder columns for better readability
        base_cols = ['wallet_label', 'address', 'blockchain', 'coin', 'protocol', 
                    'price', 'amount', 'usd_value', 'usd_value_numeric']
        pnl_cols = ['pnl_since_last_update', 'pnl_percentage', 'previous_value', 
                   'days_since_last_update', 'is_new_position', 'update_sequence']
        formatted_cols = ['pnl_formatted', 'pnl_percentage_formatted', 'previous_value_formatted']
        remaining_cols = [col for col in df_with_pnl.columns if col not in base_cols + pnl_cols + formatted_cols]
        
        column_order = base_cols + pnl_cols + formatted_cols + remaining_cols
        column_order = [col for col in column_order if col in df_with_pnl.columns]
        
        df_with_pnl = df_with_pnl[column_order]
        
        # Save the enhanced data
        df_with_pnl.to_csv(output_file, index=False)
        print(f"✅ Enhanced portfolio data saved successfully!")
        print(f"📁 File location: {output_file}")
        print(f"📊 Total rows: {len(df_with_pnl):,}")
        
        # Show new columns added
        new_columns = [
            'pnl_since_last_update',
            'pnl_percentage', 
            'previous_value',
            'days_since_last_update',
            'is_new_position',
            'update_sequence',
            'pnl_formatted',
            'pnl_percentage_formatted',
            'previous_value_formatted',
            'position_id',
            'timestamp'
        ]
        print(f"🆕 New columns added: {', '.join(new_columns)}")
        
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        sys.exit(1)
    
    print(f"\n🎉 SCRIPT COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("📈 You can now analyze PnL trends and position performance over time.")
    print("💡 Tips:")
    print("  - Use 'is_new_position' to filter first-time positions")
    print("  - Use 'update_sequence' to track position evolution")
    print("  - Use 'days_since_last_update' to analyze update frequency")
    print("  - Load the enhanced CSV into your Streamlit dashboard for visualization")

if __name__ == "__main__":
    main()
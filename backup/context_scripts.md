# 🚀 Crypto Portfolio Tracker - Complete Project Context

## 📋 Project Overview
You have built a comprehensive cryptocurrency portfolio tracking system that:
- Fetches data from multiple wallets via API
- Tracks historical portfolio changes over time
- Calculates Position-level PnL (Profit & Loss)
- Displays data in a Streamlit dashboard with advanced analytics

## 📁 Project Structure
```
trackCrypto/
├── main.py                                    # Main launcher
├── scripts/
│   ├── get_wallet.py                         # Single wallet data fetcher
│   ├── get_multi_wallet.py                   # Multi-wallet data fetcher  
│   ├── combine_history.py                    # Historical data combiner
│   └── calculate_pnl.py                      # PnL calculator
├── streamlit/
│   └── main.py                               # Streamlit dashboard
└── portfolio_data/
    ├── YYYY-MM-DD/                           # Daily organized folders
    │   └── combined/
    │       └── ALL_WALLETS_COMBINED_*.csv    # Daily snapshots
    ├── ALL_PORTFOLIOS_HISTORY.csv            # Master historical file
    └── ALL_PORTFOLIOS_HISTORY_WITH_PNL.csv   # Enhanced with PnL data
```

## 🔧 Scripts Functionality

### 1. `get_wallet.py` (60 lines)
- Fetches portfolio data from API for single wallet
- Processes wallet balances + DeFi positions
- Saves to timestamped CSV

### 2. `get_multi_wallet.py` (60 lines)  
- Uses `get_wallet.py` for multiple wallets
- Tracks 5 wallets with labels:
  ```python
  WALLETS = {
      "0x3656ff4c11c4c8b4b77402faab8b3387e36f2e77": "Old_Wallet",
      "0x5a2ccb5b0a4dc5b7ca9c0768e6e2082be7bc6229": "Main_Wallet", 
      "0x29ea4918b83223f1eec45f242d2d96a293b2fcf3": "Coinbase_Wallet",
      "0x7ab7528984690d3d8066bac18f38133a0cfba053": "Sonic_Farm",
      "0x2463cc0b87dfc7d563b5f4fee294c49fe0603c62": "ZYF_AI"
  }
  ```
- Creates combined CSV with all wallets

### 3. `combine_history.py` (80 lines)
- Runs multi-wallet tracker first
- Finds all historical CSV files  
- Combines into master history file
- Adds `source_file_timestamp` for tracking

### 4. `calculate_pnl.py` (120 lines)
- Calculates PnL between position updates over time
- Creates position identifiers to track same assets
- Adds columns: `pnl_since_last_update`, `pnl_percentage`, `is_new_position`, etc.
- Shows summary statistics and top performers

### 5. `main.py` (40 lines)
- Orchestrates everything: `combine_history()` → `calculate_pnl()` → launches Streamlit

## 📊 Data Structure

### Base CSV Format (from API):
```csv
wallet_label,address,blockchain,coin,protocol,price,amount,usd_value,token_name,is_verified,logo_url
```

### Enhanced CSV Format (with PnL):
```csv
wallet_label,address,blockchain,coin,protocol,price,amount,usd_value,usd_value_numeric,
pnl_since_last_update,pnl_percentage,previous_value,days_since_last_update,
is_new_position,update_sequence,pnl_formatted,pnl_percentage_formatted,
previous_value_formatted,token_name,is_verified,logo_url,source_file_timestamp,
timestamp,position_id
```

## 🎯 Current Status

### ✅ What's Working:
- **Data Collection**: 5 wallets, ~44 positions per run
- **Historical Data**: 36 snapshots spanning June 26 - July 11, 2025
- **Master File**: 1,537 total records in `ALL_PORTFOLIOS_HISTORY.csv`
- **PnL Calculations**: Enhanced file with position-level PnL tracking
- **Streamlit Dashboard**: Loading and displaying PnL data correctly

### 📈 Your Current Data:
- **36 historical snapshots** over ~15 days
- **1,537 total records** in master file  
- **1,139 records** with PnL calculations
- **Multiple wallets** tracked across different blockchains
- **DeFi positions** from various protocols

## 🔄 Workflow
```bash
# Complete workflow:
python main.py
```

This runs:
1. `combine_history()` - Gets latest data + combines all historical files
2. `calculate_pnl()` - Adds PnL calculations  
3. Launches Streamlit dashboard at `streamlit/main.py`

## 🌐 API Details
- **Endpoint**: `https://automation-api-virid.vercel.app/api/webhook?address={address}`
- **Returns**: Portfolio data with wallet balances + DeFi positions
- **Timeout**: 30 seconds per request
- **Rate limiting**: 1 second delay between wallet requests

## 🔧 Recent Issues Resolved

### Path Issues:
- Scripts use `./portfolio_data/` (current directory)
- Streamlit runs from `streamlit/` so uses `../portfolio_data/`

### Column Name Consistency:
- Streamlit expects: `pnl_since_last_update`
- Fixed calculate_pnl.py to use correct column names
- Added formatted columns: `pnl_formatted`, `pnl_percentage_formatted`

## 💡 Key Features

### PnL Calculation Logic:
- Creates `position_id` from: `wallet_label|address|blockchain|coin|protocol`
- Tracks same positions across time
- Calculates difference from previous snapshot
- Marks first occurrence as `is_new_position = True`

### Dashboard Analytics:
- **Cumulative PnL charts**
- **Waterfall charts** showing daily changes
- **Heatmaps** by protocol and date
- **Top/worst performers** tables
- **Win rate and profit factor** metrics

## 🚀 How to Resume Work

1. **Run full pipeline**: `python main.py`
2. **View dashboard**: Should auto-launch or run `streamlit run streamlit/main.py`
3. **Check data**: Files in `./portfolio_data/`
4. **Debug paths**: Use `python check_streamlit_paths.py`

## 📋 Dependencies
```python
import pandas as pd
import requests  
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
```

## 🎯 Next Potential Improvements
- Add more wallets to `WALLETS` dict
- Implement alerts for significant PnL changes  
- Add portfolio allocation analysis
- Export reports to PDF
- Add real-time price alerts
- Implement backtesting features

Your system is fully functional and tracking substantial historical data with comprehensive PnL analytics! 🎉
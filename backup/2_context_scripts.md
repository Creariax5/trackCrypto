# 🚀 Crypto Portfolio Tracker - Complete Project Context

## 📋 Project Overview
Comprehensive cryptocurrency portfolio tracking system that:
- Fetches wallet data from multiple addresses via API
- Tracks historical portfolio changes over time
- Calculates Position-level PnL (Profit & Loss)
- **NEW**: Extracts transaction history from HTML files
- **NEW**: Adds historical USD prices at transaction time
- Displays data in Streamlit dashboard with advanced analytics

## 📁 Project Structure
```
trackCrypto/
├── main.py                                    # Main launcher
├── config/
│   └── wallets.json                          # Wallet configuration
├── scripts/
│   ├── get_wallet.py                         # Single wallet data fetcher
│   ├── get_multi_wallet.py                   # Multi-wallet data fetcher  
│   ├── combine_history.py                    # Historical data combiner
│   ├── calculate_pnl.py                      # PnL calculator
│   ├── extract_transactions.py               # NEW: HTML transaction extractor
│   └── get_historical_prices.py              # NEW: Historical price fetcher
├── streamlit/
│   └── main.py                               # Streamlit dashboard
└── portfolio_data/
    ├── YYYY-MM-DD/                           # Daily organized folders
    │   └── combined/
    │       └── ALL_WALLETS_COMBINED_*.csv    # Daily snapshots
    ├── ALL_PORTFOLIOS_HISTORY.csv            # Master historical file
    ├── ALL_PORTFOLIOS_HISTORY_WITH_PNL.csv   # Enhanced with PnL data
    └── transactions/                          # NEW: Transaction data
        ├── download/                          # HTML files from blockchain explorer
        │   └── 0x5A2Ccb5B0a4Dc5B7Ca9c0768e6E2082Be7bc6229.html
        ├── processed/                         # Extracted CSV files
        │   ├── ALL_TRANSACTIONS_*.csv
        │   └── ALL_TRANSACTIONS_*_with_historical.csv
        └── price_cache.json                   # CoinGecko API cache
```

## 🔧 Scripts Functionality

### **Portfolio Tracking (Original System)**

#### 1. `get_wallet.py` (60 lines)
- Fetches portfolio data from API for single wallet
- Processes wallet balances + DeFi positions
- Saves to timestamped CSV

#### 2. `get_multi_wallet.py` (60 lines)  
- Uses `get_wallet.py` for multiple wallets
- **NOW LOADS FROM CONFIG**: Uses `./config/wallets.json`
- **Current wallets tracked**:
  ```json
  {
    "wallets": {
      "0x3656ff4c11c4c8b4b77402faab8b3387e36f2e77": "Old_Wallet",
      "0x5a2ccb5b0a4dc5b7ca9c0768e6e2082be7bc6229": "Main_Wallet", 
      "0x29ea4918b83223f1eec45f242d2d96a293b2fcf3": "Coinbase_Wallet",
      "0x7ab7528984690d3d8066bac18f38133a0cfba053": "Sonic_Farm",
      "0x2463cc0b87dfc7d563b5f4fee294c49fe0603c62": "ZYF_AI"
    }
  }
  ```

#### 3. `combine_history.py` (80 lines)
- Runs multi-wallet tracker first
- Finds all historical CSV files  
- Combines into master history file
- Adds `source_file_timestamp` for tracking

#### 4. `calculate_pnl.py` (120 lines)
- Calculates PnL between position updates over time
- Creates position identifiers to track same assets
- Adds columns: `pnl_since_last_update`, `pnl_percentage`, `is_new_position`, etc.
- Shows summary statistics and top performers

### **Transaction Tracking (NEW System)**

#### 5. `extract_transactions.py` (NEW)
- **Purpose**: Extract transaction data from blockchain explorer HTML files
- **Input**: HTML files in `./portfolio_data/transactions/download/`
- **Process**:
  - Extracts from both JSON data and HTML table
  - Gets timestamps, token symbols, amounts, addresses
  - **Key Fix**: Extracts full token symbols from amount text (not truncated attributes)
  - Merges data intelligently by transaction hash
- **Output**: `ALL_TRANSACTIONS_*.csv` with all transaction details

#### 6. `get_historical_prices.py` (NEW)
- **Purpose**: Add historical USD prices at transaction time
- **Process**:
  - Reads transaction CSV from `extract_transactions.py`
  - Uses CoinGecko API to get historical prices
  - **Token Discovery**: Searches by symbol with exact matching
  - **Smart Caching**: Avoids repeat API calls (price_cache.json)
  - **Rate Limiting**: 45 calls/minute to stay under limits
- **Output**: `ALL_TRANSACTIONS_*_with_historical.csv` with price data

#### 7. `main.py` (40 lines)
- Orchestrates everything: `combine_history()` → `calculate_pnl()` → launches Streamlit

## 📊 Data Structure

### **Portfolio CSV Format**:
```csv
wallet_label,address,blockchain,coin,protocol,price,amount,usd_value,usd_value_numeric,
pnl_since_last_update,pnl_percentage,previous_value,days_since_last_update,
is_new_position,update_sequence,pnl_formatted,pnl_percentage_formatted,
previous_value_formatted,token_name,is_verified,logo_url,source_file_timestamp,
timestamp,position_id
```

### **Transaction CSV Format**:
```csv
wallet_address,transaction_hash,chain,action,timestamp_utc,time_ago,token_symbol,token_name,
amount_full,amount_display,amount_direction,usd_value_full,usd_value_display,
from_address,from_address_short,from_info,to_address,to_address_short,to_info,
historical_price_usd,historical_value_usd,price_source,coingecko_id
```

## 🌐 API Details

### **Portfolio API**:
- **Endpoint**: `https://automation-api-virid.vercel.app/api/webhook?address={address}`
- **Returns**: Portfolio data with wallet balances + DeFi positions
- **Timeout**: 30 seconds per request
- **Rate limiting**: 1 second delay between wallet requests

### **CoinGecko API**:
- **Search**: `https://api.coingecko.com/api/v3/search?query={symbol}`
- **Historical**: `https://api.coingecko.com/api/v3/coins/{id}/history?date={DD-MM-YYYY}`
- **Rate limit**: 50 calls/minute (using 45 to be safe)
- **Free tier**: 10,000 calls/month

## 🎯 Current Status

### ✅ **What's Working**:
- **Portfolio Tracking**: 5 wallets, ~44 positions per run
- **Historical Data**: 36 snapshots spanning June 26 - July 11, 2025
- **Master File**: 1,537 total records in `ALL_PORTFOLIOS_HISTORY.csv`
- **PnL Calculations**: Enhanced file with position-level PnL tracking
- **Streamlit Dashboard**: Loading and displaying PnL data correctly
- **Transaction Extraction**: HTML → CSV with all transaction details
- **Historical Pricing**: CoinGecko integration with smart caching

### 📈 **Your Current Data**:
- **36 historical snapshots** over ~15 days
- **1,537 total records** in master portfolio file  
- **1,139 records** with PnL calculations
- **Transaction data** from blockchain explorer HTML files
- **Historical prices** for accurate USD values at transaction time

## 🔄 Current Workflow

### **Portfolio Tracking**:
```bash
python main.py
```
Runs: `combine_history()` → `calculate_pnl()` → Streamlit dashboard

### **Transaction Processing**:
```bash
# 1. Extract transactions from HTML
python scripts/extract_transactions.py

# 2. Add historical prices
python scripts/get_historical_prices.py
```

## 🔧 Recent Developments

### **Transaction System Issues Solved**:
1. **Token Symbol Truncation**: Fixed extraction to get full symbols (CBBTC not CBBT)
2. **Dynamic Token Discovery**: Uses CoinGecko search instead of hardcoded mapping
3. **Historical Pricing**: Added accurate USD values at transaction time
4. **Smart Caching**: Prevents duplicate API calls
5. **Rate Limiting**: Proper API management

### **Key Fixes Applied**:
- ✅ Extract token symbols from amount text: `"+0.00458987 CBBTC"` → `"CBBTC"`
- ✅ Regex pattern: `r'([A-Z]{2,10})\s*$'` for any 2-10 letter tokens
- ✅ Exact symbol matching in CoinGecko search
- ✅ Clean code structure without duplicates

## 🚀 **Next Steps / Potential Improvements**:
- Add more wallets to `config/wallets.json`
- Implement alerts for significant PnL changes  
- Add portfolio allocation analysis
- Export reports to PDF
- Add real-time price alerts
- Implement backtesting features
- Integrate transaction data with portfolio dashboard

## 💡 **Key Design Principles Used**:
- **Simple code that works** > Complex over-engineering
- **Smart caching** to minimize API calls
- **Exact matching** for reliable data
- **Comprehensive data extraction** without losing information
- **Clean separation** between portfolio and transaction systems

## 📦 **Dependencies**:
```python
import pandas as pd
import requests  
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from bs4 import BeautifulSoup
import csv, json, os, time, re
from datetime import datetime
```

Your system is fully functional with both portfolio tracking AND transaction analysis with historical pricing! 🎉
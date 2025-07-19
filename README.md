# Crypto Portfolio Tracker - Clean & Organized

## 🚀 Quick Start

```bash
# Run everything (data collection + analysis + dashboard)
python run.py

# Or just launch the dashboard
python run.py
# Choose option 2
```

## 🗂️ Project Structure

```
crypto-portfolio-tracker/
├── run.py                     # 🚀 Main launcher
├── config/                    # ⚙️ Configuration files
│   ├── wallets.json          # Wallet addresses
│   ├── friends_addresses.json # Known addresses
│   └── streamlit/            # Dashboard configs
├── collectors/               # 📊 Data collection
│   ├── get_wallet.py         # Single wallet fetcher
│   ├── get_multi_wallet.py   # Multi-wallet coordinator
│   ├── extract_transactions.py # Transaction parser
│   └── get_historical_prices.py # Price enhancement
├── processors/               # 🔄 Data processing
│   ├── combine_history.py    # Historical aggregation
│   ├── calculate_pnl.py      # PnL calculation
│   ├── external_tracker.py   # External flow analysis
│   └── ownership_analyzer.py # Multi-owner analysis
├── dashboard/               # 🌐 Web interface
│   ├── main.py              # Navigation
│   ├── current_portfolio.py # Current analysis
│   ├── historical_analysis.py # Historical tracking
│   ├── performance_analysis.py # Performance comparison
│   ├── earnings_analysis.py # PnL analytics
│   └── utils.py             # Shared utilities
├── core/                    # 🔧 Core utilities (future)
└── portfolio_data/          # 💾 Data storage
    ├── YYYY-MM-DD/          # Daily snapshots
    ├── ALL_PORTFOLIOS_HISTORY.csv # Master dataset
    ├── ALL_PORTFOLIOS_HISTORY_WITH_PNL.csv # Enhanced dataset
    └── transactions/        # Transaction data
```

## 📊 Features

### Data Collection
- **Multi-wallet tracking** across multiple blockchains
- **Real-time portfolio data** from DeFi protocols
- **Transaction analysis** from blockchain exports
- **Historical price integration** from CoinGecko

### Advanced Analytics
- **Position-level PnL tracking** with lifecycle analysis
- **Performance metrics** (APY, volatility, drawdown)
- **External flow analysis** (exchanges, friends)
- **Multi-owner support** with fractional ownership

### Interactive Dashboard
- **Current portfolio** analysis with date selection
- **Historical performance** tracking and trends
- **Comparative analysis** across assets and protocols
- **Earnings analytics** with advanced PnL visualizations

## ⚙️ Configuration

Edit `config/wallets.json` to add your wallets:
```json
{
  "wallets": {
    "0x1234...": "My Main Wallet",
    "0x5678...": "DeFi Strategy Wallet"
  }
}
```

## 🎯 Usage Examples

```bash
# Full pipeline (recommended)
python run.py

# Individual components
python collectors/get_multi_wallet.py    # Collect data
python processors/combine_history.py     # Process history  
python processors/calculate_pnl.py       # Calculate PnL
streamlit run dashboard/main.py          # Launch dashboard
```

## 📈 Dashboard Pages

1. **📊 Current Portfolio** - Real-time portfolio analysis
2. **📈 Historical Analysis** - Performance over time
3. **🎯 Performance Analysis** - Asset/protocol comparison
4. **💰 Earnings Analysis** - Advanced PnL analytics

---

**🎉 Enjoy tracking your crypto portfolio!**

# Crypto Portfolio Dashboard

A comprehensive Streamlit-based dashboard for analyzing cryptocurrency portfolio data with historical tracking and detailed insights.

## 🚀 Features

- **Daily Portfolio Analysis**: Select any date to view your portfolio snapshot
- **Interactive Visualizations**: Charts, graphs, and treemaps for data exploration
- **Multi-Wallet Support**: Compare and analyze multiple wallets simultaneously
- **Risk Assessment**: Concentration metrics and diversification analysis
- **Detailed Tables**: Filterable and exportable data tables
- **Export Functionality**: Download portfolio data in CSV format

## 📁 Project Structure

```
crypto-portfolio-dashboard/
├── streamlit/
│   ├── app.py                      # Main Streamlit application
│   ├── components/
│   │   ├── __init__.py
│   │   ├── charts.py              # Chart generation functions
│   │   ├── metrics.py             # Metrics calculation functions
│   │   └── tables.py              # Table display functions
│   ├── utils/
│   │   ├── __init__.py
│   │   └── data_processing.py     # Data loading and processing
│   └── data/
│       └── ALL_PORTFOLIOS_HISTORY.csv  # Your historical portfolio data
├── requirements.txt               # Python dependencies
└── README.md                     # This file
```

## 🛠️ Installation & Setup

1. **Clone or download the project files**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Prepare your data:**
   - Place your `ALL_PORTFOLIOS_HISTORY.csv` file in the `streamlit/data/` directory
   - Ensure the CSV contains the required columns (see Data Format section below)

4. **Run the dashboard:**
   ```bash
   cd streamlit
   streamlit run app.py
   ```

5. **Open your browser** and navigate to the URL shown in the terminal (usually `http://localhost:8501`)

## 📊 Data Format

Your `ALL_PORTFOLIOS_HISTORY.csv` file should contain the following columns:

- `source_file_timestamp`: Timestamp in DD-MM-YYYY_HH-MM-SS format
- `wallet_label`: Name/label of the wallet
- `address`: Wallet address
- `blockchain`: Blockchain name (e.g., ETHEREUM, POLYGON)
- `coin`: Token symbol (e.g., ETH, BTC, MATIC)
- `token_name`: Full token name
- `protocol`: Protocol or platform name
- `price`: Token price (can include $ and commas)
- `amount`: Token amount
- `usd_value`: USD value (can include $ and commas)
- `is_verified`: Boolean indicating if token is verified
- `logo_url`: URL to token logo

## 🎯 Key Features Explained

### Date Selection
- Choose any date from the sidebar dropdown
- Automatically shows the latest data if multiple timestamps exist for the same date
- Displays portfolio snapshot for the selected date

### Portfolio Analysis
- **Overview Metrics**: Total value, number of wallets, tokens, and blockchains
- **Wallet Distribution**: Pie chart showing value distribution across wallets  
- **Blockchain Analysis**: Bar chart of assets by blockchain
- **Top Holdings**: Horizontal bar chart of largest positions
- **Protocol Distribution**: Treemap of assets by protocol/platform

### Risk Assessment
- **Concentration Metrics**: Analysis of portfolio concentration
- **Diversification Insights**: Assessment of risk levels
- **Risk Warnings**: Automatic alerts for high concentration

### Detailed Tables
- **All Holdings**: Complete portfolio with advanced filtering
- **Wallet Summary**: Aggregated wallet statistics
- **Blockchain Summary**: Blockchain-level analysis
- **Token Summary**: Top tokens with detailed metrics

## 🎨 Customization

The dashboard uses a modular structure making it easy to customize:

- **Charts**: Modify `components/charts.py` to add new visualizations
- **Metrics**: Update `components/metrics.py` to add new calculations
- **Tables**: Enhance `components/tables.py` for additional table views
- **Data Processing**: Extend `utils/data_processing.py` for new data sources

## 🔧 Troubleshooting

**Data File Not Found:**
- Ensure `ALL_PORTFOLIOS_HISTORY.csv` is in the `streamlit/data/` directory
- Check file permissions and ensure it's readable

**No Data for Selected Date:**
- Verify your data file contains entries for the selected date
- Check timestamp format in the `source_file_timestamp` column

**Charts Not Displaying:**
- Ensure all required columns are present in your data
- Check for data type issues (numeric columns should be parseable)

## 🆘 Support

If you encounter issues:

1. Check the Streamlit console for error messages
2. Verify your data file format matches the expected structure
3. Ensure all dependencies are properly installed
4. Check file paths and permissions

## 📝 License

This project is open source. Feel free to modify and distribute as needed.
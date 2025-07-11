import csv
import json
import os
import time
import requests
import re
from datetime import datetime

def load_cache():
    """Load cached price data"""
    cache_file = "./portfolio_data/transactions/price_cache.json"
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """Save price cache"""
    cache_file = "./portfolio_data/transactions/price_cache.json"
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)

def parse_timestamp(timestamp_str):
    """Parse timestamp from HTML format to date"""
    if not timestamp_str:
        return None
    
    try:
        # "Jul 07, 2025 5:08PM" -> "07-07-2025"
        if ',' in timestamp_str:
            date_part = timestamp_str.split(',')[0] + ', ' + timestamp_str.split(',')[1].split()[0]
            # "Jul 07, 2025"
            dt = datetime.strptime(date_part, "%b %d, %Y")
            return dt.strftime("%d-%m-%Y")
    except:
        pass
    return None

def get_coingecko_id(token_symbol, cache):
    """Get CoinGecko ID from token symbol via search"""
    cache_key = f"token_id_{token_symbol.upper()}"
    
    # Check cache first
    if cache_key in cache:
        return cache[cache_key], False
    
    # Search by symbol
    url = f"https://api.coingecko.com/api/v3/search"
    params = {'query': token_symbol}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            coins = data.get('coins', [])
            
            # Look for exact symbol match
            for coin in coins:
                if coin.get('symbol', '').upper() == token_symbol.upper():
                    coingecko_id = coin.get('id')
                    print(f"✅ Found: {token_symbol} -> {coingecko_id}")
                    cache[cache_key] = coingecko_id
                    return coingecko_id, True
            
            # No exact match found
            print(f"❌ No exact match for {token_symbol}")
            cache[cache_key] = None
            return None, True
        else:
            print(f"❌ Search API error {response.status_code}")
            cache[cache_key] = None
            return None, True
            
    except Exception as e:
        print(f"❌ Search failed for {token_symbol}: {e}")
        cache[cache_key] = None
        return None, True

def get_historical_price(token_id, date, cache):
    """Get historical price from CoinGecko API with caching"""
    cache_key = f"{token_id}_{date}"
    
    # Check cache first
    if cache_key in cache:
        return cache[cache_key], False
    
    # API call to CoinGecko
    url = f"https://api.coingecko.com/api/v3/coins/{token_id}/history"
    params = {
        'date': date,  # DD-MM-YYYY format
        'localization': 'false'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            price = data.get('market_data', {}).get('current_price', {}).get('usd')
            
            if price:
                cache[cache_key] = price
                print(f"✅ {token_id} on {date}: ${price}")
                return price, True
            else:
                print(f"❌ No price data for {token_id} on {date}")
                cache[cache_key] = None
                return None, True
        
        elif response.status_code == 429:
            print("⚠️  Rate limited - waiting 60 seconds...")
            time.sleep(60)
            return get_historical_price(token_id, date, cache)
        
        else:
            print(f"❌ API error {response.status_code} for {token_id}")
            cache[cache_key] = None
            return None, True
            
    except Exception as e:
        print(f"❌ Error fetching {token_id}: {e}")
        cache[cache_key] = None
        return None, True

def extract_amount_value(amount_str):
    """Extract numeric value from amount string"""
    if not amount_str:
        return 0
    
    # "+431.36341 USDC" -> 431.36341
    # "-0.165739117224539 WETH" -> -0.165739117224539
    match = re.search(r'([+-]?\d+\.?\d*)', amount_str.replace(',', ''))
    if match:
        return float(match.group(1))
    return 0

def process_historical_prices(csv_file_path):
    """Add historical prices to transaction CSV"""
    print("🔄 Adding historical prices to transactions...")
    
    # Load cache
    cache = load_cache()
    
    # Read CSV
    transactions = []
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        transactions = list(reader)
    
    print(f"📊 Processing {len(transactions)} transactions...")
    
    # Track API calls
    api_calls = 0
    max_calls_per_minute = 45
    call_timestamps = []
    
    # Process each transaction
    for i, tx in enumerate(transactions):
        token_symbol = tx.get('token_symbol', '').strip()
        timestamp_utc = tx.get('timestamp_utc', '').strip()
        amount_full = tx.get('amount_full', '').strip()
        
        print(f"[{i+1}/{len(transactions)}] Processing {token_symbol}...")
        
        # Initialize new columns
        tx['historical_price_usd'] = ''
        tx['historical_value_usd'] = ''
        tx['price_source'] = ''
        tx['coingecko_id'] = ''
        
        if not token_symbol or not timestamp_utc:
            continue
        
        # Parse date
        date = parse_timestamp(timestamp_utc)
        if not date:
            continue
        
        # Rate limiting check
        now = time.time()
        call_timestamps = [t for t in call_timestamps if now - t < 60]
        
        if len(call_timestamps) >= max_calls_per_minute:
            sleep_time = 60 - (now - call_timestamps[0])
            if sleep_time > 0:
                print(f"⏱️  Rate limit reached, waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
        
        # Get CoinGecko ID
        token_id, token_api_called = get_coingecko_id(token_symbol, cache)
        if token_api_called:
            call_timestamps.append(time.time())
            api_calls += 1
        
        if not token_id:
            continue
        
        tx['coingecko_id'] = token_id
        
        # Rate limiting check for price lookup
        now = time.time()
        call_timestamps = [t for t in call_timestamps if now - t < 60]
        
        if len(call_timestamps) >= max_calls_per_minute:
            sleep_time = 60 - (now - call_timestamps[0])
            if sleep_time > 0:
                print(f"⏱️  Rate limit reached, waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
        
        # Get historical price
        price, price_api_called = get_historical_price(token_id, date, cache)
        if price_api_called:
            call_timestamps.append(time.time())
            api_calls += 1
        
        if price:
            # Calculate historical value
            amount = extract_amount_value(amount_full)
            historical_value = abs(amount) * price
            
            tx['historical_price_usd'] = f"${price:.6f}"
            tx['historical_value_usd'] = f"${historical_value:.2f}"
            tx['price_source'] = 'coingecko'
        
        # Save cache every 10 transactions
        if i % 10 == 0:
            save_cache(cache)
    
    # Save final cache
    save_cache(cache)
    
    # Write updated CSV
    output_file = csv_file_path.replace('.csv', '_with_historical.csv')
    
    fieldnames = list(transactions[0].keys()) if transactions else []
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transactions)
    
    print(f"🎉 Success! Made {api_calls} API calls")
    print(f"💾 Saved: {output_file}")
    
    return output_file

def main():
    """Find latest transaction CSV and add historical prices"""
    processed_dir = "./portfolio_data/transactions/processed"
    
    if not os.path.exists(processed_dir):
        print("❌ No processed transactions found. Run extract_transactions.py first.")
        return
    
    # Find latest CSV file
    csv_files = [f for f in os.listdir(processed_dir) if f.endswith('.csv') and not f.endswith('_with_historical.csv')]
    
    if not csv_files:
        print("❌ No transaction CSV files found")
        return
    
    latest_file = max(csv_files, key=lambda x: os.path.getctime(os.path.join(processed_dir, x)))
    csv_path = os.path.join(processed_dir, latest_file)
    
    print(f"📄 Processing: {latest_file}")
    
    return process_historical_prices(csv_path)

if __name__ == "__main__":
    main()
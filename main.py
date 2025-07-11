import subprocess
import sys
import os

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from combine_history import main as combine_history
from calculate_pnl import main as calculate_pnl

def main():
    """Main launcher function"""
    print("🚀 Portfolio Tracker Launcher")
    print("=" * 40)
    
    # Step 1: Combine historical data
    print("📊 Step 1: Combining historical data...")
    if not combine_history():
        print("❌ Failed to combine historical data")
        return
    
    # Step 2: Calculate PnL
    print("\n💹 Step 2: Calculating PnL...")
    if not calculate_pnl():
        print("❌ Failed to calculate PnL")
        return
    
    # Step 3: Launch Streamlit dashboard
    print("\n🌐 Step 3: Launching dashboard...")
    try:
        if sys.platform == "win32":
            subprocess.Popen(["streamlit", "run", "streamlit/main.py"], 
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(["streamlit", "run", "streamlit/main.py"])
        
        print("✅ Dashboard launched successfully!")
        print("🌍 Open your browser to view the dashboard")
        
    except Exception as e:
        print(f"❌ Failed to launch dashboard: {e}")
        print("💡 Try running manually: streamlit run streamlit/main.py")

if __name__ == "__main__":
    main()
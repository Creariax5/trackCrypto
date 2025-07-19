#!/usr/bin/env python3
"""
Crypto Portfolio Tracker - Main Launcher
Organized and cleaned project structure
"""

import subprocess
import sys
import os

# Ensure we can import from the project
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def run_data_pipeline():
    """Run the complete data processing pipeline"""
    print("🔄 CRYPTO PORTFOLIO DATA PIPELINE")
    print("=" * 40)
    
    # Step 1: Collect fresh portfolio data
    print("📊 Step 1: Collecting fresh portfolio data...")
    try:
        from collectors.get_multi_wallet import main as get_multi_wallet
        get_multi_wallet()
        print("✅ Portfolio data collected")
    except Exception as e:
        print(f"⚠️  Issue collecting data: {e}")
    
    # Step 2: Combine historical data
    print("\n📈 Step 2: Combining historical data...")
    try:
        from processors.combine_history import main as combine_history
        combine_history()
        print("✅ Historical data combined")
    except Exception as e:
        print(f"⚠️  Issue combining history: {e}")
    
    # Step 3: Calculate PnL
    print("\n💹 Step 3: Calculating PnL...")
    try:
        from processors.calculate_pnl import main as calculate_pnl
        calculate_pnl()
        print("✅ PnL calculations completed")
    except Exception as e:
        print(f"⚠️  Issue calculating PnL: {e}")

def launch_dashboard():
    """Launch the Streamlit dashboard"""
    print("\n🌐 LAUNCHING DASHBOARD")
    print("=" * 25)
    print("🚀 Starting Streamlit dashboard...")
    print("🌍 Your browser should open automatically!")
    
    try:
        # Add project root to environment
        env = os.environ.copy()
        env['PYTHONPATH'] = project_root + os.pathsep + env.get('PYTHONPATH', '')
        
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "dashboard/main.py"
        ], env=env)
        
    except KeyboardInterrupt:
        print("\n⏹️  Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")
        print("💡 Try manually: streamlit run dashboard/main.py")

def main():
    """Main function with user choice"""
    print("🚀 CRYPTO PORTFOLIO TRACKER")
    print("=" * 30)
    print("Choose an option:")
    print("1. 🔄 Run full data pipeline + launch dashboard")
    print("2. 🌐 Launch dashboard only") 
    print("3. 📊 Collect data only")
    print("4. 💹 Calculate PnL only")
    
    try:
        choice = input("\nEnter choice (1-4) or press Enter for option 1: ").strip()
        
        if choice == "2":
            launch_dashboard()
        elif choice == "3":
            print("📊 Collecting portfolio data...")
            from collectors.get_multi_wallet import main as get_multi_wallet
            get_multi_wallet()
        elif choice == "4":
            print("💹 Calculating PnL...")
            from processors.calculate_pnl import main as calculate_pnl
            calculate_pnl()
        else:  # Default: choice == "1" or Enter
            run_data_pipeline()
            launch_dashboard()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()

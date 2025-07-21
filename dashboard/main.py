import streamlit as st
from current_portfolio import current_portfolio_page
from historical_analysis import historical_analysis_page
from performance_analysis import performance_analysis_page
from earnings_analysis import earnings_analysis_page

# Page configuration
st.set_page_config(
    page_title="Crypto Portfolio Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main_navigation():
    """
    Updated main.py navigation that includes all standardized pages
    """
    st.set_page_config(
        page_title="Crypto Portfolio Dashboard",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Navigation
    st.sidebar.title("💰 Portfolio Dashboard")
    page = st.sidebar.radio(
        "Navigate to:",
        [
            "📊 Current Portfolio",
            "📈 Historical Analysis", 
            "🎯 Performance Analysis",
            "💰 Earnings Analysis",
            "⚙️ Configuration Editor"  # NEW
        ],
        key="main_navigation"
    )
    
    # Route to appropriate page
    if page == "📊 Current Portfolio":
        current_portfolio_page()
    elif page == "📈 Historical Analysis":
        historical_analysis_page()
    elif page == "🎯 Performance Analysis":
        performance_analysis_page()
    elif page == "💰 Earnings Analysis":
        earnings_analysis_page()
    elif page == "⚙️ Configuration Editor":
        # Would implement config editor here
        st.title("⚙️ Configuration Editor")
        st.info("Visual configuration editor coming next!")


if __name__ == "__main__":
    main_navigation()

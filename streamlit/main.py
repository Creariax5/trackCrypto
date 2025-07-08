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

def main():
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Choose a page:",
        ["📊 Current Portfolio", "📈 Historical Analysis", "🎯 Performance Analysis", "💰 Earnings Analysis"],
        key="page_selector"
    )

    if page == "📊 Current Portfolio":
        current_portfolio_page()
    elif page == "📈 Historical Analysis":
        historical_analysis_page()
    elif page == "🎯 Performance Analysis":
        performance_analysis_page()
    elif page == "💰 Earnings Analysis":
        earnings_analysis_page()

if __name__ == "__main__":
    main()
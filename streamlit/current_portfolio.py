import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import load_and_process_data


def create_overview_metrics(df):
    """Create overview metrics cards"""
    total_value = df['usd_value_numeric'].sum()
    total_wallets = df['wallet_label'].nunique()
    total_tokens = df['coin'].nunique()
    total_protocols = df['protocol'].nunique()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Portfolio Value",
            value=f"${total_value:,.2f}",
            delta=None
        )

    with col2:
        st.metric(
            label="Number of Wallets",
            value=f"{total_wallets}",
            delta=None
        )

    with col3:
        st.metric(
            label="Unique Tokens",
            value=f"{total_tokens}",
            delta=None
        )

    with col4:
        st.metric(
            label="Protocols/Platforms",
            value=f"{total_protocols}",
            delta=None
        )


def create_wallet_breakdown_chart(df):
    """Create wallet breakdown pie chart"""
    wallet_totals = df.groupby('wallet_label')['usd_value_numeric'].sum().reset_index()
    wallet_totals = wallet_totals.sort_values('usd_value_numeric', ascending=False)

    fig = px.pie(
        wallet_totals,
        values='usd_value_numeric',
        names='wallet_label',
        title="Portfolio Distribution by Wallet",
        hover_data=['usd_value_numeric'],
        labels={'usd_value_numeric': 'USD Value'}
    )

    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>'
    )

    return fig


def create_blockchain_breakdown_chart(df):
    """Create blockchain breakdown chart"""
    blockchain_totals = df.groupby('blockchain')['usd_value_numeric'].sum().reset_index()
    blockchain_totals = blockchain_totals.sort_values('usd_value_numeric', ascending=False)

    fig = px.bar(
        blockchain_totals,
        x='blockchain',
        y='usd_value_numeric',
        title="Asset Distribution by Blockchain",
        labels={'usd_value_numeric': 'USD Value', 'blockchain': 'Blockchain'},
        color='usd_value_numeric',
        color_continuous_scale='viridis'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False
    )

    return fig


def create_top_holdings_chart(df, top_n=10):
    """Create top holdings chart"""
    token_totals = df.groupby(['coin', 'token_name'])['usd_value_numeric'].sum().reset_index()
    token_totals = token_totals.sort_values('usd_value_numeric', ascending=False).head(top_n)

    # Create display name combining symbol and name
    token_totals['display_name'] = token_totals['coin'] + ' (' + token_totals['token_name'] + ')'

    fig = px.bar(
        token_totals,
        x='usd_value_numeric',
        y='display_name',
        orientation='h',
        title=f"Top {top_n} Token Holdings by Value",
        labels={'usd_value_numeric': 'USD Value', 'display_name': 'Token'},
        color='usd_value_numeric',
        color_continuous_scale='plasma'
    )

    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        showlegend=False
    )

    return fig


def create_protocol_breakdown_chart(df):
    """Create protocol breakdown chart"""
    protocol_totals = df.groupby('protocol')['usd_value_numeric'].sum().reset_index()
    protocol_totals = protocol_totals.sort_values('usd_value_numeric', ascending=False).head(15)

    fig = px.treemap(
        protocol_totals,
        path=['protocol'],
        values='usd_value_numeric',
        title="Asset Distribution by Protocol/Platform",
        color='usd_value_numeric',
        color_continuous_scale='blues'
    )

    return fig


def create_wallet_comparison_chart(df):
    """Create wallet comparison chart showing top tokens per wallet"""
    # Get top 5 tokens per wallet by value
    wallet_tokens = []
    for wallet in df['wallet_label'].unique():
        wallet_data = df[df['wallet_label'] == wallet]
        top_tokens = wallet_data.groupby('coin')['usd_value_numeric'].sum().reset_index()
        top_tokens = top_tokens.sort_values('usd_value_numeric', ascending=False).head(5)
        top_tokens['wallet_label'] = wallet
        wallet_tokens.append(top_tokens)

    combined_data = pd.concat(wallet_tokens, ignore_index=True)

    fig = px.bar(
        combined_data,
        x='wallet_label',
        y='usd_value_numeric',
        color='coin',
        title="Top Token Holdings by Wallet",
        labels={'usd_value_numeric': 'USD Value', 'wallet_label': 'Wallet'},
        barmode='stack'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def create_detailed_table(df):
    """Create detailed holdings table with search and filter"""
    st.subheader("📋 Detailed Holdings")

    # Create filters
    col1, col2, col3 = st.columns(3)

    with col1:
        wallet_filter = st.selectbox(
            "Filter by Wallet",
            options=['All'] + list(df['wallet_label'].unique()),
            key="wallet_filter"
        )

    with col2:
        blockchain_filter = st.selectbox(
            "Filter by Blockchain",
            options=['All'] + list(df['blockchain'].unique()),
            key="blockchain_filter"
        )

    with col3:
        min_value = st.number_input(
            "Minimum USD Value",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="min_value_filter"
        )

    # Apply filters
    filtered_df = df.copy()

    if wallet_filter != 'All':
        filtered_df = filtered_df[filtered_df['wallet_label'] == wallet_filter]

    if blockchain_filter != 'All':
        filtered_df = filtered_df[filtered_df['blockchain'] == blockchain_filter]

    filtered_df = filtered_df[filtered_df['usd_value_numeric'] >= min_value]

    # Sort by USD value descending
    filtered_df = filtered_df.sort_values('usd_value_numeric', ascending=False)

    # Display table with selected columns
    display_columns = [
        'wallet_label', 'blockchain', 'coin', 'token_name',
        'protocol', 'amount', 'price', 'usd_value'
    ]

    st.dataframe(
        filtered_df[display_columns],
        use_container_width=True,
        hide_index=True
    )

    # Show summary of filtered data
    st.info(f"Showing {len(filtered_df)} positions with total value: ${filtered_df['usd_value_numeric'].sum():,.2f}")


def current_portfolio_page():
    """Current portfolio analysis page"""
    st.title("💰 Crypto Portfolio Dashboard")
    st.markdown("---")

    # Sidebar for file upload
    st.sidebar.header("📂 Data Upload")
    uploaded_file = st.sidebar.file_uploader(
        "Upload your portfolio CSV file",
        type=['csv'],
        help="Upload the ALL_WALLETS_COMBINED CSV file",
        key="current_portfolio_upload"
    )

    if uploaded_file is not None:
        # Load and process data
        df = load_and_process_data(uploaded_file)

        if df is not None:
            st.success(f"✅ Successfully loaded {len(df)} portfolio positions")

            # Overview metrics
            st.header("📊 Portfolio Overview")
            create_overview_metrics(df)
            st.markdown("---")

            # Charts section
            st.header("📈 Portfolio Analysis")

            # Row 1: Wallet and Blockchain breakdown
            col1, col2 = st.columns(2)

            with col1:
                wallet_fig = create_wallet_breakdown_chart(df)
                st.plotly_chart(wallet_fig, use_container_width=True)

            with col2:
                blockchain_fig = create_blockchain_breakdown_chart(df)
                st.plotly_chart(blockchain_fig, use_container_width=True)

            # Row 2: Top holdings and Protocol breakdown
            col1, col2 = st.columns(2)

            with col1:
                holdings_fig = create_top_holdings_chart(df)
                st.plotly_chart(holdings_fig, use_container_width=True)

            with col2:
                protocol_fig = create_protocol_breakdown_chart(df)
                st.plotly_chart(protocol_fig, use_container_width=True)

            # Row 3: Wallet comparison
            st.subheader("🔍 Wallet Comparison")
            wallet_comparison_fig = create_wallet_comparison_chart(df)
            st.plotly_chart(wallet_comparison_fig, use_container_width=True)

            st.markdown("---")

            # Detailed table
            create_detailed_table(df)

            # Additional insights in sidebar
            st.sidebar.markdown("---")
            st.sidebar.header("📈 Quick Insights")

            # Top wallet by value
            top_wallet = df.groupby('wallet_label')['usd_value_numeric'].sum().idxmax()
            top_wallet_value = df.groupby('wallet_label')['usd_value_numeric'].sum().max()
            st.sidebar.metric(
                "Top Wallet",
                top_wallet,
                f"${top_wallet_value:,.2f}"
            )

            # Most valuable token
            top_token = df.groupby('coin')['usd_value_numeric'].sum().idxmax()
            top_token_value = df.groupby('coin')['usd_value_numeric'].sum().max()
            st.sidebar.metric(
                "Top Token",
                top_token,
                f"${top_token_value:,.2f}"
            )

            # Most used blockchain
            top_blockchain = df.groupby('blockchain')['usd_value_numeric'].sum().idxmax()
            top_blockchain_value = df.groupby('blockchain')['usd_value_numeric'].sum().max()
            st.sidebar.metric(
                "Top Blockchain",
                top_blockchain,
                f"${top_blockchain_value:,.2f}"
            )

    else:
        st.info("👆 Please upload your portfolio CSV file using the sidebar to get started!")

        # Show example of expected file format
        st.subheader("📋 Expected File Format")
        st.write("Your CSV file should contain the following columns:")

        example_data = {
            'wallet_label': ['Main_Wallet', 'DeFi_Wallet'],
            'address': ['0x1234...', '0x5678...'],
            'blockchain': ['ETHEREUM', 'POLYGON'],
            'coin': ['ETH', 'MATIC'],
            'protocol': ['Wallet', 'Uniswap V3'],
            'price': ['$2,500.00', '$0.85'],
            'amount': ['1.5000', '1000.0000'],
            'usd_value': ['$3,750.00', '$850.00'],
            'token_name': ['Ethereum', 'Polygon'],
            'is_verified': ['True', 'True'],
            'logo_url': ['https://...', 'https://...']
        }

        example_df = pd.DataFrame(example_data)
        st.dataframe(example_df, use_container_width=True)
"""
Chart generation components for the crypto portfolio dashboard.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def create_wallet_pie_chart(wallet_data: pd.DataFrame) -> go.Figure:
    """Create wallet distribution pie chart."""
    if len(wallet_data) == 0:
        return go.Figure()

    fig = px.pie(
        wallet_data,
        values='usd_value_numeric',
        names='wallet_label',
        title="Portfolio Distribution by Wallet",
        color_discrete_sequence=px.colors.qualitative.Set3
    )

    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>'
    )

    fig.update_layout(
        font=dict(size=12),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.01)
    )

    return fig


def create_blockchain_bar_chart(blockchain_data: pd.DataFrame) -> go.Figure:
    """Create blockchain distribution bar chart."""
    if len(blockchain_data) == 0:
        return go.Figure()

    fig = px.bar(
        blockchain_data,
        x='blockchain',
        y='usd_value_numeric',
        title="Asset Distribution by Blockchain",
        labels={'usd_value_numeric': 'USD Value', 'blockchain': 'Blockchain'},
        color='usd_value_numeric',
        color_continuous_scale='viridis'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False,
        font=dict(size=12)
    )

    return fig


def create_top_holdings_chart(holdings_data: pd.DataFrame) -> go.Figure:
    """Create top holdings horizontal bar chart."""
    if len(holdings_data) == 0:
        return go.Figure()

    # Create display name
    holdings_data['display_name'] = holdings_data['coin'] + ' (' + holdings_data['token_name'] + ')'

    fig = px.bar(
        holdings_data,
        x='usd_value_numeric',
        y='display_name',
        orientation='h',
        title="Top Holdings by Value",
        labels={'usd_value_numeric': 'USD Value', 'display_name': 'Token'},
        color='usd_value_numeric',
        color_continuous_scale='plasma'
    )

    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        showlegend=False,
        font=dict(size=12)
    )

    return fig


def create_protocol_treemap(protocol_data: pd.DataFrame) -> go.Figure:
    """Create protocol distribution treemap."""
    if len(protocol_data) == 0:
        return go.Figure()

    fig = px.treemap(
        protocol_data.head(15),  # Limit to top 15 for readability
        path=['protocol'],
        values='usd_value_numeric',
        title="Asset Distribution by Protocol/Platform",
        color='usd_value_numeric',
        color_continuous_scale='blues'
    )

    fig.update_layout(font=dict(size=12))

    return fig


def create_wallet_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """Create wallet comparison chart showing top tokens per wallet."""
    if len(df) == 0:
        return go.Figure()

    # Get top 5 tokens per wallet by value
    wallet_tokens = []
    for wallet in df['wallet_label'].unique():
        wallet_data = df[df['wallet_label'] == wallet]
        top_tokens = wallet_data.groupby('coin')['usd_value_numeric'].sum().reset_index()
        top_tokens = top_tokens.sort_values('usd_value_numeric', ascending=False).head(5)
        top_tokens['wallet_label'] = wallet
        wallet_tokens.append(top_tokens)

    if not wallet_tokens:
        return go.Figure()

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
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(size=12)
    )

    return fig


def create_value_distribution_donut(df: pd.DataFrame, category: str, title: str) -> go.Figure:
    """Create a donut chart for value distribution by category."""
    if len(df) == 0:
        return go.Figure()

    category_data = df.groupby(category)['usd_value_numeric'].sum().reset_index()
    category_data = category_data.sort_values('usd_value_numeric', ascending=False)

    fig = go.Figure(data=[go.Pie(
        labels=category_data[category],
        values=category_data['usd_value_numeric'],
        hole=0.4,
        hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<br>Percentage: %{percent}<extra></extra>'
    )])

    fig.update_layout(
        title=title,
        font=dict(size=12),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.01)
    )

    return fig


def create_allocation_sunburst(df: pd.DataFrame) -> go.Figure:
    """Create sunburst chart showing hierarchical allocation."""
    if len(df) == 0:
        return go.Figure()

    # Create hierarchical data
    hierarchy_data = df.groupby(['blockchain', 'protocol', 'coin']).agg({
        'usd_value_numeric': 'sum'
    }).reset_index()

    # Create path for sunburst
    hierarchy_data['path'] = (
            hierarchy_data['blockchain'] + ' / ' +
            hierarchy_data['protocol'] + ' / ' +
            hierarchy_data['coin']
    )

    fig = go.Figure(go.Sunburst(
        labels=hierarchy_data['coin'],
        parents=[''] * len(hierarchy_data),  # Simplified for now
        values=hierarchy_data['usd_value_numeric'],
        branchvalues="total",
        hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<extra></extra>',
        maxdepth=3
    ))

    fig.update_layout(
        title="Portfolio Allocation Hierarchy",
        font=dict(size=12)
    )

    return fig
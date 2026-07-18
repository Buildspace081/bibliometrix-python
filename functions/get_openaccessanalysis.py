from www.services import *


def get_open_access_analysis(df):
    """
    Generate a pie chart and table of the Open Access status distribution.

    Args:
        df: A DataFrame object containing the data.

    Returns:
        A Plotly figure object representing the Open Access distribution and
        a DataFrame with the document count per OA status.
    """
    data = df.get()

    # OA vuoto ("") indica che lo stato Open Access non e' noto/disponibile per
    # quel documento (comune sia nella pipeline OpenAlex sia nelle altre fonti
    # storiche quando il dato non e' popolato). Scelta: invece di scartare questi
    # record dal conteggio (il che nasconderebbe quanto e' effettivamente
    # completo il dataset), li raggruppiamo in una categoria esplicita
    # "Unknown" - coerente con lo spirito delle tabelle di completezza gia'
    # presenti altrove nell'app (vedi functions/get_table.py).
    oa_status = data["OA"].fillna("").replace("", "Unknown")
    oa_counts = oa_status.value_counts().reset_index()
    oa_counts.columns = ["OA Status", "Freq"]
    oa_counts = oa_counts.sort_values(by="Freq", ascending=False).reset_index(drop=True)

    # Create the plot
    fig = px.pie(
        oa_counts, names="OA Status", values="Freq",
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.Blues_r,
    )

    # Customize the layout and tooltips (hover)
    fig.update_traces(
        textinfo="label+percent",
        textfont=dict(size=13),
        marker=dict(line=dict(color="white", width=2)),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Documents: %{value}<extra></extra>"
        )
    )

    fig.update_layout(
        plot_bgcolor='white',
        font=dict(color="#222222", size=14, family="Segoe UI, Arial"),
        margin=dict(l=50, r=30, t=60, b=50),
        height=600,
        legend=dict(orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5),
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Segoe UI, Arial",
            bordercolor="#1f77b4"
        )
    )

    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, oa_counts

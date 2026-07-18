from www.services import *


def get_local_cited_documents(df, num_of_local_cited_docs, field_separator, fast_search=False):
    """
    Generate a plot and table of the most local cited documents.
    
    Args:
        df: A DataFrame object containing the data.
        num_of_local_cited_docs: The number of top cited documents to display.
        fast_search: Boolean indicating whether to use fast search or not.
        
    Returns:
        A Plotly figure object and a DataFrame of the most local cited documents.

        None (non una tupla) se la sorgente del DataFrame non e' supportata
        per l'analisi citazionale diretta (vedi nota sotto), invece di
        sollevare TypeError — stesso singolo valore sentinella che app.py
        verifica con `if result is None` al punto di chiamata
        (local_cited_documents_results.set(result) senza spacchettare prima).
    """
    df = metaTagExtraction(df, "SR")
    M = df.get()

    # Determine the local citation threshold
    if fast_search:
        loccit = M['TC'].quantile(0.75)
    else:
        loccit = 1

    # Fill missing values
    M['TC'] = M['TC'].fillna(0)

    # Create a histogram network
    H = histNetwork(df, min_citations=loccit, sep=";", network=False)

    # LIMITE NOTO (debugging step, spiegazione completa in
    # get_historiograph.py): histNetwork ritorna None per qualunque DB diverso
    # da "Web_of_Science"/"Scopus" (incluso il nostro "OPENALEX"), PRIMA di
    # toccare CR — non e' un problema di formato dei riferimenti. Non estendiamo
    # histNetwork qui (richiederebbe M['SR_FULL'], che scartiamo deliberatamente,
    # e produrrebbe comunque reti quasi sempre vuote su campioni tipici).
    if H is None:
        return None

    LCS = H['histData']
    M = H['M']
    
    # Create DataFrame for documents and local citations
    df_documents = pd.DataFrame({
        'Document': M['SR'],
        'DOI': M['DI'],
        'Year': M['PY'],
        'Local Citations': M['LCS'],
        'Global Citations': M['TC']
    })
    
    # Calculate additional metrics
    df_documents['LC/GC Ratio'] = (df_documents['Local Citations'] / df_documents['Global Citations'] * 100).round(2)
    
    # Calculate Normalized Local Citations within each publication year
    df_documents['Normalized Local Citations'] = df_documents.groupby('Year')['Local Citations'].transform(lambda x: x / x.mean()).round(2)

    # Calculate Normalized Global Citations within each publication year
    df_documents['Normalized Global Citations'] = df_documents.groupby('Year')['Global Citations'].transform(lambda x: x / x.mean()).round(2)
    
    # Sort by local citations
    df_documents = df_documents.sort_values(by='Local Citations', ascending=False)
    
    # Limit the number of documents to display
    if num_of_local_cited_docs > len(df_documents):
        num_of_local_cited_docs = len(df_documents)
    
    table_located_documents = df_documents.copy()
    df_documents = df_documents.head(num_of_local_cited_docs)
    
    # Create the plot (horizontal scatter with lines, similar to author plot)
    fig = go.Figure()

    # Add a thick line from each document label to its marker
    for idx, (i, row) in enumerate(df_documents.iterrows()):
        fig.add_shape(
            type="line",
            x0=0,
            x1=row["Local Citations"],
            y0=idx,
            y1=idx,
            line=dict(color="#e0e0e0", width=5),
            layer="below",
        )

    fig.add_trace(
        go.Scatter(
            x=df_documents["Local Citations"],
            y=list(range(len(df_documents))),
            mode="markers+text",
            marker=dict(
                size=18 + 6 * (df_documents["Local Citations"] / df_documents["Local Citations"].max()),
                color=df_documents["Local Citations"],
                colorscale=[[0, "#B3D1F2"], [1, "#5567BB"]],
                line=dict(width=1, color="#E0E0E0"),
                opacity=0.95,
                showscale=False,
            ),
            text=df_documents["Local Citations"],
            textposition="top center",
            textfont=dict(color="#5567BB", size=13),
            hovertemplate=(
                "<b>Document:</b> %{customdata[0]}<br>"
                "<b>Year:</b> %{customdata[1]}<br>"
                "<b>Local Citations:</b> %{x}<br>"
                "<b>Global Citations:</b> %{customdata[2]}<extra></extra>"
            ),
            customdata=df_documents[["Document", "Year", "Global Citations"]].values,
        )
    )

    # Add horizontal grid lines for each document (lighter)
    for idx in range(len(df_documents)):
        fig.add_shape(
            type="line",
            x0=0,
            x1=df_documents["Local Citations"].max(),
            y0=idx,
            y1=idx,
            line=dict(color="#E0E0E0", width=2),
            layer="below",
        )

    # Set x-axis ticks to 0, 5, 10, etc.
    max_x = df_documents["Local Citations"].max()
    tick_step = 5
    x_ticks = list(range(0, int(max_x) + tick_step, tick_step))
    if x_ticks[-1] < max_x:
        x_ticks.append(int(max_x))

    fig.update_yaxes(
        tickvals=list(range(len(df_documents))),
        ticktext=df_documents["Document"],
        autorange="reversed",
        showgrid=False,
        title="Document",
        tickfont=dict(size=13),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#F0F0F0",
        zeroline=False,
        tickvals=x_ticks,
        title="Local Citations",
        tickfont=dict(size=13),
    )
    fig.update_layout(
        plot_bgcolor='white',
        font=dict(color="#222222", size=14, family="Segoe UI, Arial"),
        margin=dict(l=250, r=40, t=40, b=40),
        height=50 + 90 * len(df_documents),
        showlegend=False,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Segoe UI, Arial",
            bordercolor="#5567BB"
        ),
        coloraxis_showscale=False,
    )
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}
    
    return fig, table_located_documents

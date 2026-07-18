from www.services import *


def get_local_cited_authors(df, num_of_cited_authors, fast_search=False):
    """
    Generate a plot and table of the most local cited authors.
    
    Args:
        df: A DataFrame object containing the data.
        num_of_cited_authors: The number of top cited authors to display.
        fast_search: Boolean indicating whether to use fast search or not.
        
    Returns:
        A Plotly figure object and a DataFrame of the most local cited authors.

        None (non una tupla) se la sorgente del DataFrame non e' supportata
        per l'analisi citazionale diretta (vedi nota sotto), invece di
        sollevare TypeError — stesso singolo valore sentinella che app.py
        verifica con `if result is None` al punto di chiamata
        (local_cited_authors_result.set(result) senza spacchettare prima).
    """
    # Determine the local citation threshold
    if fast_search:
        loccit = df['TC'].quantile(0.75)
    else:
        loccit = 1

    df = metaTagExtraction(df, "SR")
    M = df.get()

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
    # Propaghiamo (None, None) invece di un TypeError: stesso sentinel None gia'
    # gestito da ogni consumer in app.py (local_cited_authors_result =
    # reactive.value(None), con `if result is None` -> placeholder).
    if H is None:
        return None

    LCS = H['histData']
    M = H['M']
    
    # Split authors and repeat local citations
    AU = M['AU'].explode()
    n = AU.groupby(level=0).size()
    
    # Create DataFrame for authors and local citations
    df_authors = pd.DataFrame({'AU': AU, 'LCS': M['LCS'].repeat(n).values})
    author_counts = df_authors.groupby('AU')['LCS'].sum().reset_index()
    author_counts.columns = ["Authors", "N. of Local Citations"]
    author_counts = author_counts.sort_values(by="N. of Local Citations", ascending=False)
    
    # Limit the number of authors to display
    if num_of_cited_authors > len(author_counts):
        num_of_cited_authors = len(author_counts)
    
    # Truncate author names to 50 characters
    # author_counts["Authors"] = author_counts["Authors"].str[:50]

    # Prepare the complete table and filter rows for display
    table_located_authors = author_counts.copy()
    author_counts = author_counts.head(num_of_cited_authors).reset_index(drop=True)

    # Enhanced, beautiful, and readable plot for local cited authors
    frequency = "N. of Local Citations"
    # Create the plot (use scatter instead of scatter with orientation='h')
    fig = go.Figure()

    # Add a thick line from each label to its marker
    for i, row in author_counts.iterrows():
        fig.add_shape(
            type="line",
            x0=0,
            x1=row[frequency],
            y0=i,
            y1=i,
            line=dict(color="#e0e0e0", width=5),
            layer="below",
        )

    fig.add_trace(
        go.Scatter(
            x=author_counts[frequency],
            y=list(range(len(author_counts))),
            mode="markers+text",
            marker=dict(
                size=18 + 6 * (author_counts[frequency] / author_counts[frequency].max()),
                color=author_counts[frequency],
                colorscale=[[0, "#B3D1F2"], [1, "#5567BB"]],
                line=dict(width=1, color="#E0E0E0"),
                opacity=0.95,
                showscale=False,
            ),
            text=author_counts[frequency],
            textposition="top center",  
            textfont=dict(color="#5567BB", size=13),  
            hovertemplate=(
                "<b>Author:</b> %{customdata}<br>"
                "<b>" + frequency + ":</b> %{x}<extra></extra>"
            ),
            customdata=author_counts["Authors"],
        )
    )

    # Add horizontal grid lines for each author (lighter)
    for i in range(len(author_counts)):
        fig.add_shape(
            type="line",
            x0=0,
            x1=author_counts[frequency].max(),
            y0=i,
            y1=i,
            line=dict(color="#E0E0E0", width=2),
            layer="below",
        )

    # Set x-axis ticks to 0, 5, 10, etc.
    max_x = author_counts[frequency].max()
    tick_step = 5
    x_ticks = list(range(0, int(max_x) + tick_step, tick_step))
    if x_ticks[-1] < max_x:
        x_ticks.append(int(max_x))

    fig.update_yaxes(
        tickvals=list(range(len(author_counts))),
        ticktext=author_counts["Authors"],
        autorange="reversed",
        showgrid=False,
        title="Authors",
        tickfont=dict(size=13),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#F0F0F0",
        zeroline=False,
        tickvals=x_ticks,
        title=frequency,
        tickfont=dict(size=13),
    )
    fig.update_layout(
        plot_bgcolor='white',
        font=dict(color="#222222", size=14, family="Segoe UI, Arial"),
        margin=dict(l=0, r=0, t=0, b=0),
        height=50 + 90 * len(author_counts),
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
    
    return fig, table_located_authors

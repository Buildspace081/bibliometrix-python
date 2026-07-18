from www.services import *
from pyvis.network import Network
import tempfile
import pandas as pd
import networkx as nx
import os
from matplotlib.colors import to_rgba

def hex_to_rgba(hex_color, alpha):
    if not isinstance(hex_color, str) or not hex_color.startswith("#") or len(hex_color) != 7:
        hex_color = "#999999"  # fallback grigio neutro
    try:
        r, g, b = tuple(int(hex_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        r, g, b = (153, 153, 153)  # fallback rgb(153,153,153)
    return f"rgba({r},{g},{b},{alpha})"



def get_historiograph(df, node_label="AU1", histNodes=20, hist_isolates=True, histlabelsize=3, histsize=4, sep=";"):
    """
    Genera la historiograph e ritorna anche un file HTML interattivo con Pyvis.

    Returns:
        hist_plot: oggetto con layout e grafo networkx
        hist_data: dataframe con metadati, DOI cliccabili, cluster, anni
        filename: nome del file HTML interattivo salvato temporaneamente

        None se la sorgente del DataFrame non e' supportata per l'analisi
        citazionale diretta (vedi nota sotto), invece di sollevare TypeError.
    """
    # Pre-elaborazione
    df = metaTagExtraction(df, "SR")
    hist_results = histNetwork(df, min_citations=0, sep=sep, network=True)

    # LIMITE NOTO (debugging step, vedi anche get_local_cited_authors.py e
    # get_local_cited_documents.py per lo stesso pattern): www/services/histnetwork.py::histNetwork
    # supporta solo DB == "Web_of_Science" o "Scopus" (righe 37-43 di quel file);
    # per qualunque altro valore di DB — incluso il nostro "OPENALEX", ma anche
    # Dimensions/The_Lens/PubMed/Cochrane della pipeline storica stessa — stampa
    # "Database not compatible with direct citation analysis" e ritorna None
    # PRIMA di toccare la colonna CR. Non e' quindi un problema di formato di CR:
    # la funzione non arriva mai a parsarlo per queste sorgenti.
    #
    # Deliberatamente NON abbiamo esteso histNetwork con un ramo "OPENALEX":
    # 1) il ramo wos() dipende da M['SR_FULL'], colonna che la nostra pipeline
    #    scarta deliberatamente perche' non fa parte dello schema canonico a 34
    #    colonne (vedi openalex_mapper.py::_compute_calculated_fields) — andrebbe
    #    comunque in KeyError;
    # 2) anche risolvendo (1), wos() cerca auto-citazioni ESATTE all'interno
    #    della stessa collezione (un paper che cita un altro paper anch'esso nei
    #    risultati): su un campione generico di poche decine di risultati da una
    #    query testuale, la rete risultante sarebbe quasi sempre vuota — non un
    #    bug, ma un risultato di scarso valore che non giustifica lo sforzo;
    # 3) il ramo scopus() si aspetta l'anno tra parentesi nel riferimento
    #    (regex r'.*\((\d{4})\).*'), formato diverso dal nostro CR
    #    "Autore, ANNO, Rivista" (anno non tra parentesi) — anche qui non un
    #    crash, ma zero citazioni valide trovate silenziosamente.
    # Qui ci limitiamo quindi a intercettare il None e propagarlo pulito, con lo
    # stesso significato di "nessun risultato" gia' usato ovunque in app.py per
    # questo tipo di analisi (historiograph_results = reactive.Value(None), con
    # ogni consumer che fa `if result is not None` e mostra un placeholder
    # altrimenti) — nessuna nuova convenzione introdotta.
    if hist_results is None:
        return None

    # 1. Costruzione iniziale del grafo
    hist_plot = histPlot(
        hist_results,
        n=histNodes,
        size=histsize,
        remove_isolates=False,  # rimozione manuale
        label=node_label,
        verbose=False
    )

    # 2. Recupera layout e rete iniziale
    layout_df = pd.DataFrame(hist_plot["layout"]).copy()
    full_net = hist_plot["net"]

    # 3. Filtra archi per mantenere solo quelli con nodi nel top-N
    selected_nodes = set(full_net.nodes())
    edges_filtered = [(u, v) for u, v in full_net.edges() if u in selected_nodes and v in selected_nodes]

    # 4. Ricostruisci rete filtrata
    net_nx = nx.DiGraph()
    net_nx.add_nodes_from(selected_nodes)
    net_nx.add_edges_from(edges_filtered)

    # 5. Opzionale: rimuovi componenti isolate
    if hist_isolates:
        connected_components = list(nx.connected_components(net_nx.to_undirected()))
        valid_components = [c for c in connected_components if len(c) > 1]
        valid_nodes = set().union(*valid_components)
        net_nx = net_nx.subgraph(valid_nodes).copy()
    else:
        valid_nodes = set(net_nx.nodes)

    # 6. Filtra layout
    layout_df = layout_df[layout_df.index.isin(valid_nodes)].copy()
    layout_df["name"] = layout_df.index
    layout_df.reset_index(drop=True, inplace=True)

    # 7. Filtra hist_data in base ai nodi presenti nel grafo
    hist_data = hist_results["histData"].copy()
    hist_data = hist_data[hist_data["Paper"].isin(valid_nodes)].copy()
    hist_data = hist_data.merge(layout_df, left_on="Paper", right_on="name", how="left")


    # Cluster da colore
    if "color" in hist_data.columns:
        unique_colors = hist_data['color'].dropna().unique()
        color_to_cluster = {color: idx + 1 for idx, color in enumerate(unique_colors)}
        hist_data['cluster'] = hist_data['color'].map(color_to_cluster)
    else:
        hist_data['color'] = "gray"
        hist_data['cluster'] = -1

    # Formattazione DOI cliccabile
    hist_data['DOI'] = hist_data['DOI'].apply(
        lambda doi: f'<a href="https://doi.org/{doi}" target="_blank">{doi}</a>' if pd.notnull(doi) else ""
    )

    # Rimozione Year mancanti
    hist_data = hist_data[hist_data["Year"].notna()].copy()
    if hist_data.empty:
        raise ValueError("Nessun dato con 'Year' valido per la historiograph.")

    # Posizionamento temporale orizzontale
    hist_data = hist_data.sort_values(['cluster', 'Year'])
    min_year = hist_data["Year"].min()
    year_range = hist_data["Year"].max() - min_year + 1
    # Spazio orizzontale compatto
    hist_data["x"] = (hist_data["Year"] - min_year) * 60  # invece di /year_range * 1000

    # Spazio verticale più ravvicinato tra cluster
    hist_data["y"] = hist_data["cluster"] * 150 + np.random.uniform(-30, 30, size=len(hist_data))


    # Tooltip e label robusti
    hist_data["tooltip"] = hist_data.apply(
        lambda row: (
            f"<b>{str(row.get('Title', 'No Title')).replace('<', '&lt;').replace('>', '&gt;')}</b>"
            f"<br><b>Year:</b> {row.get('Year', 'n.d.')}"
            f"<br><b>DOI:</b> {row.get('DOI', '')}"
            f"<br><b>LCS:</b> {int(row.get('LCS', 0))}"
            f"<br><b>GCS:</b> {int(row.get('GCS', 0))}"
        ),
        axis=1
    )
    hist_data["label"] = hist_data.apply(
        lambda row: str(row.get("Title", "No Title"))[:40] + "..." if len(str(row.get("Title", ""))) > 40 else str(row.get("Title", "No Title")),
        axis=1
    )

    # Calcola opacità dinamica e dimensione font
    min_font_size = 10
    max_font_size = 130
    base_font_size = 24  # oppure calcolato in base a metrica
    font_opacity = np.sqrt((histlabelsize - min_font_size) / (max_font_size - min_font_size)) * 0.8 + 0.3
    font_opacity = max(0.1, min(1, font_opacity))  # clamp tra 0.1 e 1


    # Calcola dimensione proporzionale a LCS
    if "LCS" in hist_data.columns and not hist_data["LCS"].isnull().all():
        lcs_min = hist_data["LCS"].min()
        lcs_max = hist_data["LCS"].max()
        lcs_range = lcs_max - lcs_min if lcs_max > lcs_min else 1
        hist_data["node_size"] = hist_data["LCS"].apply(lambda lcs: 10 + ((lcs - lcs_min) / lcs_range) * 10)
    else:
        hist_data["node_size"] = histsize

    # Inizializza grafo Pyvis
    net = Network(height="98vh", width="100%", directed=True, notebook=True, cdn_resources="in_line")
    net.toggle_physics(False)

    # Aggiungi nodi
    for _, row in hist_data.iterrows():
        base_color = row.get("color", "#999999")
        color_rgba = hex_to_rgba(base_color, 0.8)
        border_color = hex_to_rgba(base_color, 0.4)

        if node_label == "AU1":
            label_value = row.get("id", f"{row.get('name', 'unknown')}, {row.get('Year', 'n.d.')}")
        elif node_label == "TI":
            label_value = row.get("Title", "No Title")
        elif node_label == "ID":
            try:
                keywords = eval(row.get("Author_Keywords", "[]")) if isinstance(row.get("Author_Keywords"), str) else row.get("Author_Keywords", [])
                label_value = "; ".join(keywords) if keywords else "No keywords"
            except:
                label_value = "No keywords"
        elif node_label == "DE":
            try:
                keywords = eval(row.get("KeywordsPlus", "[]")) if isinstance(row.get("KeywordsPlus"), str) else row.get("KeywordsPlus", [])
                label_value = "; ".join(keywords) if keywords else "No keywords"
            except:
                label_value = "No keywords"
        else:
            label_value = "unknown"

        net.add_node(
            n_id=row["Paper"],
            label=label_value,
            title=row["tooltip"],
            color={
                "background": color_rgba,
                "border": border_color,
                "highlight": {
                    "background": color_rgba,
                    "border": "#000000"
                }
            },
            x=row["x"],
            y=row["y"],
            size=row["node_size"],
            font={
                "size": histlabelsize,
                "face": "arial",
                "color": f"rgba(0,0,0,{font_opacity})"
            },
            borderWidth=2,
            borderWidthSelected=3,
            physics=False,
            fixed={"x": True, "y": False}  # blocca solo l'asse x
        )

    # Aggiungi archi con ombreggiatura
    existing_nodes = set(net.get_nodes())
    for source, target in net_nx.edges():
        if source in existing_nodes and target in existing_nodes:
            source_color = hist_data.loc[hist_data["Paper"] == source, "color"].values[0]
            edge_color = hex_to_rgba(source_color, 0.4)
            net.add_edge(source, target, color=edge_color, width=1.5)

    # Salva HTML temporaneo
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    html_path = tmp.name
    with open(html_path, 'w', encoding="utf-8") as f:
        html = net.generate_html()
        new_css = "     .card {\n                 border: none;\n             }"
        updated_html = html.replace("</style>", new_css + "\n        </style>")
        updated_html = updated_html.replace("1px solid lightgray", "none")
        
        f.write(updated_html)

    return hist_plot, hist_data, html_path.split(os.sep)[-1]

from www.services import *


def get_clustering_coupling(df, unit_of_analysis, coupling_measured, stemmer, impact_measure,
                            cluster_labeling, ngram, num_of_units, min_cluster_freq,
                            label_per_cluster, label_size, community_repulsion,
                            clustering_algorithm, node_shape='dot'):
    # LIMITE NOTO (non investigato oltre in questa sessione, fuori scope):
    # "Cluster by Coupling" risulta lento con dati OpenAlex per una causa non
    # identificata nella costruzione della matrice di coupling/coincidenza
    # citazionale (couplingMap -> network -> biblionetwork/cocMatrix/
    # network_plot in www/services/couplingmap.py), indipendente dal nostro
    # standardizzatore. La dimensione del calcolo principale (matrice N x N
    # documenti, N ~ 30) e' teoricamente troppo piccola per giustificare una
    # lentezza reale, quindi non sembra un limite "normale ma lento" per
    # questo volume di dati - ma la causa esatta non e' stata isolata (analisi
    # non validata, si sospetta codice preesistente del professore, non
    # necessariamente legato al formato di CR). Separato dal bug gia' corretto
    # in couplingmap.py::localCitations (histNetwork che ritornava None senza
    # gestione), che riguarda un crash successivo, non questa lentezza.

    # Generate coupling map
    coupling_map = couplingMap(
        df,
        analysis=unit_of_analysis,
        field=coupling_measured,
        n=num_of_units,
        minfreq=min_cluster_freq,
        ngrams=ngram,
        community_repulsion=community_repulsion,
        impact_measure=impact_measure,
        stemming=stemmer,
        size=label_size,
        label_term=cluster_labeling,
        n_labels=label_per_cluster,
        repel=False,
        clustering=clustering_algorithm  
    )

    ### Plotting the coupling map
    fig = coupling_map['map']
    fig.update_layout(
        height=750,
        autosize=True,
        width=None,
        showlegend=True,
        margin=dict(t=20)  # aggiunge spazio bianco sopra
    )
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    cm_data = coupling_map['data']
    cm_clusters = coupling_map['clusters']

    # Get graph and verify it's an igraph object
    graph = coupling_map['net']['graph']
    if not isinstance(graph, ig.Graph):
        raise TypeError("Expected an igraph.Graph object in 'couplingMap['net']['graph'].")
    
    # Initialize Pyvis network with matching R settings
    net = Network(height="98vh", width="100%", notebook=True, cdn_resources="in_line")
    net.toggle_physics(False)

    # Use colors from df['adjusted_color']
    unique_clusters = set(coupling_map['net']['cluster_obj'].membership)
    cluster_colors = {}
    
    # Get unique cluster IDs and their colors
    for i, cluster_id in enumerate(unique_clusters):
        if i < len(cm_clusters):
            # Get hex color from DataFrame and convert to rgba
            hex_color = cm_clusters['adjusted_color'].iloc[i]
            # Convert hex to rgb format
            hex_color = hex_color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            cluster_colors[cluster_id] = f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.3)"
        else:
            # Fallback for any additional clusters
            cluster_colors[cluster_id] = f"rgba(128,128,128,0.3)"  # Default gray

    # Generate layout
    layout = graph.layout_fruchterman_reingold()
    # Get coordinates from layout
    coords = np.array([[pos[0], pos[1]] for pos in layout])
    
    # Scale coordinates to fit 800px height
    # First normalize to [-1,1] range
    coords = coords / np.abs(coords).max()
    
    # Then scale to target dimensions
    # Width will be proportional to maintain aspect ratio
    coords[:, 0] *= 1000  # Scale x coordinates 
    coords[:, 1] *= 400   # Scale y coordinates to fit 800px (centered)

    # Prepare for avoid_net_overlaps
    node_labels = [v["name"] if "name" in v.attributes() else f"Node {v.index}" for v in graph.vs]
    node_sizes = []
    nodes = []
    
    # Add nodes with matching R visNetwork settings
    for idx, vertex in enumerate(graph.vs):
        cluster_id = coupling_map['net']['cluster_obj'].membership[vertex.index]
        node_color = cluster_colors[cluster_id]

        # Normalize node sizes
        min_deg, max_deg = min(graph.degree()), max(graph.degree())
        node_size = 30 if max_deg == min_deg else (35 * (vertex.degree() - min_deg) / (max_deg - min_deg) + 30)
        node_size = max(30, min(150, node_size))
        font_size = node_size * 2.5
        node_sizes.append(node_size)
        
        # Set font opacity based on node size
        if font_size < 90:
            font_opacity = 0.4
        elif 90 <= font_size < 100:
            font_opacity = 0.6
        elif 100 <= font_size < 120:
            font_opacity = 0.8
        else:  
            font_opacity = 1.0

        # Calculate font opacity using R-like formula
        # min_font_size = 80   # Minimum node size 
        # max_font_size = 150  # Maximum node size 
        # font_opacity = np.sqrt((font_size - min_font_size) / (max_font_size - min_font_size)) 
        # font_opacity = max(0.1, min(1, font_opacity))  # Clamp between 0.3 and 0.8
        
        nodes.append({
            'id': vertex.index,
            'label': vertex["name"] if "name" in vertex.attributes() else f"Node {vertex.index}",
            'title': vertex["name"] if "name" in vertex.attributes() else f"Node {vertex.index}",
            'color': node_color,
            'size': node_size,
            'font': {
                'size': font_size, 
                'color': f'rgba(0,0,0,{font_opacity})', 
                'vadjust': -0.7*font_size if node_shape.lower() in ['dot', 'square'] else 0
            },
            'shadow': True,
            'shape': 'dot',
            'x': layout[idx][0] * 1000,
            'y': layout[idx][1] * 1000
        })

    # Remove overlapping labels
    noOverlap = True
    if noOverlap:
        threshold = 0.05
        ymax = np.ptp(coords[:, 1])  # equivalent to diff(range())
        xmax = np.ptp(coords[:, 0])
        threshold2 = threshold * np.mean([xmax, ymax])
        
        # Create data structure for overlap checking
        labels_to_remove = avoid_net_overlaps(coords, node_labels, node_sizes, threshold=threshold2)
    else:
        labels_to_remove = []
    #labels_to_remove = avoid_net_overlaps(coords, node_labels, node_sizes, threshold=0.05)
    
    # Add nodes to network
    unique_nodes = {node['id']: node for node in nodes}.values()
    for node in unique_nodes:
        if node['label'] in labels_to_remove:
            node['label'] = ''
        net.add_node(node['id'], **node)

    # Add edges with improved styling matching R implementation
    added_edges = set()
    edge_weights = [e.attributes().get('weight', 1) for e in graph.es]
    max_weight = max(edge_weights) if edge_weights else 1
    
    for edge in graph.es:
        source, target = edge.tuple
        cluster_source = coupling_map['net']['cluster_obj'].membership[source]
        cluster_target = coupling_map['net']['cluster_obj'].membership[target]
        
        # Set edge color with proper opacity
        if cluster_source == cluster_target:
            base_color = cluster_colors[cluster_source]
            # Convert rgba to hex with opacity
            rgba_values = [int(x) for x in base_color[5:-1].split(',')[:-1]]
            edge_color = f"rgba({rgba_values[0]},{rgba_values[1]},{rgba_values[2]},0.56)"
        else:
            # Use darker gray for inter-cluster edges (equivalent to #69696960 in R)
            edge_color = "rgba(105,105,105,0.38)"
        
        # Calculate edge width similar to R implementation
        edge_weight = edge.attributes().get('weight', 1)
        normalized_weight = (edge_weight ** 2 / (max_weight ** 2)) * (10 + 2.5)  # 2.5 is base edge size
        
        edge_tuple = (source, target) if source < target else (target, source)
        
        # Add edge if not already added
        if edge_tuple not in added_edges:
            net.add_edge(
                source, 
                target, 
                color=edge_color,
                width=normalized_weight,
                smooth={'type': 'horizontal'},
                dashes=False  # Set to True if you have line type information
            )
            added_edges.add(edge_tuple)

    # Configure network options to match R visNetwork
    net.set_options("""
        var options = {
            "nodes": {
                "shadow": true
            },
            "edges": {
                "smooth": {"type": "horizontal"}
            },
            "interaction": {
                "dragNodes": true,
                "hideEdgesOnDrag": true,
                "navigationButtons": false,
                "zoomSpeed": 0.4
            },
            "physics": {
                "enabled": false
            },
            "manipulation": {
                "enabled": false
            }
        }
    """)

    # Save network to HTML
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    html_path = tmp.name
    with open(html_path, 'w', encoding="utf-8") as f:
        html = net.generate_html()
        new_css = "     .card {\n                 border: none;\n             }"
        updated_html = html.replace("</style>", new_css + "\n        </style>")
        updated_html = updated_html.replace("1px solid lightgray", "none")
        
        f.write(updated_html)

    return fig, html_path.split(os.sep)[-1], cm_data, cm_clusters

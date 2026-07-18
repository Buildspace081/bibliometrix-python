"""
Mapping OpenAlex -> schema a 34 colonne WoS-style.

Speculare a www/services/format_functions.py (che copre WoS/Scopus/Dimensions/
The_Lens/PubMed/Cochrane): qui e' definita una sola sorgente, "OpenAlex", con una
funzione format_XX_column per ciascuna delle 34 colonne dello schema bibliometrix,
piu' una funzione di orchestrazione map_work_to_record che le combina in un unico
record cosi' come fa il blocco `entry_data = {...}` in format_functions.py::process_single_file.

Differenze principali rispetto alla pipeline WoS storica, da tenere presenti in
fase di implementazione (vedi analisi fatta in conversazione):
- authorships[].institutions[] e' gia' strutturato (niente split posizionali su
  stringhe di affiliazione ne' whitelist di paesi come in metatagextraction.py::AU_CO).
- abstract_inverted_index va ricostruito in una stringa lineare prima di popolare AB.
- referenced_works e' solo una lista di ID: per popolare CR con citazioni leggibili
  serve l'output di openalex_client.get_works_by_ids (parametro resolved_references).
- cited_by_count e' gia' un int (a differenza di TC in format_tc_column, che restava
  stringa quando proveniva da WoS .txt/.ciw).
- alcune colonne dello schema WoS-style non hanno, per decisione esplicita presa in
  fase di design, un equivalente popolato in questa pipeline: EM, FU, FX, JI, OI,
  PU, RP, SC restituiscono sempre stringa vuota (vedi i rispettivi format_XX_column
  per la motivazione puntuale), anche quando OpenAlex esporrebbe un dato parziale
  utilizzabile (es. RP da `is_corresponding`, PU da `host_organization_name`). JI
  vuota e' pero' intenzionale anche nella pipeline WoS storica per le sorgenti
  senza abbreviazione (vedi format_ji_column): non e' un dato mancante, e'
  il segnale che fa scattare il fallback su SO dentro metatagextraction.py::SR.
- SN (ISSN) deriva da `primary_location.source.issn_l`, spostato qui da JI dopo
  aver verificato che SN e' il campo ISSN in tutte le sorgenti storiche
  (format_functions.py::format_sn_column).
- SR (Short Reference) NON ha una format_sr_column(work) a livello di singolo
  record, a differenza delle altre colonne: la funzione esistente riusata per
  calcolarla, metatagextraction.py::SR(M), richiede l'INTERA collezione gia'
  in forma di DataFrame per poter deduplicare correttamente i valori ripetuti
  (suffissi "-a", "-b", ...). Vedi compute_sr_for_records più in basso e
  etl_pipeline.py::_compute_calculated_fields per come viene usata.
"""

from .utils import *
from .metatagextraction import SR


# Numero massimo di referenced_works considerati da format_cr_column per un
# singolo work. Decisione presa in questo punto dello sviluppo (non
# preesistente): alcuni work OpenAlex citano centinaia di referenze, e
# risolverle/formattarle tutte avrebbe un costo (chiamate batch a
# get_works_by_ids, dimensione di CR) sproporzionato rispetto al beneficio per
# un campo che nello schema WoS-style e' comunque una lista informativa, non
# esaustiva per definizione in molte fonti.
MAX_REFERENCED_WORKS = 100

# Mappa dichiarativa colonna WoS-style -> percorso/estrattore OpenAlex.
# Pensata come documentazione leggibile del mapping (colonna -> dove si trova il
# dato in un oggetto "work" OpenAlex), non necessariamente usata a runtime.
# Popolata in fase di implementazione con il mapping discusso in conversazione,
# es.: {"TI": "title", "PY": "publication_year", "SO": "primary_location.source.display_name", ...}
OPENALEX_FIELD_MAP: dict = {}

# Mappa OpenAlex `type` (vocabolario controllato, vedi
# https://docs.openalex.org/api-entities/works/work-object#type) -> vocabolario
# WoS-style per la colonna DT. Copre i type piu' comuni; un type OpenAlex non
# presente qui non e' un errore: format_dt_column ricade sul valore originale
# capitalizzato invece di perdere l'informazione (vedi format_dt_column).
OPENALEX_TYPE_TO_WOS_DT: dict = {
    "article": "Article",
    "review": "Review",
    "book-chapter": "Book Chapter",
    "preprint": "Preprint",
    "dataset": "Dataset",
    "dissertation": "Thesis",
    "book": "Book",
    "editorial": "Editorial Material",
    "letter": "Letter",
    "erratum": "Correction",
    "report": "Report",
    "peer-review": "Peer Review",
    "paratext": "Paratext",
    "standard": "Standard",
    "grant": "Grant",
    "supplementary-materials": "Supplementary Materials",
    "reference-entry": "Reference Entry",
    "other": "Other",
}

# Lookup ISO 3166-1 alpha-2 -> nome paese, nella STESSA convenzione di naming usata
# dalla whitelist in www/static/countries.txt (consumata da
# metatagextraction.py::AU_CO/AU1_CO/AU_UN). I nomi qui DEVONO combaciare
# esattamente con le righe di quel file, cosi' che una stringa C1 costruita da
# format_c1_column resti riconoscibile dal matching a valle
# (`c1.split(",")[-1].strip().upper()` + ricerca `\b<paese>\b` nella whitelist)
# senza dover toccare metatagextraction.py.
#
# Note sulle scelte fatte per allinearsi a countries.txt:
# - "US" -> "UNITED STATES" (non "USA": entrambe le forme sono in whitelist, ma
#   AU_CO() normalizza comunque "UNITED STATES" -> "USA" a valle, quindi il
#   risultato finale coincide).
# - "GB" -> "UNITED KINGDOM" (in whitelist esistono anche ENGLAND/SCOTLAND/WALES/
#   NORTH IRELAND come alias storici WoS, ma non sono codici ISO e OpenAlex non
#   li restituisce mai come country_code).
# - "RU" -> "RUSSIA" (non "RUSSIAN FEDERATION", assente dalla whitelist).
# - "MK" -> "NORTH MACEDONIA" (nome ISO corrente; "MACEDONIA" resta in whitelist
#   come alias storico ma non e' il target di questa lookup).
# - "TW" -> "TAIWAN" (AU_CO() normalizza comunque "TAIWAN" -> "CHINA" a valle).
# - "CD" -> "CONGO" (la whitelist ha una sola voce "CONGO", senza distinzione
#   Congo-Brazzaville/Congo-Kinshasa; stessa approssimazione gia' presente li').
ISO_COUNTRY_CODE_TO_NAME: dict = {
    "AF": "AFGHANISTAN", "AL": "ALBANIA", "DZ": "ALGERIA", "AD": "ANDORRA",
    "AO": "ANGOLA", "AG": "ANTIGUA", "AR": "ARGENTINA", "AM": "ARMENIA",
    "AU": "AUSTRALIA", "AT": "AUSTRIA", "AZ": "AZERBAIJAN", "BS": "BAHAMAS",
    "BH": "BAHRAIN", "BD": "BANGLADESH", "BB": "BARBADOS", "BY": "BELARUS",
    "BE": "BELGIUM", "BZ": "BELIZE", "BJ": "BENIN", "BT": "BHUTAN",
    "BO": "BOLIVIA", "BA": "BOSNIA", "BW": "BOTSWANA", "BR": "BRAZIL",
    "BN": "BRUNEI", "BG": "BULGARIA", "BF": "BURKINA FASO", "BI": "BURUNDI",
    "CV": "CABO VERDE", "KH": "CAMBODIA", "CM": "CAMEROON", "CA": "CANADA",
    "CF": "CENTRAL AFRICAN REPUBLIC", "TD": "CHAD", "CL": "CHILE", "CN": "CHINA",
    "CO": "COLOMBIA", "KM": "COMOROS", "CG": "CONGO", "CD": "CONGO",
    "CR": "COSTA RICA", "CI": "COTE D'IVOIRE", "HR": "CROATIA", "CU": "CUBA",
    "CY": "CYPRUS", "CZ": "CZECH REPUBLIC", "DK": "DENMARK", "DJ": "DJIBOUTI",
    "DM": "DOMINICA", "DO": "DOMINICAN REPUBLIC", "EC": "ECUADOR", "EG": "EGYPT",
    "SV": "EL SALVADOR", "GQ": "EQUATORIAL GUINEA", "ER": "ERITREA",
    "EE": "ESTONIA", "ET": "ETHIOPIA", "FO": "FAROE", "FJ": "FIJI",
    "FI": "FINLAND", "FR": "FRANCE", "GA": "GABON", "GM": "GAMBIA",
    "GE": "GEORGIA", "DE": "GERMANY", "GH": "GHANA", "GR": "GREECE",
    "GU": "GUAM", "GT": "GUATEMALA", "GN": "GUINEA", "GW": "GUINEA-BISSAU",
    "HT": "HAITI", "HN": "HONDURAS", "HK": "HONG KONG", "HU": "HUNGARY",
    "IS": "ICELAND", "IN": "INDIA", "ID": "INDONESIA", "IR": "IRAN",
    "IQ": "IRAQ", "IE": "IRELAND", "IL": "ISRAEL", "IT": "ITALY",
    "JM": "JAMAICA", "JP": "JAPAN", "JO": "JORDAN", "KZ": "KAZAKHSTAN",
    "KE": "KENYA", "KI": "KIRIBATI", "KR": "KOREA", "XK": "KOSOVO",
    "KW": "KUWAIT", "KG": "KYRGYZSTAN", "LA": "LAOS", "LV": "LATVIA",
    "LB": "LEBANON", "LS": "LESOTHO", "LR": "LIBERIA", "LY": "LIBYA",
    "LI": "LIECHTENSTEIN", "LT": "LITHUANIA", "LU": "LUXEMBOURG",
    "MK": "NORTH MACEDONIA", "MG": "MADAGASCAR", "MW": "MALAWI",
    "MY": "MALAYSIA", "MV": "MALDIVES", "ML": "MALI", "MT": "MALTA",
    "MH": "MARSHALL ISLANDS", "MR": "MAURITANIA", "MU": "MAURITIUS",
    "MX": "MEXICO", "FM": "MICRONESIA", "MD": "MOLDOVA", "MC": "MONACO",
    "MN": "MONGOLIA", "ME": "MONTENEGRO", "MA": "MOROCCO", "MZ": "MOZAMBIQUE",
    "MM": "MYANMAR", "NA": "NAMIBIA", "NR": "NAURU", "NP": "NEPAL",
    "NL": "NETHERLANDS", "NZ": "NEW ZEALAND", "NI": "NICARAGUA", "NE": "NIGER",
    "NG": "NIGERIA", "KP": "NORTH KOREA", "NO": "NORWAY", "OM": "OMAN",
    "PK": "PAKISTAN", "PW": "PALAU", "PA": "PANAMA", "PG": "PAPUA NEW GUINEA",
    "PY": "PARAGUAY", "PE": "PERU", "PH": "PHILIPPINES", "PL": "POLAND",
    "PT": "PORTUGAL", "QA": "QATAR", "RO": "ROMANIA", "RU": "RUSSIA",
    "RW": "RWANDA", "KN": "SAINT KITTS AND NEVIS", "LC": "SAINT LUCIA",
    "WS": "SAMOA", "SM": "SAN MARINO", "ST": "SAO TOME AND PRINCIPE",
    "SA": "SAUDI ARABIA", "SN": "SENEGAL", "RS": "SERBIA", "SC": "SEYCHELLES",
    "SL": "SIERRA LEONE", "SG": "SINGAPORE", "SK": "SLOVAKIA", "SI": "SLOVENIA",
    "SB": "SOLOMON ISLANDS", "SO": "SOMALIA", "ZA": "SOUTH AFRICA",
    "SS": "SOUTH SUDAN", "ES": "SPAIN", "LK": "SRI LANKA", "SD": "SUDAN",
    "SR": "SURINAME", "SZ": "SWAZILAND", "SE": "SWEDEN", "CH": "SWITZERLAND",
    "SY": "SYRIA", "TW": "TAIWAN", "TJ": "TAJIKISTAN", "TZ": "TANZANIA",
    "TH": "THAILAND", "TG": "TOGO", "TO": "TONGA", "TT": "TRINIDAD AND TOBAGO",
    "TN": "TUNISIA", "TR": "TURKEY", "TM": "TURKMENISTAN", "UG": "UGANDA",
    "UA": "UKRAINE", "AE": "UNITED ARAB EMIRATES", "GB": "UNITED KINGDOM",
    "US": "UNITED STATES", "UY": "URUGUAY", "UZ": "UZBEKISTAN", "VU": "VANUATU",
    "VA": "VATICANO", "VE": "VENEZUELA", "VN": "VIETNAM", "YE": "YEMEN",
    "ZM": "ZAMBIA", "ZW": "ZIMBABWE",
}


def map_work_to_record(work, resolved_references=None):
    """
    Funzione di orchestrazione: converte un singolo oggetto "work" OpenAlex grezzo
    in un record (dict) nello schema a 34 colonne WoS-style, chiamando in sequenza
    tutte le format_XX_column definite in questo modulo.

    Analoga al blocco `entry_data = {...}` in
    www/services/format_functions.py::process_single_file, ma con un'unica sorgente
    (OpenAlex) invece del branching multi-sorgente/multi-formato usato li'.

    Non calcola i campi che richiedono l'intera collezione (es. SR, che necessita
    di deduplicare "Autore, Anno, Rivista" su tutto il dataset): quello e' compito
    di etl_pipeline.py::_compute_calculated_fields, eseguito dopo questa funzione.

    Args:
        work: dict, singolo oggetto "work" grezzo restituito da OpenAlex
            (vedi openalex_client.search_works).
        resolved_references: dict[str, dict] opzionale, mappa ID OpenAlex -> work
            risolto, usata da format_cr_column per costruire citazioni leggibili a
            partire da `referenced_works`. None se la risoluzione e' stata saltata
            (in quel caso CR conterra' presumibilmente i soli ID grezzi).

    Returns:
        dict: record con esattamente le chiavi di `columns` (lista canonica
        definita in www/services/utils.py) meno "SR" — 33 chiavi in totale.

    Raises:
        ValueError: se il dict costruito internamente non coincide esattamente
            (ne' per difetto ne' per eccesso) con `set(columns) - {"SR"}| —
            indica una regressione tra questa funzione e la lista canonica in
            utils.py, non un problema sui dati del work in input.
    """
    record = {
        "AB": format_ab_column(work),
        "AF": format_af_column(work),
        "AU": format_au_column(work),
        "AU_UN": format_au_un_column(work),
        "AU1_UN": format_au1_un_column(work),
        "BP": format_bp_column(work),
        "EP": format_ep_column(work),
        "CR": format_cr_column(work, resolved_references),
        "C1": format_c1_column(work),
        "DB": format_db_column(work),
        "DE": format_de_column(work),
        "DI": format_di_column(work),
        "DT": format_dt_column(work),
        "EM": format_em_column(work),
        "FU": format_fu_column(work),
        "FX": format_fx_column(work),
        "IS": format_is_column(work),
        "JI": format_ji_column(work),
        "ID": format_id_column(work),
        "LA": format_la_column(work),
        "OA": format_oa_column(work),
        "OI": format_oi_column(work),
        "PMID": format_pmid_column(work),
        "PU": format_pu_column(work),
        "PY": format_py_column(work),
        "RP": format_rp_column(work),
        "SC": format_sc_column(work),
        "SN": format_sn_column(work),
        "SO": format_so_column(work),
        "TC": format_tc_column(work),
        "TI": format_ti_column(work),
        "UT": format_ut_column(work),
        "VL": format_vl_column(work),
    }

    expected_keys = set(columns) - {"SR"}
    actual_keys = set(record.keys())
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        raise ValueError(
            "map_work_to_record: il record prodotto non coincide con lo schema "
            "canonico (www/services/utils.py::columns) meno SR. "
            f"Mancanti: {missing}. Extra: {extra}."
        )

    return record


def format_ab_column(work):
    """
    Colonna AB (Abstract). Ricostruisce il testo lineare dell'abstract a partire da
    `work["abstract_inverted_index"]` (dict parola -> lista di posizioni), che in
    OpenAlex sostituisce l'abstract come stringa unica presente in WoS.

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: abstract ricostruito, oppure stringa vuota se `abstract_inverted_index`
        e' assente/None (es. per motivi di copyright, come spesso accade in OpenAlex).
    """
    return _reconstruct_abstract(work.get("abstract_inverted_index"))


def format_af_column(work):
    """
    Colonna AF (Authors Full Name). Per la sorgente OpenAlex coincide
    esattamente con AU (vedi format_au_column e la nota nel suo docstring):
    entrambe derivano da `work["authorships"][].author.display_name` senza
    alcuna trasformazione. Questa funzione delega direttamente a
    format_au_column invece di duplicarne la logica.

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        list[str]: identico all'output di format_au_column(work).
    """
    return format_au_column(work)


def format_au_column(work):
    """
    Colonna AU (Author/s). A differenza di format_au_column in
    format_functions.py (che normalizza WoS/Scopus/ecc. nel formato "COGNOME
    Iniziali"), qui si usa direttamente `work["authorships"][].author.display_name`
    cosi' come restituito da OpenAlex, senza alcuna logica di split cognome/nome:
    scelta deliberata per evitare euristiche fragili sui nomi (es. nomi composti,
    prefissi, ordini cognome-nome non occidentali) quando il dato "display_name"
    e' gia' disponibile in forma leggibile.

    Nota: con questa scelta AU e AF risultano uguali per la sorgente OpenAlex
    (entrambi il nome completo dell'autore), a differenza della pipeline WoS
    storica dove sono formati distinti ("Cognome I." vs "Cognome, Nome completo").

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        list[str]: un elemento per autore, pari a `author.display_name`,
        nell'ordine restituito da `work["authorships"]`. Autori senza `author` o
        senza `display_name` vengono omessi.
    """
    authors = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        display_name = author.get("display_name")
        if display_name:
            authors.append(display_name)
    return authors


def format_au_un_column(work):
    """
    Colonna AU_UN (Authors University/Institution). Estrae le istituzioni da
    `work["authorships"][].institutions[].display_name`, gia' strutturate e
    disambiguate da OpenAlex (a differenza di AU_UN in metatagextraction.py, che
    deve inferire l'istituzione da una stringa di affiliazione grezza tramite una
    whitelist di tag come "UNIV", "COLL", ecc.).

    Restituisce list[str] (non una singola stringa ";"-separated), per coerenza
    con cio' che si aspettano i consumer a valle sull'output della pipeline di
    import diretta (es. functions/get_affiliationproductionovertime.py e
    functions/get_relevantaffiliations.py, che trattano AU_UN come lista per
    riga tramite `.apply(...)`/`.explode()`).

    Deduplicazione: se piu' autori condividono la stessa istituzione (stesso
    `display_name`), questa compare una sola volta nell'output, preservando
    l'ordine di prima apparizione.

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        list[str]: nomi delle istituzioni distinte associate agli autori del work,
        lista vuota se `work["authorships"]` e' assente/vuoto o nessun autore ha
        institutions.
    """
    seen = set()
    universities = []
    for authorship in work.get("authorships") or []:
        for institution in authorship.get("institutions") or []:
            name = institution.get("display_name")
            if name and name not in seen:
                seen.add(name)
                universities.append(name)
    return universities


def format_au1_un_column(work):
    """
    Colonna AU1_UN (Institution of the First Author). A differenza di AU_UN,
    restituisce una singola stringa (non una lista), per coerenza con
    format_au1_un_column in format_functions.py (che restituisce sempre una
    stringa, es. `str(entry.get('C3','')).split("; ")[0]`) e con l'etichetta
    "First Author University" (singolare) usata in functions/get_table.py.

    Il primo autore e' individuato cercando `author_position == "first"` in
    `work["authorships"]`; se il campo non e' presente/valorizzato su nessun
    elemento, si ricade sul primo elemento della lista `authorships` (che in
    pratica coincide quasi sempre con l'autore in posizione "first").

    Se il primo autore ha piu' institutions, viene presa solo la prima (stessa
    scelta "solo il primo valore" fatta da format_au1_un_column in
    format_functions.py per WoS, che tiene solo l'indice 0 dopo lo split su C3).

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: nome dell'istituzione del primo autore, "" se non disponibile
        (nessun autore, primo autore senza institutions, o institution senza
        display_name).
    """
    authorships = work.get("authorships") or []
    if not authorships:
        return ""

    first_authorship = next(
        (a for a in authorships if a.get("author_position") == "first"),
        authorships[0],
    )

    institutions = first_authorship.get("institutions") or []
    if not institutions:
        return ""

    return institutions[0].get("display_name") or ""


def format_bp_column(work):
    """
    Colonna BP (Beginning Page). Deriva da `work["biblio"]["first_page"]`, con
    accesso robusto ai campi annidati: se `work["biblio"]` e' assente/None,
    viene trattato come dict vuoto invece di sollevare AttributeError/KeyError.

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: numero di pagina iniziale, "" se assente (comune per preprint,
        come visto nell'esempio arXiv analizzato in conversazione).
    """
    biblio = work.get("biblio") or {}
    return biblio.get("first_page") or ""


def format_ep_column(work):
    """
    Colonna EP (Ending Page). Deriva da `work["biblio"]["last_page"]`, con
    accesso robusto ai campi annidati: se `work["biblio"]` e' assente/None,
    viene trattato come dict vuoto invece di sollevare AttributeError/KeyError.

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: numero di pagina finale, "" se assente.
    """
    biblio = work.get("biblio") or {}
    return biblio.get("last_page") or ""


def format_cr_column(work, resolved_references=None):
    """
    Colonna CR (Cited References). Deriva da `work["referenced_works"]`, che in
    OpenAlex e' solo una lista di ID (non stringhe bibliografiche complete come
    in WoS).

    Funzione di solo mapping: non fa I/O di rete. `resolved_references` deve
    essere gia' stato popolato a monte (tipicamente da una singola chiamata
    batch a openalex_client.get_works_by_ids su tutti gli ID di
    `referenced_works` di uno o piu' work) e viene passato qui gia' pronto,
    per mantenere la separazione tra mapping puro (questo modulo) e I/O di
    rete (openalex_client.py).

    Per ogni ID in `work["referenced_works"]` (troncato a MAX_REFERENCED_WORKS
    elementi):
    - se l'ID e' presente in `resolved_references`, la citazione e' costruita
      nello stesso stile "Autore, ANNO, RIVISTA" usato da
      metatagextraction.py::SR, riusando format_au_column/format_py_column/
      format_so_column sul work risolto (vedi _format_reference_citation);
    - se l'ID NON e' risolvibile (risoluzione fallita, batch andato in errore,
      o resolved_references non fornito/None), il riferimento non viene
      scartato: l'ID OpenAlex nudo viene incluso cosi' com'e' come fallback,
      cosi' l'informazione "esiste un riferimento qui" non va persa in
      silenzio anche se non e' stato possibile arricchirla.

    Args:
        work: oggetto "work" OpenAlex grezzo.
        resolved_references: dict[str, dict] opzionale, mappa ID OpenAlex
            normalizzato -> work risolto (vedi openalex_client.get_works_by_ids).
            None o {} equivalgono a "nessuna risoluzione disponibile": tutti i
            riferimenti ricadono sul fallback ID nudo.

    Returns:
        list[str]: una voce per riferimento citato (citazione leggibile o ID
        nudo), nell'ordine di `work["referenced_works"]`, troncata a
        MAX_REFERENCED_WORKS elementi. Lista vuota se `referenced_works` e'
        assente/vuoto.
    """
    referenced_ids = (work.get("referenced_works") or [])[:MAX_REFERENCED_WORKS]
    resolved_references = resolved_references or {}

    citations = []
    for raw_id in referenced_ids:
        if not raw_id:
            continue

        normalized_id = raw_id.rsplit("/", 1)[-1]
        resolved_work = resolved_references.get(normalized_id)

        if resolved_work:
            citations.append(_format_reference_citation(resolved_work))
        else:
            citations.append(normalized_id)

    return citations


def _format_reference_citation(resolved_work):
    """
    Funzione interna: costruisce la citazione leggibile "Autore, ANNO, RIVISTA"
    per un singolo work OpenAlex risolto, riusando le format_XX_column gia'
    definite in questo modulo (format_au_column, format_py_column,
    format_so_column) invece di duplicare la logica di estrazione — stesso
    stile della formula "FirstAuthors, PY, J9" usata da
    metatagextraction.py::SR per il riferimento breve di un documento.

    Usata da format_cr_column.

    Args:
        resolved_work: dict, oggetto "work" OpenAlex grezzo del riferimento
            citato (gia' risolto tramite openalex_client.get_works_by_ids).

    Returns:
        str: "Autore, ANNO, RIVISTA". Il primo autore e' "NA" se il work
        risolto non ha autori (stessa convenzione di metatagextraction.py::SR);
        RIVISTA puo' comparire come stringa vuota se non disponibile sul work
        risolto; ANNO e' sempre presente come stringa numerica (0 se il work
        risolto non ha `publication_year`, vedi format_py_column).
    """
    authors = format_au_column(resolved_work)
    first_author = authors[0] if authors else "NA"
    year = format_py_column(resolved_work)  # int (vedi format_py_column) -> cast esplicito qui sotto
    journal = format_so_column(resolved_work)
    return f"{first_author}, {str(year)}, {journal}"


def format_c1_column(work):
    """
    Colonna C1 (Authors Affiliation). Fonte dati: i campi strutturati OpenAlex
    (`authorships[].author.display_name`, `authorships[].institutions[].display_name`,
    `authorships[].institutions[].country_code`), NON `raw_affiliation_strings`
    (testo grezzo non normalizzato).

    Ogni stringa di output e' costruita nel formato WoS-style
    "[NomeAutore] Nome Istituzione, PAESE" (paese in maiuscolo), riproducendo la
    convenzione con cui format_c1_column in format_functions.py rimuove il
    prefisso "[Autori] " dalle righe C1 di WoS — qui il prefisso viene invece
    generato ex novo a partire da un dato gia' strutturato.

    Il nome del paese e' ottenuto da ISO_COUNTRY_CODE_TO_NAME, che usa
    ESATTAMENTE la stessa convenzione di naming della whitelist in
    www/static/countries.txt: questo garantisce che
    metatagextraction.py::AU_CO/AU1_CO/AU_UN (che deriva paesi/istituzioni da C1
    facendo `c1.split(",")[-1].strip().upper()` e cercando il risultato nella
    whitelist) continui a funzionare invariato anche sulle righe C1 generate da
    questa funzione, senza bisogno di modifiche a valle.

    Un'istituzione senza `country_code` riconosciuto in ISO_COUNTRY_CODE_TO_NAME
    produce comunque una riga C1 valida, ma senza il segmento finale ", PAESE":
    in quel caso il matching a valle in AU_CO/AU1_CO semplicemente non trovera'
    un paese per quella affiliazione (stesso comportamento di una riga WoS con
    paese mancante/non riconosciuto).

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        list[str]: una stringa "[NomeAutore] Nome Istituzione, PAESE" per ogni
        combinazione (autore, istituzione) presente in `work["authorships"]`.
        Autori senza institutions non producono alcuna riga (nessuna affiliazione
        da riportare). Lista vuota se `work["authorships"]` e' assente/vuoto.
    """
    affiliations = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        author_name = author.get("display_name")
        if not author_name:
            continue

        for institution in authorship.get("institutions") or []:
            institution_name = institution.get("display_name")
            if not institution_name:
                continue

            country_code = institution.get("country_code")
            country_name = ISO_COUNTRY_CODE_TO_NAME.get((country_code or "").upper())

            if country_name:
                affiliation = f"[{author_name}] {institution_name}, {country_name}"
            else:
                affiliation = f"[{author_name}] {institution_name}"

            affiliations.append(affiliation)

    return affiliations


def format_db_column(work):
    """
    Colonna DB (Database). Costante: tutti i record prodotti da questo mapper
    provengono dalla sorgente OpenAlex.

    Args:
        work: oggetto "work" OpenAlex grezzo (non usato, presente solo per
            uniformita' di firma con le altre format_XX_column).

    Returns:
        str: sempre "OPENALEX".
    """
    return "OPENALEX"


def format_de_column(work):
    """
    Colonna DE (Author Keywords). Deriva da `work["keywords"][].display_name`
    (i keyword assegnati algoritmicamente da OpenAlex con score di confidenza,
    non keyword scelte dall'autore come in WoS: da segnalare come scostamento
    semantico rispetto al significato originale di DE).

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        list[str]: keyword estratte da `work["keywords"]`, lista vuota se il
        campo e' assente/vuoto o gli elementi non hanno `display_name`.
    """
    keywords = []
    for keyword in work.get("keywords") or []:
        name = keyword.get("display_name")
        if name:
            keywords.append(name)
    return keywords


def format_di_column(work):
    """
    Colonna DI (DOI). Deriva da `work["doi"]`, normalizzato rimuovendo il prefisso
    URL "https://doi.org/" per ottenere il DOI nudo nel formato atteso dallo schema
    WoS-style (es. "10.48550/arxiv.1201.0490").

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: DOI nudo, "" se `work["doi"]` e' assente/None.
    """
    doi = work.get("doi")
    if not doi:
        return ""
    prefix = "https://doi.org/"
    if doi.startswith(prefix):
        return doi[len(prefix):]
    return doi


def format_dt_column(work):
    """
    Colonna DT (Document Type). Deriva da `work["type"]` (vocabolario controllato
    OpenAlex, es. "article", "preprint", "book-chapter"), tradotto nel vocabolario
    WoS-style (es. "Article", "Review") tramite OPENALEX_TYPE_TO_WOS_DT.

    Se `work["type"]` non e' presente in OPENALEX_TYPE_TO_WOS_DT (type nuovo o
    non ancora mappato), il fallback e' il valore OpenAlex originale con la
    prima lettera maiuscola (`str.capitalize()`), invece di una stringa vuota:
    l'informazione grezza resta comunque visibile/utilizzabile a valle anziche'
    andare persa silenziosamente.

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: valore DT mappato, il valore originale capitalizzato se non
        presente in OPENALEX_TYPE_TO_WOS_DT, "" se `work["type"]` e' assente/None.
    """
    work_type = work.get("type")
    if not work_type:
        return ""
    return OPENALEX_TYPE_TO_WOS_DT.get(work_type, work_type.capitalize())


def format_em_column(work):
    """
    Colonna EM (Email). Campo non disponibile da OpenAlex (nessun indirizzo email
    degli autori esposto dall'API): restituisce sempre stringa vuota per decisione
    esplicita, invece di propagare KeyError/AttributeError a valle.

    Args:
        work: oggetto "work" OpenAlex grezzo (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_fu_column(work):
    """
    Colonna FU (Funding Details). Campo non disponibile da OpenAlex per questa
    pipeline: restituisce sempre stringa vuota per decisione esplicita.

    Args:
        work: oggetto "work" OpenAlex grezzo (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_fx_column(work):
    """
    Colonna FX (Funding Text). Campo non disponibile da OpenAlex per questa
    pipeline: restituisce sempre stringa vuota per decisione esplicita.

    Args:
        work: oggetto "work" OpenAlex grezzo (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_is_column(work):
    """
    Colonna IS (Issue). Deriva da `work["biblio"]["issue"]`, con accesso robusto
    ai campi annidati: se `work["biblio"]` e' assente/None, viene trattato come
    dict vuoto invece di sollevare AttributeError/KeyError.

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: numero di fascicolo, "" se assente.
    """
    biblio = work.get("biblio") or {}
    return biblio.get("issue") or ""


def format_ji_column(work):
    """
    Colonna JI (Abbreviated Journal Name). OpenAlex non fornisce
    un'abbreviazione standardizzata del nome rivista: restituisce sempre "".

    Non e' un dato perso: metatagextraction.py::SR (riusata da
    compute_sr_for_records) tratta esplicitamente JI == "" come "nessuna
    abbreviazione disponibile" e ricade sul nome completo della rivista (SO)
    per costruire la colonna SR — esattamente lo stesso pattern gia' usato
    dalla pipeline WoS storica per le sorgenti senza abbreviazione (Dimensions,
    The_Lens, Cochrane in format_functions.py::format_ji_column).

    Args:
        work: oggetto "work" OpenAlex grezzo (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_id_column(work):
    """
    Colonna ID (Index/Keywords Plus). Deriva da `work["concepts"][].display_name`.

    Nota concettuale importante: a differenza di Keywords Plus in WoS (termini
    estratti algoritmicamente dai titoli delle referenze citate da un articolo),
    i "concepts" di OpenAlex sono TOPIC assegnati algoritmicamente al work stesso
    tramite un classificatore proprietario di OpenAlex, organizzati in una
    gerarchia (`level`) con uno score di confidenza. Sono quindi concettualmente
    piu' vicini a una tassonomia/categorizzazione automatica del contenuto che
    non a delle "keyword aggiuntive" nel senso WoS del termine: vanno trattati
    come un'approssimazione, non come un equivalente semantico di ID.

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        list[str]: nomi dei concetti estratti da `work["concepts"]`, lista vuota
        se il campo e' assente/vuoto o gli elementi non hanno `display_name`.
    """
    concepts = []
    for concept in work.get("concepts") or []:
        name = concept.get("display_name")
        if name:
            concepts.append(name)
    return concepts


def format_la_column(work):
    """
    Colonna LA (Language). Pass-through diretto di `work["language"]` (codice
    ISO 639-1, es. "en"), a differenza di WoS dove LA e' tipicamente il nome
    esteso della lingua (es. "English"): da segnalare come possibile scostamento
    di formato se il resto della pipeline (es. filtri o report) si aspetta il
    nome esteso.

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: codice lingua ISO 639-1, "" se `work["language"]` e' assente/None.
    """
    return work.get("language") or ""


def format_oa_column(work):
    """
    Colonna OA (Open Access). Deriva da `work["open_access"]["oa_status"]`
    (vocabolario controllato OpenAlex: "gold", "green", "hybrid", "bronze",
    "closed", ...), pass-through diretto.

    NOTA: implementata qui solo perche' necessaria a map_work_to_record per
    produrre tutte le 33 chiavi richieste (34 colonne meno SR) — senza di essa
    map_work_to_record avrebbe sollevato NotImplementedError su OA. A
    differenza di EM/FU/FX/OI/PU/RP/SC/SN (tutte deliberatamente "sempre
    vuote" per decisione esplicita presa in conversazione), OA NON e' stata
    oggetto della stessa decisione esplicita: va rivista se il formato
    desiderato e' diverso da un semplice pass-through di `oa_status`
    (es. un booleano derivato da `is_oa`, invece della stringa di stato).

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: valore di `oa_status`, "" se `open_access`/`oa_status` sono
        assenti/None.
    """
    open_access = work.get("open_access") or {}
    return open_access.get("oa_status") or ""


def format_oi_column(work):
    """
    Colonna OI (ORCID). Campo non disponibile da OpenAlex per questa pipeline:
    restituisce sempre stringa vuota per decisione esplicita.

    Args:
        work: oggetto "work" OpenAlex grezzo (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_pmid_column(work):
    """
    Colonna PMID (PubMed ID). Deriva da `work["ids"]["pmid"]`, se presente (non
    tutti i work OpenAlex hanno un ID PubMed associato), normalizzato all'ID nudo
    (senza l'eventuale prefisso URL "https://pubmed.ncbi.nlm.nih.gov/").

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: PMID nudo, "" se `work["ids"]["pmid"]` e' assente/None.
    """
    ids = work.get("ids") or {}
    pmid = ids.get("pmid")
    if not pmid:
        return ""
    return pmid.rsplit("/", 1)[-1]


def format_pu_column(work):
    """
    Colonna PU (Publisher). Campo non disponibile da OpenAlex per questa
    pipeline: restituisce sempre stringa vuota per decisione esplicita (pur
    essendo `primary_location.source.host_organization_name` potenzialmente
    disponibile, non viene usato in questa versione della pipeline).

    Args:
        work: oggetto "work" OpenAlex grezzo (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_py_column(work):
    """
    Colonna PY (Publication Year). Deriva da `work["publication_year"]`
    (gia' un int lato OpenAlex).

    BUG DOCUMENTATO E RISOLTO (rilevante per la relazione finale, sezione
    "Weak or inconsistent type enforcement"): questa funzione restituiva in
    origine str(publication_year), classificando PY come STRING in
    type_contracts.py::COLUMN_SPECS. Il ragionamento iniziale era "replicare
    il tipo grezzo della pipeline WoS storica", che infatti restituisce anche
    li' una stringa (format_functions.py::format_py_column). Il problema:
    nella pipeline storica quella stringa diventa int64 "gratis" perche'
    functions/get_data.py costruisce il DataFrame con
    `pd.read_json(StringIO(json))`, che applica inferenza automatica di tipo
    alle stringhe numeriche; la nostra etl_pipeline.py::_build_dataframe usa
    invece `pd.DataFrame(records)` diretto, che non fa questa inferenza — con
    PY=str, functions/get_annualproduction.py andava in TypeError su
    `range(min_year, max_year + 1)` (somma int su stringa).

    Verificato con grep su format_functions.py e su tutte le functions/*.py:
    nessun consumer richiede PY come stringa (nessuno slicing, nessun
    accessor .str, nessuna concatenazione diretta); numerosi consumer lo
    richiedono esplicitamente numerico (min/max, range, confronti aritmetici,
    groupby, np.linspace/pd.cut), e 4 di essi fanno gia' un cast difensivo
    `pd.to_numeric(df['PY'], errors='coerce')` proprio per la stessa ragione
    (get_authorlocalimpact.py, get_authorproductionovertime.py,
    get_sourceslocalimpact.py, get_thematicevolution.py). Corretto qui
    restituendo un int nativo, e classificando PY come INTEGER in
    type_contracts.py::COLUMN_SPECS invece di STRING: il DataFrame prodotto
    da questa pipeline ottiene cosi' lo stesso dtype numerico che la pipeline
    storica ottiene indirettamente tramite il roundtrip JSON.

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        int: anno di pubblicazione, 0 se `work["publication_year"]` e'
        assente/None/non convertibile (stesso default "assenza" usato per TC
        in format_tc_column).
    """
    py = work.get("publication_year")
    if py is None:
        return 0
    try:
        return int(py)
    except (TypeError, ValueError):
        return 0


def format_rp_column(work):
    """
    Colonna RP (Correspondence Address/Reprint Author). Per decisione esplicita,
    restituisce sempre stringa vuota: OpenAlex espone un flag `is_corresponding`
    per autore, ma non un indirizzo di corrispondenza strutturato/affidabile
    equivalente a RP in WoS, quindi si evita di costruire un dato di bassa
    qualita' a partire da quel flag.

    Args:
        work: oggetto "work" OpenAlex grezzo (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_sc_column(work):
    """
    Colonna SC (Subject Category / Fields of Research). Campo non disponibile da
    OpenAlex per questa pipeline: restituisce sempre stringa vuota per decisione
    esplicita (pur essendo `topics[].field.display_name` potenzialmente
    disponibile, non viene usato in questa versione della pipeline).

    Args:
        work: oggetto "work" OpenAlex grezzo (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_sn_column(work):
    """
    Colonna SN (ISSN). Deriva da
    `work["primary_location"]["source"]["issn_l"]`, con accesso robusto ai
    campi annidati: `primary_location` e/o `source` possono essere None per
    interi record (es. preprint su repository senza ISSN, come l'esempio
    arXiv analizzato in conversazione), nel qual caso vengono trattati come
    dict vuoti invece di sollevare AttributeError/KeyError.

    Verificato contro format_functions.py::format_sn_column: SN e' il campo
    ISSN in tutte le sorgenti storiche (WoS, PubMed, Scopus, The_Lens) — questo
    valore era prima erroneamente assegnato a JI (Abbreviated Journal Name),
    corretto qui.

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: ISSN-L della sorgente, "" se `primary_location`/`source`/`issn_l`
        sono assenti/None.
    """
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    return source.get("issn_l") or ""


def format_so_column(work):
    """
    Colonna SO (Journal/Source). Deriva da
    `work["primary_location"]["source"]["display_name"]`, con accesso robusto ai
    campi annidati: `primary_location` e/o `source` possono essere None per
    interi record (es. work senza location primaria), nel qual caso vengono
    trattati come dict vuoti invece di sollevare AttributeError/KeyError.

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: nome della rivista/sorgente, "" se `primary_location` o `source`
        sono assenti/None.
    """
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    return source.get("display_name") or ""


def format_tc_column(work):
    """
    Colonna TC (Times Cited). Deriva da `work["cited_by_count"]`, con cast
    esplicito a int (a differenza di format_tc_column in format_functions.py,
    dove il valore WoS restava una stringa quando presente e un int 0 come
    default, generando un tipo misto nella colonna: qui l'obiettivo e'
    restituire sempre int).

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        int: `cited_by_count` castato a int, 0 se assente/None/non convertibile.
    """
    try:
        return int(work.get("cited_by_count"))
    except (TypeError, ValueError):
        return 0


def format_ti_column(work):
    """
    Colonna TI (Title). Deriva da `work["title"]`, con fallback su
    `work["display_name"]` se `title` e' vuoto/assente (i due campi coincidono
    nella maggior parte dei casi osservati, ma `display_name` e' piu'
    costantemente popolato).

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: titolo del work, "" se sia `title` che `display_name` sono
        assenti/vuoti.
    """
    title = work.get("title")
    if title:
        return title
    return work.get("display_name") or ""


def format_ut_column(work):
    """
    Colonna UT (Publication ID / accession number). Deriva da `work["id"]`
    (URI OpenAlex, es. "https://openalex.org/W2101234009"), da cui viene
    rimosso il prefisso URL per ottenere l'ID nudo (es. "W2101234009").

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: ID OpenAlex nudo, "" se `work["id"]` e' assente/None.
    """
    raw_id = work.get("id")
    if not raw_id:
        return ""
    return raw_id.rsplit("/", 1)[-1]


def format_vl_column(work):
    """
    Colonna VL (Volume). Deriva da `work["biblio"]["volume"]`, con accesso
    robusto ai campi annidati: se `work["biblio"]` e' assente/None, viene
    trattato come dict vuoto invece di sollevare AttributeError/KeyError.

    Args:
        work: oggetto "work" OpenAlex grezzo.

    Returns:
        str: numero di volume, "" se assente.
    """
    biblio = work.get("biblio") or {}
    return biblio.get("volume") or ""


def build_sr_bridge_frame(records):
    """
    Costruisce il DataFrame "ponte" da passare, senza alcuna trasformazione,
    a metatagextraction.py::SR(M).

    Non e' un adattamento in senso stretto: le chiavi dei record prodotti da
    format_au_column/format_db_column/format_ji_column/format_so_column/
    format_py_column in questo stesso modulo si chiamano gia' AU/DB/JI/SO/PY,
    esattamente come le colonne che SR(M) si aspetta. Il "ponte" e' quindi solo
    l'atto di raccogliere piu' record gia' mappati in un unico pandas.DataFrame
    (SR() e' intrinsecamente un'operazione di collezione, non di riga singola:
    vedi il modulo docstring per il perche').

    Args:
        records: list[dict], record gia' prodotti da map_work_to_record (o
            comunque contenenti almeno le chiavi AU, DB, JI, SO, PY nello
            stesso formato prodotto dalle format_XX_column di questo modulo).

    Returns:
        pandas.DataFrame costruito direttamente da records, una riga per record,
        senza rinominare alcuna colonna.
    """
    return pd.DataFrame(records)


def compute_sr_for_records(records):
    """
    Calcola SR (e SR_FULL) per un'intera collezione di record gia' mappati,
    riusando SENZA MODIFICHE metatagextraction.py::SR(M) — la stessa funzione
    gia' usata altrove nella codebase per lo stesso scopo (es. couplingmap.py,
    get_collaborationnetwork.py, entrambe tramite
    `metaTagExtraction(df, "SR")`) — invece di riscrivere a mano la formula
    "Autore, Anno, Rivista" e la sua deduplicazione.

    Questa funzione va chiamata UNA VOLTA sull'intera lista di record (tipicamente
    da etl_pipeline.py::_compute_calculated_fields), MAI record-per-record: SR()
    delega la deduplicazione a `Series.duplicated()`, che e' significativa solo
    se valutata sull'intera collezione. Per questo, a differenza delle altre 34
    colonne, non esiste (e non deve esistere) una format_sr_column(work) a
    livello di singolo record in questo modulo.

    Args:
        records: list[dict], record gia' mappati con almeno le chiavi AU, DB,
            JI, SO, PY (vedi build_sr_bridge_frame).

    Returns:
        list[dict]: nuovi dict (i record in input non vengono mutati), ciascuno
        arricchito con le chiavi "SR" e "SR_FULL" calcolate da
        metatagextraction.py::SR(M) sull'intera collezione. Lista vuota se
        `records` e' vuota (SR() non viene invocata: `M["DB"].iloc[0]` solleverebbe
        IndexError su un DataFrame vuoto).
    """
    if not records:
        return []

    bridge = build_sr_bridge_frame(records)
    bridge = SR(bridge)

    enriched = []
    for original, sr_value, sr_full_value in zip(records, bridge["SR"], bridge["SR_FULL"]):
        record = dict(original)
        record["SR"] = sr_value
        record["SR_FULL"] = sr_full_value
        enriched.append(record)
    return enriched


def _reconstruct_abstract(inverted_index):
    """
    Funzione interna: ricostruisce il testo lineare di un abstract a partire dalla
    struttura "inverted index" di OpenAlex (dict parola -> lista di posizioni),
    riordinando le parole secondo le posizioni indicate.

    Algoritmo: determina la posizione massima presente nell'indice, alloca un
    array di quella dimensione+1 (inizialmente tutto "buchi"), assegna ogni
    parola a ciascuna delle sue posizioni, poi unisce l'array con uno spazio
    scartando i "buchi" rimasti vuoti.

    Robustezza (nessuna eccezione sollevata):
    - inverted_index assente/None/vuoto -> "".
    - posizioni non intere o negative vengono ignorate silenziosamente.
    - posizioni duplicate (due parole diverse rivendicano la stessa posizione,
      anomalia che non dovrebbe verificarsi in un indice invertito valido ma
      viene comunque gestita): vince l'ultima parola incontrata nell'ordine di
      iterazione del dict, senza sollevare errori.
    - "buchi" nelle posizioni (nessuna parola assegnata a una data posizione,
      es. per omissioni nell'indice restituito da OpenAlex): la posizione viene
      semplicemente saltata in fase di join, non riempita con placeholder.

    Usata da format_ab_column.

    Args:
        inverted_index: dict[str, list[int]] | None, tipicamente
            `work["abstract_inverted_index"]`.

    Returns:
        str: testo dell'abstract ricostruito, stringa vuota se inverted_index e'
        None, vuoto, o non contiene alcuna posizione valida.
    """
    if not inverted_index:
        return ""

    max_position = -1
    for positions in inverted_index.values():
        for position in positions or []:
            if isinstance(position, int) and position > max_position:
                max_position = position

    if max_position < 0:
        return ""

    slots = [None] * (max_position + 1)
    for word, positions in inverted_index.items():
        for position in positions or []:
            if isinstance(position, int) and 0 <= position <= max_position:
                slots[position] = word

    return " ".join(word for word in slots if word is not None)

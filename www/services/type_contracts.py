"""
Schema tipizzato delle 34 colonne bibliometrix-style e funzioni di validazione.

Questo modulo e' la fonte di verita' sui tipi attesi per ciascuna colonna prodotta
dalla pipeline ETL. In pratica, oggi, l'unico chiamante pianificato e'
etl_pipeline.py sull'output di openalex_mapper.py::map_work_to_record +
compute_sr_for_records (vedi COLUMN_SPECS piu' sotto per una nota importante
sulla scelta di tipo per EM/FU/OA/OI/SC, dove la pipeline WoS storica in
format_functions.py diverge dal nostro mapper OpenAlex).

Convenzione di tipo:
- campi multi-valore (uno o piu' elementi per pubblicazione) -> list[str]
- campi scalari testuali -> str
- campi scalari numerici -> int

La lista dei nomi di colonna canonici e' gia' definita in www/services/utils.py
(variabile `columns`); questo modulo la arricchisce con l'informazione di tipo
associata a ciascuna colonna, senza duplicarne la definizione.
"""

from .utils import *
from enum import Enum


class ColumnType(Enum):
    """Tipi di dato ammessi per una colonna dello schema a 34 colonne."""
    STRING = "string"
    INTEGER = "integer"
    STRING_LIST = "string_list"


class SchemaValidationError(Exception):
    """Sollevata quando un record o un DataFrame non rispetta lo schema atteso
    (colonna mancante, tipo non coerente, colonna non riconosciuta in modalita' strict).
    Non sollevata direttamente da validate_record/validate_dataframe (che
    riportano errori come lista di stringhe, senza sollevare eccezioni): resta
    disponibile per un chiamante (es. etl_pipeline.py) che voglia trasformare
    una lista di errori di validazione in un'eccezione bloccante."""
    pass


# Specifica dichiarativa per ciascuna delle 34 colonne dello schema bibliometrix-style
# (i nomi devono restare allineati a `columns` in www/services/utils.py).
#
# NOTA su EM, FU, OA, OI, SC: nella pipeline WoS storica (format_functions.py)
# questi campi sono inizializzati come liste (es. `emails = []`, `open_access = []`)
# e possono restare multi-valore per WoS/.txt. Nel nostro mapper OpenAlex
# (openalex_mapper.py) restituiscono invece sempre una stringa scalare (EM/FU/OI/SC
# sono sempre "" per decisione esplicita; OA e' un pass-through scalare di
# `oa_status`). Decisione presa in conversazione: qui sono classificati STRING,
# allineati a cio' che produce davvero openalex_mapper.py (l'unico chiamante
# attuale di questo modulo). Se in futuro type_contracts.py dovesse validare
# anche l'output della pipeline WoS storica, questa scelta andra' rivista
# insieme a format_functions.py, non silenziosamente.
#
# "required" qui significa "la chiave deve essere presente nel record" — non
# "il valore non puo' essere vuoto": "" / [] / 0 sono rappresentazioni valide
# di "nessun dato", None/NaN non lo sono mai.
#
# BUG DOCUMENTATO E RISOLTO (rilevante per la relazione finale, sezione "Weak
# or inconsistent type enforcement"): PY era inizialmente classificato STRING
# perche' openalex_mapper.py::format_py_column restituiva str(publication_year).
# Questo replicava il tipo GREZZO prodotto dalla pipeline WoS storica
# (format_functions.py::format_py_column restituisce anch'essa una stringa),
# ma non replicava il suo effetto pratico: get_data.py costruisce il
# DataFrame storico con `pd.read_json(StringIO(json))`, che converte
# automaticamente le stringhe numeriche in int64, mentre
# etl_pipeline.py::_build_dataframe usa `pd.DataFrame(records)` diretto, che
# NON fa questa inferenza — quindi PY restava str a valle SOLO nella nostra
# pipeline, mai in quella storica. Il sintomo: functions/get_annualproduction.py
# andava in TypeError su `range(min_year, max_year + 1)` perche' min_year/
# max_year erano stringhe. Verificato con grep su format_functions.py e su
# tutte le functions/*.py che nessun consumer richiede PY come stringa (nessuno
# slicing, nessun accessor .str, nessuna concatenazione); numerosi consumer lo
# richiedono esplicitamente numerico (min/max, range, confronti aritmetici,
# groupby, np.linspace/pd.cut), e 4 di essi (get_authorlocalimpact.py,
# get_authorproductionovertime.py, get_sourceslocalimpact.py,
# get_thematicevolution.py) fanno gia' un cast difensivo
# `pd.to_numeric(..., errors="coerce")` proprio per questo motivo. Risolto
# classificando PY come INTEGER qui e facendo restituire un int nativo da
# format_py_column (vedi openalex_mapper.py per il dettaglio completo).
COLUMN_SPECS: dict = {
    "AB":     {"type": ColumnType.STRING,      "required": True, "description": "Abstract"},
    "AF":     {"type": ColumnType.STRING_LIST, "required": True, "description": "Authors Full Name"},
    "AU":     {"type": ColumnType.STRING_LIST, "required": True, "description": "Authors"},
    "AU1_UN": {"type": ColumnType.STRING,      "required": True, "description": "First Author University"},
    "AU_UN":  {"type": ColumnType.STRING_LIST, "required": True, "description": "Authors University"},
    "BP":     {"type": ColumnType.STRING,      "required": True, "description": "Begin Page"},
    "C1":     {"type": ColumnType.STRING_LIST, "required": True, "description": "Authors Affiliations"},
    "CR":     {"type": ColumnType.STRING_LIST, "required": True, "description": "Cited References"},
    "DB":     {"type": ColumnType.STRING,      "required": True, "description": "Source"},
    "DE":     {"type": ColumnType.STRING_LIST, "required": True, "description": "Keywords"},
    "DI":     {"type": ColumnType.STRING,      "required": True, "description": "DOI"},
    "DT":     {"type": ColumnType.STRING,      "required": True, "description": "Document Type"},
    "EM":     {"type": ColumnType.STRING,      "required": True, "description": "Author Email"},
    "EP":     {"type": ColumnType.STRING,      "required": True, "description": "End Page"},
    "FU":     {"type": ColumnType.STRING,      "required": True, "description": "Funding Details"},
    "FX":     {"type": ColumnType.STRING,      "required": True, "description": "Acknowledgements"},
    "ID":     {"type": ColumnType.STRING_LIST, "required": True, "description": "Index Keywords"},
    "IS":     {"type": ColumnType.STRING,      "required": True, "description": "Issue"},
    "JI":     {"type": ColumnType.STRING,      "required": True, "description": "Abbreviated Source Title"},
    "LA":     {"type": ColumnType.STRING,      "required": True, "description": "Language"},
    "OA":     {"type": ColumnType.STRING,      "required": True, "description": "Open Access"},
    "OI":     {"type": ColumnType.STRING,      "required": True, "description": "Author's ORCID"},
    "PMID":   {"type": ColumnType.STRING,      "required": True, "description": "PubMed ID"},
    "PU":     {"type": ColumnType.STRING,      "required": True, "description": "Publisher"},
    "PY":     {"type": ColumnType.INTEGER,     "required": True, "description": "Publication Year"},
    "RP":     {"type": ColumnType.STRING,      "required": True, "description": "Correspondence Address"},
    "SC":     {"type": ColumnType.STRING,      "required": True, "description": "Fields of Study"},
    "SN":     {"type": ColumnType.STRING,      "required": True, "description": "ISSN"},
    "SO":     {"type": ColumnType.STRING,      "required": True, "description": "Journal"},
    "SR":     {"type": ColumnType.STRING,      "required": True, "description": "Authors, Publication Year and Journal"},
    "TC":     {"type": ColumnType.INTEGER,     "required": True, "description": "Time Cited"},
    "TI":     {"type": ColumnType.STRING,      "required": True, "description": "Title"},
    "UT":     {"type": ColumnType.STRING,      "required": True, "description": "Publication ID"},
    "VL":     {"type": ColumnType.STRING,      "required": True, "description": "Volume"},
}


def get_expected_type(column):
    """
    Restituisce il ColumnType atteso per una colonna dello schema a 34 colonne.

    Args:
        column: nome della colonna (es. "AU", "PY", "TC").

    Returns:
        ColumnType corrispondente, secondo COLUMN_SPECS.

    Raises:
        KeyError: se la colonna non fa parte dello schema definito in COLUMN_SPECS.
    """
    if column not in COLUMN_SPECS:
        raise KeyError(f"Colonna non presente nello schema COLUMN_SPECS: {column!r}")
    return COLUMN_SPECS[column]["type"]


def is_multivalue(column):
    """
    Indica se una colonna e' definita come multi-valore (list[str], es. AU, C1, CR,
    DE, ID) oppure scalare (str/int, es. PY, TC, TI, SO).

    Args:
        column: nome della colonna.

    Returns:
        bool.

    Raises:
        KeyError: se la colonna non fa parte dello schema definito in COLUMN_SPECS
            (propagata da get_expected_type).
    """
    return get_expected_type(column) == ColumnType.STRING_LIST


def _is_missing_scalar(value):
    """
    Funzione interna: indica se un valore scalare va considerato "mancante" nel
    senso proibito dal contratto (None, o NaN in stile pandas/numpy).

    Una stringa vuota "" o una lista vuota [] NON sono considerate mancanti:
    sono le rappresentazioni valide di "nessun dato" gia' stabilite nel design
    di openalex_mapper.py. Non tenta di valutare la "vacuita'" di list/dict/
    tuple/set (per cui il concetto di NaN non ha senso): restituisce False per
    quei tipi senza sollevare eccezioni.

    Args:
        value: valore da controllare.

    Returns:
        bool: True se value e' None o NaN, False altrimenti (incluse liste/dict
        di qualunque contenuto).
    """
    if isinstance(value, (list, dict, tuple, set)):
        return False
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def coerce_record_types(record):
    """
    Tenta una coercizione "best-effort" dei valori di un record verso i tipi
    dichiarati in COLUMN_SPECS, permissiva in input ma con output SEMPRE
    conforme allo schema (barriera finale anti-NaN/None richiesta dal design):

    - colonna STRING_LIST: None/NaN -> []; list/tuple gia' presente -> list();
      qualunque altro scalare (es. una singola stringa) -> wrappato in lista
      di un elemento.
    - colonna INTEGER: None/NaN -> 0; altrimenti tentativo di `int(value)`
      (funziona anche su stringhe numeriche come "42" o float come 42.0);
      se la conversione fallisce (es. stringa non numerica), fallback a 0
      invece di sollevare un'eccezione.
    - colonna STRING: None/NaN -> ""; stringa gia' presente -> invariata;
      qualunque altro valore (int, float, list residua, ecc.) -> convertito
      con `str(value)`.

    Il record restituito contiene ESATTAMENTE le chiavi di COLUMN_SPECS (quindi
    di `columns` in utils.py): colonne mancanti nell'input vengono aggiunte con
    il default vuoto del loro tipo, colonne extra presenti nell'input ma non
    nello schema vengono scartate. Questo rende la funzione una barriera
    robusta anche contro record parziali o con chiavi sporche, non solo contro
    valori None/NaN sui campi attesi.

    Args:
        record: dict rappresentante una singola riga/pubblicazione. Puo' essere
            parziale, avere chiavi extra, o contenere None/NaN/tipi sbagliati:
            nessuno di questi casi solleva un'eccezione.

    Returns:
        dict: nuovo record con esattamente le chiavi di COLUMN_SPECS, ciascuna
        con un valore del tipo python atteso.
    """
    coerced = {}

    for column, spec in COLUMN_SPECS.items():
        value = record.get(column) if isinstance(record, dict) else None
        expected_type = spec["type"]

        if expected_type == ColumnType.STRING_LIST:
            if _is_missing_scalar(value):
                coerced_value = []
            elif isinstance(value, list):
                coerced_value = value
            elif isinstance(value, tuple):
                coerced_value = list(value)
            else:
                coerced_value = [value]

        elif expected_type == ColumnType.INTEGER:
            if _is_missing_scalar(value):
                coerced_value = 0
            else:
                try:
                    coerced_value = int(value)
                except (TypeError, ValueError):
                    coerced_value = 0

        else:  # ColumnType.STRING
            if _is_missing_scalar(value):
                coerced_value = ""
            elif isinstance(value, str):
                coerced_value = value
            else:
                coerced_value = str(value)

        coerced[column] = coerced_value

    return coerced


def validate_record(record, strict=True):
    """
    Valida un singolo record (dict colonna -> valore) contro COLUMN_SPECS,
    SENZA correggerlo (a differenza di coerce_record_types): riporta soltanto
    gli errori trovati.

    Verifica, per ogni colonna prevista dallo schema:
    - presenza della chiave, se il campo e' marcato come obbligatorio;
    - assenza di valori None/NaN residui (distinti da "" / [] / 0, che sono
      rappresentazioni valide di "nessun dato");
    - coerenza del tipo python del valore con quanto dichiarato in COLUMN_SPECS
      (list per i campi multi-valore, str per gli scalari testuali, int
      — esplicitamente NON bool — per gli scalari numerici);
    - assenza di colonne non riconosciute, se strict=True.

    Args:
        record: dict rappresentante una singola riga/pubblicazione, con chiavi
            attese tra le 34 colonne dello schema.
        strict: se True, chiavi extra non presenti in COLUMN_SPECS sono considerate
            un errore di validazione; se False, vengono ignorate.

    Returns:
        list[str]: messaggi di errore (lista vuota se il record e' valido). Non
        solleva eccezioni: un input non-dict produce un singolo messaggio di
        errore descrittivo invece di un TypeError.
    """
    if not isinstance(record, dict):
        return [f"record non è un dict: {type(record).__name__}"]

    errors = []

    for column, spec in COLUMN_SPECS.items():
        if column not in record:
            if spec["required"]:
                errors.append(f"{column}: colonna obbligatoria mancante")
            continue

        value = record[column]
        expected_type = spec["type"]

        if expected_type == ColumnType.STRING_LIST:
            if not isinstance(value, list):
                errors.append(
                    f"{column}: atteso list (STRING_LIST), trovato {type(value).__name__} ({value!r})"
                )

        elif expected_type == ColumnType.INTEGER:
            if _is_missing_scalar(value):
                errors.append(f"{column}: valore mancante (None/NaN) su colonna INTEGER")
            elif not isinstance(value, int) or isinstance(value, bool):
                errors.append(
                    f"{column}: atteso int (INTEGER), trovato {type(value).__name__} ({value!r})"
                )

        else:  # ColumnType.STRING
            if _is_missing_scalar(value):
                errors.append(f"{column}: valore mancante (None/NaN) su colonna STRING")
            elif not isinstance(value, str):
                errors.append(
                    f"{column}: atteso str (STRING), trovato {type(value).__name__} ({value!r})"
                )

    if strict:
        extra = set(record.keys()) - set(COLUMN_SPECS.keys())
        if extra:
            errors.append(f"colonne non riconosciute nello schema: {sorted(extra)}")

    return errors


def validate_dataframe(df, strict=True):
    """
    Valida un intero pandas.DataFrame contro COLUMN_SPECS, applicando
    validate_record ad ogni riga e aggregando gli errori con riferimento
    all'indice di riga originale del DataFrame (non alla posizione 0-based).

    Args:
        df: pandas.DataFrame da validare, atteso con lo schema a 34 colonne
            (o un suo sottoinsieme).
        strict: vedi validate_record.

    Returns:
        list[str]: messaggi di errore, prefissati con "riga <indice>: ..."
        (lista vuota se il DataFrame e' valido). Un DataFrame vuoto (0 righe)
        restituisce una lista vuota senza errori.
    """
    errors = []
    for row_index, record in zip(df.index, df.to_dict(orient="records")):
        for error in validate_record(record, strict=strict):
            errors.append(f"riga {row_index}: {error}")
    return errors

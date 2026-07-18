"""
Entry-point unico per la pipeline ETL "query utente -> OpenAlex -> schema WoS-style".

Orchestra, in ordine:
1. query utente -> openalex_client (ricerca + paginazione cursor-based, con
   risoluzione opzionale in batch degli ID in `referenced_works`)
2. openalex_client -> openalex_mapper (mapping di ciascun "work" grezzo sulle
   34 colonne dello schema bibliometrix-style)
3. calcolo dei campi derivati che richiedono l'intera collezione (es. SR, che deve
   deduplicare le sigle "Autore, Anno, Rivista" ripetute nel dataset, con la stessa
   logica concettuale di metatagextraction.py::SR)
4. type_contracts (coercizione e validazione dei tipi prima di finalizzare l'output)
5. assemblaggio del pandas.DataFrame finale, con lo stesso schema a 34 colonne
   prodotto dalla pipeline storica basata su file (vedi
   www/services/format_functions.py::process_single_file).

Questo modulo e' pensato come punto di ingresso alternativo a
functions/get_data.py (che copre l'import da file WoS/Scopus/ecc.), cosi' che il
resto della codebase (le funzioni in functions/get_*.py, che operano sul
DataFrame condiviso `df`) possa continuare a funzionare senza sapere se i dati
provengono da un file caricato dall'utente o da una query OpenAlex.
"""

from .utils import *
from .openalex_client import *
from .openalex_mapper import *
from .type_contracts import *


class ETLPipelineError(Exception):
    """Sollevata quando la pipeline ETL fallisce in uno dei suoi stadi (fetch,
    risoluzione referenze, mapping, validazione) in un modo che non permette di
    produrre un DataFrame utilizzabile."""
    pass


def run_openalex_etl(
    query,
    filters=None,
    mailto=None,
    max_results=None,
    resolve_references=True,
    strict_validation=True,
):
    """
    Entry-point principale: esegue l'intera pipeline ETL da una query utente
    OpenAlex a un pandas.DataFrame nello schema a 34 colonne WoS-style.

    Args:
        query: stringa di ricerca testuale libera, inoltrata a
            openalex_client.search_works.
        filters: dict opzionale di filtri OpenAlex aggiuntivi (es. anno, tipo
            documento), vedi openalex_client.search_works.
        mailto: email da usare per la polite pool di OpenAlex.
        max_results: numero massimo di record da scaricare; None per scaricare
            tutti i risultati della query.
        resolve_references: se True, risolve in batch gli ID in `referenced_works`
            per popolare la colonna CR con citazioni leggibili invece dei soli ID
            OpenAlex (costo aggiuntivo in chiamate HTTP, vedi
            openalex_client.get_works_by_ids).
        strict_validation: passato come `strict` a type_contracts.validate_record
            per ogni record dopo la coercizione dei tipi: se True (default),
            eventuali colonne non riconosciute nello schema canonico contano come
            errori di validazione; se False, vengono tollerate. In ENTRAMBI i
            casi, qualunque altro errore residuo (tipo non conforme, colonna
            obbligatoria mancante, None/NaN sopravvissuto alla coercizione) fa
            comunque sollevare ETLPipelineError da _validate_records: e' una rete
            di sicurezza interna che non dovrebbe mai scattare in condizioni
            normali (map_work_to_record + coerce_record_types garantiscono gia'
            record conformi), non un comportamento disattivabile con questo flag.

    Returns:
        Tupla (df, validation_errors):
        - df: pandas.DataFrame con lo schema a 34 colonne bibliometrix-style,
          colonne nell'ordine di `columns` (www/services/utils.py).
        - validation_errors: list[str], sempre [] nel percorso di successo
          (qualunque errore di validazione residuo interrompe la pipeline con
          ETLPipelineError prima di raggiungere il return — vedi
          _validate_records). Il secondo elemento della tupla e' mantenuto per
          stabilita' della firma pubblica, per il caso in cui in futuro
          _validate_records venga reso tollerante invece che bloccante.

    Raises:
        ETLPipelineError: se uno stadio non recuperabile della pipeline fallisce
            (nessun risultato dalla query, errore HTTP non gestito dal client,
            oppure errori di validazione residui dopo la coercizione dei tipi).
    """
    works = _fetch_raw_works(query, filters, mailto, max_results)

    resolved_references = None
    if resolve_references:
        resolved_references = _resolve_references_for_works(works, mailto)

    records = _map_works_to_records(works, resolved_references=resolved_references)
    records = _compute_calculated_fields(records)

    coerced_records, _ = _validate_records(records, strict=strict_validation)

    df = _build_dataframe(coerced_records)

    return df, []


def _fetch_raw_works(query, filters, mailto, max_results):
    """
    Stadio 1: recupera dalla API OpenAlex la lista grezza di oggetti "work" (dict
    JSON) corrispondenti alla query utente, delegando a
    openalex_client.search_works (che gia' pagina internamente con cursore fino
    a max_results o esaurimento dei risultati).

    Args:
        query, filters, mailto, max_results: vedi run_openalex_etl.

    Returns:
        list[dict]: oggetti "work" OpenAlex grezzi.

    Raises:
        ETLPipelineError: se la query non produce alcun risultato, oppure se
            openalex_client.search_works solleva OpenAlexRequestError (errore
            HTTP non recuperabile dopo i retry).
    """
    try:
        works = search_works(query, max_results=max_results, filters=filters, mailto=mailto)
    except OpenAlexRequestError as exc:
        raise ETLPipelineError(
            f"Recupero dei work da OpenAlex fallito per la query {query!r}: {exc}"
        ) from exc

    if not works:
        raise ETLPipelineError(f"Nessun risultato OpenAlex per la query {query!r}.")

    return works


def _resolve_references_for_works(works, mailto):
    """
    Stadio 2 (opzionale): raccoglie l'unione di tutti gli ID presenti nel campo
    `referenced_works` dei work scaricati e li risolve in batch tramite
    openalex_client.get_works_by_ids, per costruire citazioni leggibili per la
    colonna CR invece dei soli ID.

    Deduplica a livello di INTERA collezione (non per singolo work) e chiama
    get_works_by_ids UNA SOLA VOLTA sull'unione di tutti gli ID: get_works_by_ids
    spezza gia' internamente in chunk da 50 (il suo DEFAULT_BATCH_SIZE), quindi
    minimizzare qui il numero di chiamate a get_works_by_ids stessa (una sola,
    con l'intera lista) minimizza a cascata il numero di richieste HTTP totali
    rispetto a chiamarla una volta per work.

    Ogni referenced_works di un singolo work viene troncato a
    openalex_mapper.MAX_REFERENCED_WORKS PRIMA di entrare nell'unione: sono gli
    stessi ID che format_cr_column considerera' comunque (lo stesso cap), quindi
    risolvere ID oltre quel limite sarebbe lavoro sprecato.

    Args:
        works: list[dict] di work OpenAlex grezzi, vedi _fetch_raw_works.
        mailto: email per la polite pool.

    Returns:
        dict[str, dict]: mappa da ID OpenAlex a oggetto "work" risolto, passata a
        openalex_mapper.map_work_to_record / format_cr_column. Dizionario vuoto
        se nessun work ha referenced_works.
    """
    seen = set()
    all_ids = []
    for work in works:
        referenced = (work.get("referenced_works") or [])[:MAX_REFERENCED_WORKS]
        for ref_id in referenced:
            if ref_id and ref_id not in seen:
                seen.add(ref_id)
                all_ids.append(ref_id)

    if not all_ids:
        return {}

    return get_works_by_ids(all_ids, mailto=mailto)


def _map_works_to_records(works, resolved_references=None):
    """
    Stadio 3: applica openalex_mapper.map_work_to_record a ciascun work grezzo,
    producendo la lista di record (dict) nello schema a 34 colonne WoS-style
    (esclusi i campi calcolati a livello di collezione come SR).

    Args:
        works: list[dict] di work OpenAlex grezzi.
        resolved_references: dict opzionale id -> work risolto, vedi
            _resolve_references_for_works; None se resolve_references=False in
            run_openalex_etl (CR contera' presumibilmente solo gli ID grezzi).

    Returns:
        list[dict]: un record per work, con le chiavi delle 34 colonne (tranne i
        campi calcolati a livello di collezione).
    """
    return [
        map_work_to_record(work, resolved_references=resolved_references)
        for work in works
    ]


def _compute_calculated_fields(records):
    """
    Stadio 4: calcola i campi derivati dall'intera collezione, in particolare SR
    (Autore, Anno, Rivista), che richiede la deduplicazione tra tutti i record del
    dataset (stessa logica concettuale di metatagextraction.py::SR, adattata per
    operare su una lista di record invece che su un DataFrame reattivo wrappato da
    `df.get()`/`df.set()`).

    Args:
        records: list[dict] prodotta da _map_works_to_records.

    Returns:
        list[dict]: nuovi record (gli originali non vengono mutati, vedi
        compute_sr_for_records), arricchiti con la chiave "SR". Nota: la
        funzione riusata, openalex_mapper.compute_sr_for_records, aggiunge
        anche "SR_FULL" (sottoprodotto di metatagextraction.py::SR, riusata
        invariata) — SR_FULL viene deliberatamente SCARTATA qui perche' non fa
        parte dello schema canonico a 34 colonne (`columns` in utils.py):
        decisione presa esplicitamente dopo averlo verificato con
        type_contracts.validate_record durante lo sviluppo di questo modulo.
    """
    enriched = compute_sr_for_records(records)
    for record in enriched:
        record.pop("SR_FULL", None)
    return enriched


def _validate_records(records, strict=True):
    """
    Stadi 5+6: prima coercizione (type_contracts.coerce_record_types su ogni
    record, per assorbire inconsistenze di tipo note es. TC/PY come stringa),
    poi validazione (type_contracts.validate_record sui record gia' coerciti).

    Se, DOPO la coercizione, restano errori di validazione, solleva
    ETLPipelineError con il dettaglio invece di restituirli: coerce_record_types
    e' pensata per garantire sempre output conforme, quindi un errore residuo a
    questo punto significa una regressione nella pipeline stessa (es. un
    format_XX_column che ha smesso di rispettare il proprio contratto di tipo),
    non un problema recuperabile sui dati di un singolo work — e' la "rete di
    sicurezza finale" del brief, non un controllo disattivabile.

    Args:
        records: list[dict] da validare, dopo il calcolo dei campi derivati
            (vedi _compute_calculated_fields).
        strict: propagato a type_contracts.validate_record; se True, record con
            colonne non riconosciute sono considerati invalidi.

    Returns:
        Tupla (coerced_records, errors):
        - coerced_records: list[dict] con i valori coerciti da
          type_contracts.coerce_record_types.
        - errors: list[str], SEMPRE [] quando la funzione ritorna normalmente
          (qualunque errore residuo fa sollevare ETLPipelineError prima del
          return). Mantenuta nella firma per stabilita' dell'API.

    Raises:
        ETLPipelineError: se validate_record rileva almeno un errore su almeno
            un record dopo la coercizione.
    """
    coerced_records = [coerce_record_types(record) for record in records]

    errors = []
    for index, record in enumerate(coerced_records):
        for error in validate_record(record, strict=strict):
            errors.append(f"record {index}: {error}")

    if errors:
        raise ETLPipelineError(
            "Validazione fallita su record gia' coerciti (non dovrebbe accadere): "
            + "; ".join(errors)
        )

    return coerced_records, errors


def _build_dataframe(records):
    """
    Stadio 6: assembla il pandas.DataFrame finale a partire dalla lista di record
    validati, garantendo che le colonne siano nello stesso ordine dello schema a
    34 colonne definito in www/services/utils.py (variabile `columns`), per
    compatibilita' con le funzioni esistenti in functions/get_*.py che assumono
    questo schema.

    Args:
        records: list[dict] di record coerciti/validati.

    Returns:
        pandas.DataFrame con lo schema a 34 colonne WoS-style, colonne ordinate
        secondo `columns` (www/services/utils.py). Con records=[] restituisce un
        DataFrame a 0 righe ma con tutte le 34 colonne comunque definite.
    """
    df = pd.DataFrame(records)
    df = df.reindex(columns=columns)
    return df

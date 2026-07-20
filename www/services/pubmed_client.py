"""
Client HTTP per le E-utilities di PubMed/NCBI (https://eutils.ncbi.nlm.nih.gov).

Responsabilita' di questo modulo:
- Cercare PMID che corrispondono a una query testuale (ESearch, JSON).
- Recuperare i record completi corrispondenti a una lista di PMID (EFetch, XML).
- Applicare retry con backoff esponenziale sugli errori transitori, riusando
  la stessa logica gia' validata su OpenAlex (vedi http_client.py).

A differenza di OpenAlex, PubMed non espone un endpoint singolo che restituisce
gia' i record completi per una query testuale: servono due chiamate in
sequenza, ESearch (query -> lista di ID) ed EFetch (lista di ID -> XML
completo). search_articles() incapsula questa sequenza in un'unica funzione,
cosi' da esporre a etl_pipeline.py un contratto identico a quello di
openalex_client.search_works(): una query in ingresso, una lista di record
grezzi pronti per il mapping in uscita.

A differenza di OpenAlex, il testo dei riferimenti bibliografici (quando
presente) e' gia' incluso nel payload di EFetch (ReferenceList/Reference/
Citation): non serve alcuna risoluzione batch equivalente a
openalex_client.get_works_by_ids, quindi questo modulo non ha una funzione
corrispondente.

Questo modulo non fa alcun mapping verso lo schema WoS-style: restituisce
sempre elementi XML grezzi (xml.etree.ElementTree.Element, un nodo
<PubmedArticle> per articolo) cosi' come li restituisce PubMed. Il mapping
verso le 34 colonne e' responsabilita' di pubmed_mapper.py; l'orchestrazione
dei due e' responsabilita' di etl_pipeline.py.
"""

import logging
import xml.etree.ElementTree as ET

from .utils import *
from .http_client import ExternalAPIRequestError, request_with_retry


logger = logging.getLogger(__name__)


BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ESEARCH_ENDPOINT = f"{BASE_URL}/esearch.fcgi"
EFETCH_ENDPOINT = f"{BASE_URL}/efetch.fcgi"

# Limite massimo di PMID per singola chiamata EFetch via GET. Le E-utilities
# accettano batch piu' grandi via POST (fino a 10000 con usehistory), ma
# questa pipeline non ha bisogno di quel volume (stesso ordine di grandezza
# di risultati richiesto lato OpenAlex) - GET con batch moderati e' piu'
# semplice e sufficiente.
DEFAULT_BATCH_SIZE = 200

# Risultati per singola chiamata ESearch. NCBI consente retmax fino a 10000
# per chiamata; qui restiamo bassi e usiamo retstart per paginare, con lo
# stesso pattern di budget di tempo gia' validato su search_works.
DEFAULT_RETMAX = 200

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 1.5
# Stessa tupla (connect, read) e stessa motivazione documentata in
# openalex_client.py::DEFAULT_TIMEOUT: un timeout singolo non copre il tempo
# totale della richiesta, solo l'inattivita' tra un chunk e il successivo.
DEFAULT_TIMEOUT = (5, 15)

DEFAULT_FETCH_TIMEOUT_SECONDS = 30


class PubMedRequestError(ExternalAPIRequestError):
    """Sollevata quando una richiesta a PubMed E-utilities fallisce in modo non
    recuperabile (status 4xx diverso da 429, oppure 5xx/timeout dopo
    l'esaurimento dei retry). Sottoclasse di ExternalAPIRequestError, stesso
    ruolo di OpenAlexRequestError per la sorgente OpenAlex: un chiamante che
    vuole gestire "qualunque fonte esterna fallita" allo stesso modo puo'
    intercettare la classe base invece di questa."""
    pass


def search_articles(query, max_results=None, email=None, api_key=None,
                     retmax=DEFAULT_RETMAX, fetch_timeout_seconds=DEFAULT_FETCH_TIMEOUT_SECONDS,
                     start_time=None):
    """
    Esegue una ricerca testuale completa su PubMed: prima ESearch (query ->
    lista di PMID, paginata con retstart finche' tutti i risultati non sono
    stati raccolti o max_results e' stato raggiunto), poi EFetch a batch
    (lista di PMID -> XML completo) per recuperare i record.

    Stesso limite di sicurezza di openalex_client.search_works: se
    `fetch_timeout_seconds` non e' None, PRIMA di ogni nuova richiesta
    (ESearch o EFetch) si controlla il tempo trascorso da `start_time`; se il
    budget e' superato, la raccolta si interrompe restituendo i risultati
    gia' ottenuti fino a quel momento invece di continuare indefinitamente.

    Args:
        query: stringa di ricerca libera, mappata sul parametro `term` di
            ESearch (supporta i tag di campo nativi di PubMed, es.
            "diabetes[Title]", ma qui viene passata cosi' com'e').
        max_results: numero massimo di articoli da raccogliere
            complessivamente; None per scaricare tutti i risultati della
            query (attenzione: puo' comportare molte richieste HTTP su query
            con molti match).
        email: email da passare come parametro `email` (raccomandato da NCBI
            per identificare il chiamante, analogo a `mailto` su OpenAlex).
        api_key: chiave API NCBI opzionale, passata come parametro `api_key`
            (alza il rate limit da 3 a 10 richieste/secondo).
        retmax: risultati per chiamata ESearch (default DEFAULT_RETMAX).
        fetch_timeout_seconds: budget di tempo (secondi) per l'INTERA
            raccolta (ESearch + tutte le EFetch), non per singola richiesta.
            None per nessun limite.
        start_time: istante di riferimento (da time.monotonic()); se None, si
            usa l'istante di ingresso in questa funzione.

    Returns:
        list[xml.etree.ElementTree.Element]: un nodo <PubmedArticle> per
        articolo trovato, nell'ordine restituito da PubMed, troncati a
        max_results se specificato.

    Raises:
        PubMedRequestError: se una richiesta ESearch o EFetch fallisce in
            modo non recuperabile (propagata da _request_with_retry).
    """
    if max_results is not None and max_results <= 0:
        return []

    if start_time is None:
        start_time = time.monotonic()

    pmids = _search_pmids(
        query, max_results=max_results, email=email, api_key=api_key,
        retmax=retmax, fetch_timeout_seconds=fetch_timeout_seconds, start_time=start_time,
    )
    if not pmids:
        return []

    return fetch_articles(
        pmids, email=email, api_key=api_key,
        fetch_timeout_seconds=fetch_timeout_seconds, start_time=start_time,
    )


def _search_pmids(query, max_results=None, email=None, api_key=None, retmax=DEFAULT_RETMAX,
                   fetch_timeout_seconds=DEFAULT_FETCH_TIMEOUT_SECONDS, start_time=None):
    """
    Funzione interna: esegue ESearch paginando con retstart finche' PubMed non
    ha esaurito i risultati oppure e' stato raccolto max_results PMID.

    Returns:
        list[str]: PMID trovati, come stringhe, nell'ordine restituito da
        PubMed.
    """
    if start_time is None:
        start_time = time.monotonic()

    pmids = []
    retstart = 0

    while True:
        if fetch_timeout_seconds is not None and (time.monotonic() - start_time) > fetch_timeout_seconds:
            logger.warning(
                "_search_pmids: budget di %.1fs esaurito, interrotta la ricerca dopo %d PMID raccolti",
                fetch_timeout_seconds, len(pmids),
            )
            break

        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": retmax,
            "retstart": retstart,
        }
        if email:
            params["email"] = email
        if api_key:
            params["api_key"] = api_key

        response = _request_with_retry(ESEARCH_ENDPOINT, params)
        payload = response.json()

        result = payload.get("esearchresult", {})
        page_ids = result.get("idlist", [])
        if not page_ids:
            break

        pmids.extend(page_ids)

        if max_results is not None and len(pmids) >= max_results:
            pmids = pmids[:max_results]
            break

        total_count = int(result.get("count", 0))
        retstart += len(page_ids)
        if retstart >= total_count:
            break

    return pmids


def fetch_articles(pmids, email=None, api_key=None, batch_size=DEFAULT_BATCH_SIZE,
                    fetch_timeout_seconds=DEFAULT_FETCH_TIMEOUT_SECONDS, start_time=None):
    """
    Recupera i record XML completi per una lista di PMID, tramite EFetch a
    batch (fino a batch_size PMID per chiamata).

    Un batch che fallisce in modo persistente (dopo tutti i retry di
    _request_with_retry) NON interrompe il recupero degli altri batch:
    l'errore viene loggato e i PMID di quel batch restano semplicemente
    assenti dalla lista restituita - stesso comportamento di
    openalex_client.get_works_by_ids sui batch falliti.

    Args:
        pmids: lista di PMID (stringhe o interi) da recuperare. Duplicati
            vengono deduplicati preservando il primo ordine di apparizione.
        email: email da passare come parametro `email`.
        api_key: chiave API NCBI opzionale.
        batch_size: numero massimo di PMID per chiamata EFetch.
        fetch_timeout_seconds: budget di tempo (secondi) per l'INTERO
            recupero, non per singolo batch. None per nessun limite.
        start_time: istante di riferimento (da time.monotonic()); se None, si
            usa l'istante di ingresso in questa funzione.

    Returns:
        list[xml.etree.ElementTree.Element]: un nodo <PubmedArticle> per
        articolo recuperato con successo. I PMID non risolvibili (batch
        fallito dopo i retry, oppure mai raggiunti per esaurimento del budget
        di tempo) sono semplicemente assenti dal risultato.
    """
    seen = set()
    deduped_pmids = []
    for pmid in pmids:
        pmid_str = str(pmid)
        if pmid_str and pmid_str not in seen:
            seen.add(pmid_str)
            deduped_pmids.append(pmid_str)

    if start_time is None:
        start_time = time.monotonic()

    articles = []
    for batch_start in range(0, len(deduped_pmids), batch_size):
        if fetch_timeout_seconds is not None and (time.monotonic() - start_time) > fetch_timeout_seconds:
            logger.warning(
                "fetch_articles: budget di %.1fs esaurito, interrotto dopo %d/%d PMID recuperati",
                fetch_timeout_seconds, len(articles), len(deduped_pmids),
            )
            break

        batch = deduped_pmids[batch_start:batch_start + batch_size]
        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "rettype": "abstract",
            "retmode": "xml",
        }
        if email:
            params["email"] = email
        if api_key:
            params["api_key"] = api_key

        try:
            response = _request_with_retry(EFETCH_ENDPOINT, params)
        except PubMedRequestError as exc:
            logger.error(
                "fetch_articles: batch di %d PMID fallito dopo i retry (primi PMID: %s): %s",
                len(batch), batch[:3], exc,
            )
            continue

        root = ET.fromstring(response.content)
        articles.extend(root.findall("PubmedArticle"))

    return articles


def _request_with_retry(url, params, max_retries=DEFAULT_MAX_RETRIES, backoff_factor=DEFAULT_BACKOFF_FACTOR, timeout=DEFAULT_TIMEOUT):
    """
    Funzione interna: wrapper sottile su http_client.request_with_retry, con
    PubMedRequestError come tipo di eccezione sollevato. Stesso pattern di
    openalex_client._request_with_retry (vedi quel modulo per il perche' di
    questa estrazione).
    """
    return request_with_retry(
        url, params,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        timeout=timeout,
        error_cls=PubMedRequestError,
    )

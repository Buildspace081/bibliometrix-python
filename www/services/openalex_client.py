"""
Client HTTP per l'API pubblica di OpenAlex (https://api.openalex.org).

Responsabilita' di questo modulo:
- Eseguire ricerche testuali sull'endpoint /works.
- Gestire la paginazione cursor-based per scaricare risultati oltre la singola pagina.
- Applicare retry con backoff esponenziale sugli errori transitori (rate limit 429,
  errori 5xx, timeout di rete).
- Risolvere in batch una lista di ID OpenAlex (usato per popolare la colonna CR a
  partire dagli ID grezzi contenuti in `referenced_works`).

Questo modulo non fa alcun mapping verso lo schema WoS-style: restituisce sempre i
dizionari JSON grezzi cosi' come li restituisce OpenAlex. Il mapping verso le 34
colonne e' responsabilita' di openalex_mapper.py; l'orchestrazione dei due e'
responsabilita' di etl_pipeline.py.
"""

import logging

from .utils import *


logger = logging.getLogger(__name__)


BASE_URL = "https://api.openalex.org"
WORKS_ENDPOINT = f"{BASE_URL}/works"

DEFAULT_PER_PAGE = 25
MAX_PER_PAGE = 200  # limite massimo imposto dalle API OpenAlex
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 1.5
DEFAULT_TIMEOUT = 10  # secondi
DEFAULT_BATCH_SIZE = 50  # limite OpenAlex per filter=openalex_id:ID1|ID2|...


class OpenAlexRequestError(Exception):
    """Sollevata quando una richiesta a OpenAlex fallisce in modo non recuperabile
    (status 4xx diverso da 429, oppure 5xx/timeout dopo l'esaurimento dei retry)."""
    pass


def search_works(query, max_results=None, filters=None, mailto=None, per_page=MAX_PER_PAGE):
    """
    Esegue una ricerca testuale completa su /works, paginando automaticamente
    con cursore finche' OpenAlex non restituisce `meta.next_cursor == None`
    oppure finche' non e' stato raccolto `max_results` risultati.

    Ogni singola richiesta di pagina passa da _request_with_retry (retry con
    backoff esponenziale su 429/5xx/errori di rete, vedi quella funzione).

    Args:
        query: stringa di ricerca libera, mappata sul parametro `search` di OpenAlex.
        max_results: numero massimo di risultati da raccogliere complessivamente;
            None per scaricare tutti i risultati della query (attenzione: puo'
            comportare molte richieste HTTP su query con molti match).
        filters: dict opzionale di filtri aggiuntivi (es. {"publication_year": "2020-2023"}),
            serializzato nel parametro `filter` di OpenAlex come coppie
            "chiave:valore" separate da virgola (AND tra chiavi diverse; per OR
            sullo stesso campo il valore va gia' passato nel formato
            "a|b|c" da chi costruisce il dict).
        mailto: email da passare come parametro `mailto` per rientrare nella
            "polite pool" di OpenAlex (rate limit piu' alto e prioritario).
        per_page: risultati per pagina richiesti ad OpenAlex ad ogni chiamata
            (di default MAX_PER_PAGE=200, il massimo consentito, per minimizzare
            il numero di richieste). Esposto come parametro soprattutto per
            poterlo abbassare nei test, cosi' da forzare piu' pagine anche con
            max_results piccoli.

    Returns:
        list[dict]: work grezzi raccolti su tutte le pagine necessarie,
        nell'ordine restituito da OpenAlex, troncati a max_results se specificato.

    Raises:
        OpenAlexRequestError: se una richiesta di pagina fallisce in modo non
            recuperabile (propagata da _request_with_retry).
    """
    if max_results is not None and max_results <= 0:
        return []

    effective_per_page = min(per_page, MAX_PER_PAGE)

    results = []
    cursor = "*"

    while cursor is not None:
        params = {
            "search": query,
            "per-page": effective_per_page,
            "cursor": cursor,
        }
        if mailto:
            params["mailto"] = mailto
        if filters:
            params["filter"] = _serialize_filters(filters)

        response = _request_with_retry(WORKS_ENDPOINT, params)
        payload = response.json()

        page_results = payload.get("results", [])
        if not page_results:
            break

        results.extend(page_results)

        if max_results is not None and len(results) >= max_results:
            results = results[:max_results]
            break

        cursor = (payload.get("meta") or {}).get("next_cursor")

    return results


def _serialize_filters(filters):
    """
    Funzione interna: serializza un dict di filtri nel formato query-string
    atteso dal parametro `filter` di OpenAlex: coppie "chiave:valore" separate
    da virgola (semantica AND tra chiavi diverse). La sintassi OR su uno stesso
    campo (`chiave:valore1|valore2`) va gia' incapsulata nel valore passato per
    quella chiave da chi costruisce il dict `filters`.

    Args:
        filters: dict[str, str] di filtri OpenAlex.

    Returns:
        str: valore da assegnare al parametro `filter` nella query string.
    """
    return ",".join(f"{key}:{value}" for key, value in filters.items())


def get_work_by_id(openalex_id, mailto=None):
    """
    Recupera un singolo "work" OpenAlex dato il suo ID (short form "W123..." o URL
    completo "https://openalex.org/W123...").

    Args:
        openalex_id: identificatore OpenAlex del work da recuperare.
        mailto: email per la polite pool.

    Returns:
        dict | None: l'oggetto "work" grezzo, oppure None se non trovato (404).

    Raises:
        OpenAlexRequestError: per errori diversi da 404.
    """
    raise NotImplementedError


def get_works_by_ids(ids, mailto=None, batch_size=DEFAULT_BATCH_SIZE):
    """
    Risolve in batch una lista di ID OpenAlex verso i rispettivi oggetti "work"
    completi, usando il filtro OR `openalex_id:ID1|ID2|...` supportato da /works
    (fino a 50 ID per chiamata, limite imposto dall'API OpenAlex) per minimizzare
    il numero di richieste HTTP.

    Usato tipicamente da openalex_mapper.py::format_cr_column per risolvere il
    contenuto di `referenced_works` (che in OpenAlex e' solo una lista di ID)
    nelle citazioni leggibili richieste dalla colonna CR dello schema WoS-style.

    Un batch che fallisce in modo persistente (dopo tutti i retry di
    _request_with_retry) NON interrompe la risoluzione degli altri batch:
    l'errore viene loggato e gli ID di quel batch restano semplicemente assenti
    dal dizionario restituito, cosi' come gli ID non trovati da OpenAlex. Il
    chiamante non puo' distinguere "non trovato" da "batch fallito" guardando
    solo il dizionario risultato: se questa distinzione servisse a valle, andra'
    aggiunta separatamente (es. restituendo anche la lista di ID falliti).

    Args:
        ids: lista di ID OpenAlex (forma short "W123..." o URL completo
            "https://openalex.org/W123...") da risolvere. Duplicati e ID
            vuoti/None vengono ignorati.
        mailto: email per la polite pool.
        batch_size: numero massimo di ID per chiamata; la lista (deduplicata e
            normalizzata) viene spezzata in chunk di questa dimensione.

    Returns:
        dict[str, dict]: mappa da ID OpenAlex normalizzato (short form) al
        relativo oggetto "work" grezzo. Gli ID non risolvibili (non trovati da
        OpenAlex, oppure appartenenti a un batch fallito dopo i retry) sono
        semplicemente assenti dal risultato.
    """
    normalized_ids = []
    seen = set()
    for raw_id in ids or []:
        normalized = _normalize_openalex_id(raw_id)
        if normalized and normalized not in seen:
            seen.add(normalized)
            normalized_ids.append(normalized)

    resolved = {}
    for batch_start in range(0, len(normalized_ids), batch_size):
        batch = normalized_ids[batch_start:batch_start + batch_size]
        params = {
            "filter": "openalex_id:" + "|".join(batch),
            # per-page deve coprire l'intero batch, altrimenti si rischia di
            # ricevere solo i primi DEFAULT_PER_PAGE risultati del filtro OR.
            "per-page": len(batch),
        }
        if mailto:
            params["mailto"] = mailto

        try:
            response = _request_with_retry(WORKS_ENDPOINT, params)
        except OpenAlexRequestError as exc:
            logger.error(
                "get_works_by_ids: batch di %d ID fallito dopo i retry (primi ID: %s): %s",
                len(batch), batch[:3], exc,
            )
            continue

        payload = response.json()
        for work in payload.get("results", []):
            work_id = _normalize_openalex_id(work.get("id"))
            if work_id:
                resolved[work_id] = work

    return resolved


def _normalize_openalex_id(openalex_id_or_url):
    """
    Funzione interna: normalizza un ID OpenAlex alla forma short (es. "W123456789"),
    accettando sia la forma short che l'URL completo ("https://openalex.org/W123456789").

    Args:
        openalex_id_or_url: ID OpenAlex in una qualsiasi delle due forme, oppure
            None/stringa vuota.

    Returns:
        str: ID in forma short, normalizzato; stringa vuota se
        openalex_id_or_url e' None/vuoto.
    """
    if not openalex_id_or_url:
        return ""
    return openalex_id_or_url.rsplit("/", 1)[-1]


def _request_with_retry(url, params, max_retries=DEFAULT_MAX_RETRIES, backoff_factor=DEFAULT_BACKOFF_FACTOR, timeout=DEFAULT_TIMEOUT):
    """
    Funzione interna: esegue una GET HTTP con retry ed exponential backoff.

    Riprova la richiesta in caso di:
    - errori di rete/timeout,
    - HTTP 429 (rate limit), rispettando l'header Retry-After se presente
      (altrimenti backoff esponenziale),
    - HTTP 5xx (errori transitori lato server).

    Non riprova su errori 4xx diversi da 429 (es. 400/404), che vengono considerati
    definitivi e propagati immediatamente come OpenAlexRequestError.

    Args:
        url: URL completo della richiesta.
        params: dict di query string da passare a requests.get.
        max_retries: numero massimo di RI-tentativi dopo il primo (quindi al
            massimo max_retries + 1 richieste HTTP totali).
        backoff_factor: fattore moltiplicativo per il tempo di attesa tra un
            tentativo e il successivo (attesa = backoff_factor ** tentativo).
        timeout: timeout in secondi per ciascuna richiesta HTTP.

    Returns:
        requests.Response: la risposta HTTP con status < 400.

    Raises:
        OpenAlexRequestError: su errore 4xx diverso da 429 (nessun retry), oppure
            dopo l'esaurimento dei retry per 429/5xx/errori di rete, con status
            code e corpo della risposta inclusi nel messaggio per facilitare il debug.
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_error = exc
            if attempt == max_retries:
                raise OpenAlexRequestError(
                    f"Richiesta a {url} fallita dopo {max_retries + 1} tentativi: {exc}"
                ) from exc
            time.sleep(backoff_factor ** attempt)
            continue

        if response.status_code < 400:
            return response

        if response.status_code == 429 or response.status_code >= 500:
            last_error = OpenAlexRequestError(
                f"HTTP {response.status_code} da {url}: {response.text[:500]}"
            )
            if attempt == max_retries:
                raise last_error

            retry_after = response.headers.get("Retry-After")
            wait_seconds = backoff_factor ** attempt
            if retry_after is not None:
                try:
                    wait_seconds = float(retry_after)
                except ValueError:
                    pass
            time.sleep(wait_seconds)
            continue

        # 4xx diverso da 429: errore considerato definitivo, nessun retry.
        raise OpenAlexRequestError(
            f"HTTP {response.status_code} da {url}: {response.text[:500]}"
        )

    # Non raggiungibile in condizioni normali (il loop ritorna o solleva ad ogni
    # iterazione), presente solo per robustezza.
    raise OpenAlexRequestError(f"Richiesta a {url} fallita: {last_error}")

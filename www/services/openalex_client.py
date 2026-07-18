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

# Tupla (connect_timeout, read_timeout), non un singolo valore. DEBUGGING LOG:
# con un timeout singolo (era 10s), `requests` lo applica come timeout di
# INATTIVITA' tra un chunk di risposta e il successivo, NON come tetto sul
# tempo totale della richiesta - se il server (o un proxy/CDN intermedio)
# manda anche un solo byte ogni tanto entro la finestra, la richiesta puo'
# restare appesa indefinitamente senza mai sollevare ReadTimeout. Diagnosticato
# concretamente: una query "AI" e' rimasta bloccata >2m44s su una singola
# chiamata di search_works (connessione TCP ESTABLISHED verso l'infrastruttura
# OpenAlex, CPU 0%, nessun retry mai scattato) prima di essere interrotta
# manualmente. connect_timeout=5s (tempo per stabilire la connessione TCP),
# read_timeout=15s (silenzio massimo tollerato tra un byte e l'altro della
# risposta) restano lo stesso tipo di garanzia "anti-inattivita'", ma con
# margini piu' stretti; il vero argine contro un'attesa indefinita e' pero'
# il tetto di tempo complessivo aggiunto a search_works (vedi piu' sotto) e a
# get_works_by_ids, che non dipende da come si comporta il timeout di requests.
DEFAULT_TIMEOUT = (5, 15)

DEFAULT_BATCH_SIZE = 50  # limite OpenAlex per filter=openalex_id:ID1|ID2|...

# max_retries ridotto, isolato a get_works_by_ids (risoluzione batch di
# referenced_works per popolare CR). NON tocca DEFAULT_MAX_RETRIES, che resta
# a 3 per search_works e per qualunque altro chiamante generico di
# _request_with_retry. Motivazione: una query generica con molti risultati
# puo' generare decine di batch da risolvere (es. 60 batch per 30 paper con
# referenced_works al cap di 100 ciascuno); con max_retries=3 il caso peggiore
# per singolo batch (assumendo che il read_timeout scatti regolarmente) resta
# nell'ordine delle decine di secondi per tentativo, che su 60 batch si somma
# rapidamente. Con max_retries=1 (2 tentativi totali) il caso peggiore per
# singolo batch si dimezza, riducendo proporzionalmente anche il tetto
# complessivo - in combinazione con il timeout di fase in
# _resolve_references_for_works (vedi etl_pipeline.py), non con l'obiettivo
# di eliminarlo da solo.
RESOLVE_MAX_RETRIES = 1

# Budget di default (secondi) per l'INTERA paginazione di search_works, non
# per singola richiesta di pagina. Stesso ruolo di resolve_timeout_seconds in
# get_works_by_ids/_resolve_references_for_works: un secondo argine oltre al
# timeout a tupla di _request_with_retry, indipendente da come si comporta
# la libreria requests in casi limite (connessione tenuta viva artificialmente,
# server lento ma "vivo").
DEFAULT_FETCH_TIMEOUT_SECONDS = 30

# TERZO BUG REALE DIAGNOSTICATO OGGI (debugging log, stesso stile degli altri
# due): _request_with_retry rispettava l'header Retry-After di una risposta
# 429 senza alcun tetto massimo, facendo `time.sleep(float(retry_after))`.
# Diagnosticato concretamente: dopo aver esaurito il budget giornaliero delle
# API OpenAlex durante i test di questa sessione, una richiesta ha ricevuto
# 429 con `Retry-After: 28979` (quasi 8 ore) e il processo e' rimasto
# "bloccato" per ore in un time.sleep() legittimo ma inutilizzabile in un
# contesto interattivo (Shiny). La firma era identica a un socket appeso
# (CPU 0%, stato sleeping, connessione TCP ESTABLISHED del pool keep-alive di
# requests ancora aperta) e per questo era stata scambiata inizialmente per
# un problema di timeout HTTP - non lo era: la risposta 429 arrivava in
# meno di 0.1s, il problema era tutto nello sleep successivo, non tollerato
# ne' dal timeout a tupla di _request_with_retry (si applica solo mentre si
# attende la risposta, non dopo averla ricevuta) ne' dal budget di fase di
# search_works/get_works_by_ids (controllato solo PRIMA di iniziare una nuova
# richiesta, non durante lo sleep interno a un tentativo gia' in corso).
# Nessun retry_after piu' lungo di questo tetto viene piu' onorato per intero:
# se la richiesta fallisce ancora dopo l'attesa limitata e i tentativi
# rimasti, risale normalmente come OpenAlexRequestError (comportamento gia'
# esistente, invariato), che il resto della pipeline e l'handler della pagina
# API sanno gia' gestire mostrando un errore invece di bloccarsi in silenzio.
MAX_RETRY_AFTER_WAIT_SECONDS = 20


class OpenAlexRequestError(Exception):
    """Sollevata quando una richiesta a OpenAlex fallisce in modo non recuperabile
    (status 4xx diverso da 429, oppure 5xx/timeout dopo l'esaurimento dei retry)."""
    pass


def search_works(query, max_results=None, filters=None, mailto=None, per_page=MAX_PER_PAGE,
                  fetch_timeout_seconds=DEFAULT_FETCH_TIMEOUT_SECONDS, start_time=None):
    """
    Esegue una ricerca testuale completa su /works, paginando automaticamente
    con cursore finche' OpenAlex non restituisce `meta.next_cursor == None`
    oppure finche' non e' stato raccolto `max_results` risultati.

    Ogni singola richiesta di pagina passa da _request_with_retry (retry con
    backoff esponenziale su 429/5xx/errori di rete, vedi quella funzione).

    LIMITE DI SICUREZZA (debugging log): se `fetch_timeout_seconds` non e'
    None, PRIMA di richiedere ogni nuova pagina si controlla il tempo
    trascorso da `start_time` (o dall'inizio di questa chiamata, se
    start_time non e' fornito): se il budget e' superato, la paginazione si
    interrompe con un break (non un'eccezione) e vengono restituiti i
    risultati gia' raccolti fino a quel momento (parziali ma utilizzabili),
    invece di continuare a chiedere altre pagine indefinitamente. E' un
    secondo argine indipendente dal timeout a tupla di _request_with_retry:
    diagnosticato un caso reale in cui una singola richiesta HTTP e' rimasta
    bloccata piu' di due minuti senza mai sollevare un'eccezione di timeout
    (connessione tenuta viva artificialmente) - questo budget limita il danno
    anche se il timeout della singola richiesta non dovesse bastare.

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
        fetch_timeout_seconds: budget di tempo (secondi) per l'INTERA
            paginazione, non per singola richiesta. Default
            DEFAULT_FETCH_TIMEOUT_SECONDS (30s). None per nessun limite
            (comportamento pre-esistente).
        start_time: istante di riferimento (da time.monotonic()) da cui
            calcolare il tempo trascorso; se None, si usa l'istante di
            ingresso in questa funzione. Permette al chiamante (tipicamente
            etl_pipeline.py::_fetch_raw_works) di far partire il cronometro
            prima ancora di chiamare search_works.

    Returns:
        list[dict]: work grezzi raccolti su tutte le pagine necessarie (o
        raccolte prima dell'esaurimento del budget di tempo), nell'ordine
        restituito da OpenAlex, troncati a max_results se specificato.

    Raises:
        OpenAlexRequestError: se una richiesta di pagina fallisce in modo non
            recuperabile (propagata da _request_with_retry).
    """
    if max_results is not None and max_results <= 0:
        return []

    if start_time is None:
        start_time = time.monotonic()

    effective_per_page = min(per_page, MAX_PER_PAGE)

    results = []
    cursor = "*"

    while cursor is not None:
        if fetch_timeout_seconds is not None and (time.monotonic() - start_time) > fetch_timeout_seconds:
            logger.warning(
                "search_works: budget di %.1fs esaurito, interrotta la paginazione dopo %d risultati raccolti",
                fetch_timeout_seconds, len(results),
            )
            break

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


def get_works_by_ids(ids, mailto=None, batch_size=DEFAULT_BATCH_SIZE, resolve_timeout_seconds=None, start_time=None):
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

    Ogni chiamata HTTP verso un batch usa RESOLVE_MAX_RETRIES (1 ri-tentativo,
    non i 3 di default) invece del default di _request_with_retry: qui i batch
    possono essere decine per una singola risoluzione (vedi
    etl_pipeline.py::_resolve_references_for_works), quindi il costo peggiore
    per singolo batch va tenuto basso deliberatamente, a differenza di
    search_works che chiama _request_with_retry con i retry di default.

    Se resolve_timeout_seconds e' specificato, PRIMA di iniziare ogni nuovo
    batch si controlla il tempo trascorso da start_time (o dall'inizio di
    questa chiamata, se start_time non e' fornito): se il budget e' superato,
    il loop si interrompe con un break (non un'eccezione) e viene restituito
    il dizionario parziale gia' risolto fino a quel momento. Gli ID dei batch
    non ancora processati restano semplicemente assenti dal risultato, con lo
    stesso effetto pratico di un batch fallito: format_cr_column ricadra' sul
    fallback a ID nudo per quei riferimenti.

    Args:
        ids: lista di ID OpenAlex (forma short "W123..." o URL completo
            "https://openalex.org/W123...") da risolvere. Duplicati e ID
            vuoti/None vengono ignorati.
        mailto: email per la polite pool.
        batch_size: numero massimo di ID per chiamata; la lista (deduplicata e
            normalizzata) viene spezzata in chunk di questa dimensione.
        resolve_timeout_seconds: budget di tempo (secondi) per l'INTERA
            risoluzione, non per singolo batch. None (default) significa
            nessun limite: tutti i batch vengono processati indipendentemente
            dal tempo impiegato.
        start_time: istante di riferimento (da time.monotonic()) da cui
            calcolare il tempo trascorso; se None, si usa l'istante di ingresso
            in questa funzione. Permette al chiamante (tipicamente
            etl_pipeline.py::_resolve_references_for_works) di far partire il
            cronometro prima ancora di chiamare get_works_by_ids.

    Returns:
        dict[str, dict]: mappa da ID OpenAlex normalizzato (short form) al
        relativo oggetto "work" grezzo. Gli ID non risolvibili (non trovati da
        OpenAlex, appartenenti a un batch fallito dopo i retry, oppure mai
        raggiunti per esaurimento del budget di tempo) sono semplicemente
        assenti dal risultato.
    """
    normalized_ids = []
    seen = set()
    for raw_id in ids or []:
        normalized = _normalize_openalex_id(raw_id)
        if normalized and normalized not in seen:
            seen.add(normalized)
            normalized_ids.append(normalized)

    if start_time is None:
        start_time = time.monotonic()

    resolved = {}
    for batch_start in range(0, len(normalized_ids), batch_size):
        if resolve_timeout_seconds is not None and (time.monotonic() - start_time) > resolve_timeout_seconds:
            logger.warning(
                "get_works_by_ids: budget di %.1fs esaurito, interrotto dopo %d/%d ID risolti "
                "(%d batch rimanenti non processati)",
                resolve_timeout_seconds, len(resolved), len(normalized_ids),
                (len(normalized_ids) - batch_start + batch_size - 1) // batch_size,
            )
            break

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
            response = _request_with_retry(WORKS_ENDPOINT, params, max_retries=RESOLVE_MAX_RETRIES)
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
    - HTTP 429 (rate limit), rispettando l'header Retry-After se presente ma
      con un tetto a MAX_RETRY_AFTER_WAIT_SECONDS (un server puo' chiedere
      un'attesa di ore, vedi il commento su quella costante; altrimenti
      backoff esponenziale),
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
        timeout: tupla (connect_timeout, read_timeout) in secondi, passata
            direttamente a requests.get. NON e' un tetto sul tempo totale
            della richiesta: read_timeout e' il silenzio massimo tollerato
            tra un chunk di risposta e il successivo (vedi DEFAULT_TIMEOUT
            per il perche' di questa distinzione).

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
                    # Tetto a MAX_RETRY_AFTER_WAIT_SECONDS: un server puo'
                    # legittimamente chiedere di attendere ore (visto in
                    # produzione con un 429 da budget esaurito e
                    # Retry-After: 28979), ma un'attesa cosi' lunga non e'
                    # utilizzabile in un contesto interattivo - vedi il
                    # commento su MAX_RETRY_AFTER_WAIT_SECONDS per il dettaglio.
                    wait_seconds = min(float(retry_after), MAX_RETRY_AFTER_WAIT_SECONDS)
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

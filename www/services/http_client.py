"""
Client HTTP generico con retry/backoff/timeout robusti, condiviso da tutti i
client di sorgente (OpenAlex, PubMed, ...). Nessuna logica specifica di una
singola API vive qui: endpoint, parametri di query e la classe di eccezione
da sollevare sono responsabilita' del chiamante.

Estratto da openalex_client.py::_request_with_retry quando e' stata aggiunta
PubMed come seconda fonte: quella funzione era gia' completamente generica
(prendeva solo url+params in input), l'unica parte "OpenAlex-specific" era il
nome della classe di eccezione sollevata direttamente al suo interno. Senza
questa estrazione, i tre bug reali diagnosticati e corretti su OpenAlex in
questa sessione - timeout singolo che non copre il tempo totale della
richiesta, header Retry-After onorato senza alcun tetto, retry ingenui su
errori transitori - sarebbero rimasti da ri-diagnosticare e ri-correggere una
seconda volta, identici, per PubMed.
"""

import logging

from .utils import *


logger = logging.getLogger(__name__)


DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 1.5

# Tupla (connect_timeout, read_timeout), non un singolo valore - vedi
# openalex_client.py per la cronaca completa del bug che ha portato a questa
# scelta: un timeout singolo passato a requests.get() e' un timeout di
# INATTIVITA' tra un chunk di risposta e il successivo, non un tetto sul
# tempo totale della richiesta.
DEFAULT_TIMEOUT = (5, 15)

# Tetto massimo (secondi) onorato per l'header Retry-After di una risposta
# 429 - vedi openalex_client.py per la cronaca completa del bug (un server puo'
# legittimamente chiedere un'attesa di ore, inutilizzabile in un contesto
# interattivo).
MAX_RETRY_AFTER_WAIT_SECONDS = 20


class ExternalAPIRequestError(Exception):
    """Sollevata quando una richiesta a un'API esterna fallisce in modo non
    recuperabile. Le classi di eccezione source-specific (es.
    OpenAlexRequestError, PubMedRequestError) ereditano da questa: un
    chiamante che vuole gestire "qualunque fonte esterna fallita" allo stesso
    modo puo' intercettare solo questa base, senza conoscere quale client
    l'ha sollevata."""
    pass


def request_with_retry(url, params, max_retries=DEFAULT_MAX_RETRIES,
                        backoff_factor=DEFAULT_BACKOFF_FACTOR, timeout=DEFAULT_TIMEOUT,
                        error_cls=ExternalAPIRequestError):
    """
    Esegue una GET HTTP con retry ed exponential backoff.

    Riprova la richiesta in caso di:
    - errori di rete/timeout,
    - HTTP 429 (rate limit), rispettando l'header Retry-After se presente ma
      con un tetto a MAX_RETRY_AFTER_WAIT_SECONDS (un server puo' chiedere
      un'attesa di ore; altrimenti backoff esponenziale),
    - HTTP 5xx (errori transitori lato server).

    Non riprova su errori 4xx diversi da 429 (es. 400/404), che vengono
    considerati definitivi e propagati immediatamente come `error_cls`.

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
            tra un chunk di risposta e il successivo.
        error_cls: classe di eccezione da sollevare in caso di fallimento
            definitivo. Deve accettare un singolo argomento posizionale
            (il messaggio). Permette a ciascun client source-specific di
            sollevare la propria sottoclasse (es. OpenAlexRequestError,
            PubMedRequestError) riusando identica la logica di retry.

    Returns:
        requests.Response: la risposta HTTP con status < 400.

    Raises:
        error_cls: su errore 4xx diverso da 429 (nessun retry), oppure dopo
            l'esaurimento dei retry per 429/5xx/errori di rete, con status
            code e corpo della risposta inclusi nel messaggio per facilitare
            il debug.
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_error = exc
            if attempt == max_retries:
                raise error_cls(
                    f"Richiesta a {url} fallita dopo {max_retries + 1} tentativi: {exc}"
                ) from exc
            time.sleep(backoff_factor ** attempt)
            continue

        if response.status_code < 400:
            return response

        if response.status_code == 429 or response.status_code >= 500:
            last_error = error_cls(
                f"HTTP {response.status_code} da {url}: {response.text[:500]}"
            )
            if attempt == max_retries:
                raise last_error

            retry_after = response.headers.get("Retry-After")
            wait_seconds = backoff_factor ** attempt
            if retry_after is not None:
                try:
                    wait_seconds = min(float(retry_after), MAX_RETRY_AFTER_WAIT_SECONDS)
                except ValueError:
                    pass
            time.sleep(wait_seconds)
            continue

        # 4xx diverso da 429: errore considerato definitivo, nessun retry.
        raise error_cls(
            f"HTTP {response.status_code} da {url}: {response.text[:500]}"
        )

    # Non raggiungibile in condizioni normali (il loop ritorna o solleva ad ogni
    # iterazione), presente solo per robustezza.
    raise error_cls(f"Richiesta a {url} fallita: {last_error}")

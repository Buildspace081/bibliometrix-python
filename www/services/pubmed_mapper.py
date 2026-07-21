"""
Mapping PubMed (E-utilities EFetch XML) -> schema a 34 colonne WoS-style.

Speculare a openalex_mapper.py (che a sua volta e' speculare a
format_functions.py per le sorgenti storiche): qui e' definita una sola
sorgente, "PubMed", con una funzione format_XX_column per ciascuna delle 34
colonne dello schema bibliometrix, piu' una funzione di orchestrazione
map_article_to_record che le combina in un unico record.

Ogni funzione riceve `article`, un elemento xml.etree.ElementTree.Element
<PubmedArticle> cosi' come restituito da pubmed_client.search_articles/
fetch_articles, e naviga percorsi RELATIVI ESPLICITI (es.
"MedlineCitation/Article/ArticleTitle") invece di wildcard ".//" ovunque sia
possibile un'ambiguita' strutturale: il caso reale verificato in questa
sessione e' MedlineCitation/PMID (il PMID dell'articolo stesso) contro
MedlineCitation/CommentsCorrectionsList/CommentsCorrections/PMID (PMID di
articoli CORRELATI, es. errata corrige o commenti), entrambi presenti nello
stesso documento - un ".//PMID" generico avrebbe funzionato per puro
accidente di ordine dei nodi nei campioni osservati, ma non e' un contratto
strutturale affidabile.

Differenze principali rispetto a OpenAlex, da tenere presenti (vedi analisi
fatta in conversazione dopo l'esplorazione empirica di piu' record PubMed
reali):
- Gli autori non sono un oggetto strutturato con display_name gia' pronto:
  PubMed espone LastName/ForeName/Initials separati (o CollectiveName per
  autori collettivi, es. gruppi di studio clinico), quindi AU/AF vanno
  RICOSTRUITI concatenando questi campi, nello stesso stile "Cognome
  Iniziali"/"Cognome NomeCompleto" gia' usato dalla pipeline storica per la
  sorgente PubMed (vedi format_functions.py::format_au_column/
  format_af_column, branch `source == 'PubMed'`, che legge pero' da un
  export MEDLINE .txt con campi AU/FAU gia' pre-formattati dalla stessa
  convenzione - qui la ricostruiamo da zero a partire dai sotto-elementi XML).
- Le affiliazioni (AffiliationInfo/Affiliation) sono un'UNICA stringa di testo
  libero (indirizzo completo, a volte con email in coda), NON strutturate in
  nome-istituzione/paese come in OpenAlex (authorships[].institutions[]):
  C1 qui e' quindi costruita come "[Autore] testo-affiliazione-intero" senza
  alcun parsing di paese (a differenza di format_c1_column in
  openalex_mapper.py, che separa institution.display_name da
  institution.country_code). Di conseguenza AU_UN eredita la stessa
  approssimazione: contiene la stringa di affiliazione grezza per intero
  (indirizzo compreso), non un nome di istituzione isolato e ripulito -
  vedi format_au_un_column per il dettaglio.
- Il testo dei riferimenti bibliografici, quando presente
  (PubmedData/ReferenceList/Reference/Citation), e' GIA' una stringa
  leggibile in formato citazione ("Autore1, Autore2... (Anno) Titolo. Rivista
  Vol:pagine"), a differenza di OpenAlex dove referenced_works e' solo una
  lista di ID da risolvere con una chiamata batch separata
  (openalex_client.get_works_by_ids). Verificato empiricamente: ReferenceList
  e' presente solo per una parte dei record (tipicamente quelli con
  full-text collegato a PMC), assente per molti altri (es. articoli piu'
  vecchi, o riviste che non forniscono la bibliografia strutturata a PubMed) -
  in quel caso CR e' semplicemente una lista vuota, non un errore.
- TC (Times Cited) non ha alcun equivalente in PubMed (che non e' un indice
  citazionale): restituisce sempre 0, non un dato mancante recuperabile per
  altra via.
- MeshHeadingList/MeshHeading/DescriptorName (i termini MeSH assegnati da
  indicizzatori NLM da un vocabolario controllato) e' concettualmente PIU'
  vicino al significato originale di ID (Keywords Plus: termini assegnati da
  un processo editoriale/algoritmico esterno all'autore) rispetto ai
  "concepts" di OpenAlex (assegnati da un classificatore automatico
  proprietario) - vedi format_id_column.
- KeywordList con attributo Owner="NOTNLM" contiene le keyword scelte
  dall'autore stesso (quando l'editore le fornisce a PubMed), quindi e' un
  segnale piu' fedele al significato originale di DE (Author Keywords)
  rispetto ai "keywords" algoritmici di OpenAlex - vedi format_de_column.
- Journal/ISOAbbreviation e' un'abbreviazione standardizzata genuina (es.
  "Lancet", "N Engl J Med"), a differenza di OpenAlex che non fornisce alcuna
  abbreviazione (format_ji_column li' restituisce sempre "") - vedi
  format_ji_column qui sotto per il contrasto.
- Alcune colonne non hanno, per decisione esplicita, un equivalente popolato
  in questa pipeline (stesso approccio gia' preso per OpenAlex): EM, FU, FX,
  OA, OI (vedi nota sotto), PU, RP, SC restituiscono sempre stringa vuota.
  OI e' un'eccezione parziale: PubMed espone ORCID per autore
  (Author/Identifier[@Source='ORCID']) quando presente, quindi qui e'
  effettivamente implementata (a differenza di OpenAlex, dove OI e' sempre
  vuota per assenza del dato) - vedi format_oi_column.
"""

import re

from .utils import *
from .metatagextraction import SR


# Numero massimo di riferimenti considerati da format_cr_column per un
# singolo articolo. Stessa motivazione di MAX_REFERENCED_WORKS in
# openalex_mapper.py: alcune review citano centinaia di riferimenti, e CR
# nello schema WoS-style e' comunque pensata come lista informativa, non
# esaustiva per definizione in molte fonti - qui non c'e' nemmeno il costo di
# una chiamata di rete aggiuntiva (il testo e' gia' incluso nell'XML), ma il
# cap resta per coerenza con la stessa decisione di design presa per
# OpenAlex e per limitare la dimensione della colonna.
MAX_REFERENCES = 100

# Mappa dichiarativa PublicationType PubMed -> vocabolario WoS-style per DT.
# A differenza di OPENALEX_TYPE_TO_WOS_DT (un solo `type` per work), un
# articolo PubMed puo' avere PIU' PublicationType contemporaneamente (es.
# "Clinical Trial" + "Journal Article" + "Randomized Controlled Trial"),
# quasi sempre includendo il generico "Journal Article": format_dt_column
# preferisce il primo tipo NON generico presente (vedi quella funzione per
# la logica di scelta), usando questa mappa solo per la traduzione nel
# vocabolario WoS-style. Un tipo non presente qui non e' un errore: si
# ricade sul valore originale (vedi format_dt_column).
PUBMED_TYPE_TO_WOS_DT: dict = {
    "Journal Article": "Article",
    "Review": "Review",
    "Systematic Review": "Review",
    "Meta-Analysis": "Review",
    "Letter": "Letter",
    "Editorial": "Editorial Material",
    "Comment": "Editorial Material",
    "News": "News Item",
    "Biography": "Biographical-Item",
    "Published Erratum": "Correction",
    "Retraction of Publication": "Correction",
    "Case Reports": "Article",
    "Clinical Trial": "Article",
    "Randomized Controlled Trial": "Article",
    "Multicenter Study": "Article",
    "Observational Study": "Article",
    "Preprint": "Preprint",
    "Book": "Book",
    "Book Chapter": "Book Chapter",
}


def map_article_to_record(article, sep=";"):
    """
    Funzione di orchestrazione: converte un singolo elemento <PubmedArticle>
    grezzo in un record (dict) nello schema a 34 colonne WoS-style, chiamando
    in sequenza tutte le format_XX_column definite in questo modulo.

    Analoga a openalex_mapper.py::map_work_to_record. Non calcola SR (che
    richiede l'intera collezione, vedi compute_sr_for_records piu' in basso).

    Args:
        article: xml.etree.ElementTree.Element, singolo nodo <PubmedArticle>
            (vedi pubmed_client.search_articles/fetch_articles).
        sep: separatore usato internamente per unire valori multipli in
            colonne scalari (es. OI). Non incide sulle colonne STRING_LIST,
            che restano list[str] native.

    Returns:
        dict: record con esattamente le chiavi di `columns` (lista canonica
        definita in www/services/utils.py) meno "SR" — 33 chiavi in totale.

    Raises:
        ValueError: se il dict costruito internamente non coincide
            esattamente con `set(columns) - {"SR"}` — indica una regressione
            tra questa funzione e la lista canonica in utils.py.
    """
    record = {
        "AB": format_ab_column(article),
        "AF": format_af_column(article),
        "AU": format_au_column(article),
        "AU_UN": format_au_un_column(article),
        "AU1_UN": format_au1_un_column(article),
        "BP": format_bp_column(article),
        "EP": format_ep_column(article),
        "CR": format_cr_column(article),
        "C1": format_c1_column(article),
        "DB": format_db_column(article),
        "DE": format_de_column(article),
        "DI": format_di_column(article),
        "DT": format_dt_column(article),
        "EM": format_em_column(article),
        "FU": format_fu_column(article),
        "FX": format_fx_column(article),
        "IS": format_is_column(article),
        "JI": format_ji_column(article),
        "ID": format_id_column(article),
        "LA": format_la_column(article),
        "OA": format_oa_column(article),
        "OI": format_oi_column(article, sep=sep),
        "PMID": format_pmid_column(article),
        "PU": format_pu_column(article),
        "PY": format_py_column(article),
        "RP": format_rp_column(article),
        "SC": format_sc_column(article),
        "SN": format_sn_column(article),
        "SO": format_so_column(article),
        "TC": format_tc_column(article),
        "TI": format_ti_column(article),
        "UT": format_ut_column(article),
        "VL": format_vl_column(article),
    }

    expected_keys = set(columns) - {"SR"}
    actual_keys = set(record.keys())
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        raise ValueError(
            "map_article_to_record: il record prodotto non coincide con lo schema "
            "canonico (www/services/utils.py::columns) meno SR. "
            f"Mancanti: {missing}. Extra: {extra}."
        )

    return record


def _author_elements(article):
    """Funzione interna: lista degli elementi <Author> dell'articolo, [] se
    AuthorList e' assente."""
    return article.findall("MedlineCitation/Article/AuthorList/Author")


def _author_display_name(author):
    """
    Funzione interna: nome "leggibile" di un autore, usato nel prefisso
    "[Autore] ..." di C1 (stesso ruolo di author.display_name in
    openalex_mapper.py::format_c1_column). Per un autore con CollectiveName
    (es. un gruppo di studio clinico, vedi il campione PMID 8366922
    analizzato in conversazione, con <CollectiveName>Diabetes Control and
    Complications Trial Research Group</CollectiveName> come primo "autore"),
    restituisce direttamente quel nome; altrimenti "Cognome NomeCompleto".

    Returns:
        str: nome leggibile, "" se l'autore non ha ne' CollectiveName ne'
        LastName.
    """
    collective = author.findtext("CollectiveName")
    if collective:
        return collective.strip()

    last_name = (author.findtext("LastName") or "").strip()
    fore_name = (author.findtext("ForeName") or "").strip()
    if not last_name:
        return ""
    return f"{last_name} {fore_name}".strip()


def format_ab_column(article):
    """
    Colonna AB (Abstract). Concatena tutti gli elementi
    <AbstractText> sotto Article/Abstract. Molti abstract PubMed sono
    strutturati in sezioni con attributo Label (es. "BACKGROUND", "METHODS",
    "RESULTS", "CONCLUSIONS" - verificato concretamente sul PMID 9742977,
    con Label="BACKGROUND"/"METHODS"/"FINDINGS"/"INTERPRETATION"): quando
    Label e' presente viene anteposto al testo della sezione come
    "LABEL: testo", per non perdere la struttura originale; le sezioni sono
    poi unite con uno spazio.

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: abstract ricostruito, "" se Abstract/AbstractText sono assenti
        (comune per lettere, editoriali, articoli senza abstract).
    """
    sections = []
    for abstract_text in article.findall("MedlineCitation/Article/Abstract/AbstractText"):
        text = "".join(abstract_text.itertext()).strip()
        if not text:
            continue
        label = abstract_text.get("Label")
        sections.append(f"{label}: {text}" if label else text)
    return " ".join(sections)


def format_af_column(article):
    """
    Colonna AF (Authors Full Name), formato "Cognome NomeCompleto" (stessa
    convenzione, spazio non virgola, gia' usata dalla pipeline storica per
    PubMed - vedi format_functions.py::format_af_column, branch
    `source == 'PubMed'`: quella legge il campo FAU gia' pronto da un export
    MEDLINE .txt, qui lo ricostruiamo da LastName+ForeName).

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        list[str]: un elemento per autore (vedi _author_display_name per la
        gestione di CollectiveName), nell'ordine di AuthorList. Autori senza
        ne' CollectiveName ne' LastName vengono omessi.
    """
    names = []
    for author in _author_elements(article):
        name = _author_display_name(author)
        if name:
            names.append(name)
    return names


def format_au_column(article):
    """
    Colonna AU (Author/s), formato "Cognome Iniziali" (stessa convenzione
    della pipeline storica per PubMed - vedi format_functions.py::
    format_au_column, branch `source == 'PubMed'`, che legge il campo AU gia'
    pronto in quel formato da un export MEDLINE .txt; qui lo ricostruiamo da
    LastName+Initials).

    Usa l'elemento <Initials> quando presente (gia' nel formato compatto
    atteso, es. "DM"); se assente, deriva le iniziali da ForeName prendendo
    la prima lettera di ogni parola (fallback, raro nei campioni osservati).
    Per un autore con CollectiveName, usa il nome collettivo cosi' com'e'
    (nessuna iniziale da estrarre) - stessa gestione di format_af_column.

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        list[str]: un elemento per autore, nell'ordine di AuthorList. Autori
        senza ne' CollectiveName ne' LastName vengono omessi.
    """
    authors = []
    for author in _author_elements(article):
        collective = author.findtext("CollectiveName")
        if collective:
            authors.append(collective.strip())
            continue

        last_name = (author.findtext("LastName") or "").strip()
        if not last_name:
            continue

        initials = (author.findtext("Initials") or "").strip()
        if not initials:
            fore_name = author.findtext("ForeName") or ""
            initials = "".join(word[0] for word in fore_name.split() if word)

        authors.append(f"{last_name} {initials}".strip())
    return authors


def format_au_un_column(article):
    """
    Colonna AU_UN (Authors University/Institution). PubMed non fornisce un
    nome di istituzione isolato e strutturato come OpenAlex
    (authorships[].institutions[].display_name): AffiliationInfo/Affiliation
    e' un'UNICA stringa di testo libero che include tipicamente dipartimento,
    istituzione, citta', paese, ed eventualmente un'email in coda (verificato
    concretamente sul PMID 42472980: "Department of Neurosurgery,
    Afyonkarahisar Health Sciences University Health Application and Research
    Center, Afyonkarahisar, Turkey. serhatyildizhan07@gmail.com.").

    Questa funzione restituisce quindi la stringa di affiliazione GREZZA per
    intero (non un nome di istituzione ripulito da indirizzo/email) - da
    segnalare come approssimazione dichiarata, non un dato equivalente in
    qualita' a quello di OpenAlex. Un parsing piu' fine (es. riuso della
    logica a tag di metatagextraction.py::AU_UN, che individua l'istituzione
    cercando marcatori come "UNIV"/"HOSP"/"INST" in una stringa di
    affiliazione WoS-style) non e' stato applicato qui per decisione
    esplicita di scope: quella funzione lavora sull'intera collezione (come
    SR), non sul singolo record, e non e' mai invocata da alcun consumer
    a valle per la sorgente OPENALEX (verificato via grep - nessuna chiamata
    a metaTagExtraction(df, "AU_UN") in functions/*.py), quindi non c'e'
    garanzia che lo sarebbe per PUBMED: riprodurne la logica qui avrebbe
    aggiunto complessita' per un beneficio incerto.

    Deduplicazione: se piu' autori condividono la stessa stringa di
    affiliazione, questa compare una sola volta, preservando l'ordine di
    prima apparizione (stessa scelta di format_au_un_column in
    openalex_mapper.py).

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        list[str]: stringhe di affiliazione distinte, lista vuota se nessun
        autore ha AffiliationInfo.
    """
    seen = set()
    affiliations = []
    for author in _author_elements(article):
        for affiliation_info in author.findall("AffiliationInfo"):
            text = (affiliation_info.findtext("Affiliation") or "").strip()
            if text and text not in seen:
                seen.add(text)
                affiliations.append(text)
    return affiliations


def format_au1_un_column(article):
    """
    Colonna AU1_UN (Institution of the First Author). Come AU_UN, restituisce
    la stringa di affiliazione grezza (non un nome di istituzione isolato) -
    vedi format_au_un_column per la motivazione completa
    dell'approssimazione. A differenza di AU_UN, restituisce una singola
    stringa (non una lista), stessa convenzione di format_au1_un_column in
    openalex_mapper.py.

    Il primo autore e' semplicemente il primo elemento <Author> di
    AuthorList (PubMed non ha un flag equivalente ad `author_position` di
    OpenAlex: l'ordine nella lista E' l'ordine di autorship). Se ha piu'
    AffiliationInfo, viene presa solo la prima.

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: stringa di affiliazione del primo autore, "" se non disponibile
        (nessun autore, o primo autore senza AffiliationInfo).
    """
    authors = _author_elements(article)
    if not authors:
        return ""

    affiliation_info = authors[0].find("AffiliationInfo")
    if affiliation_info is None:
        return ""

    return (affiliation_info.findtext("Affiliation") or "").strip()


def format_bp_column(article):
    """
    Colonna BP (Beginning Page). Deriva da
    Article/Pagination/StartPage.

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: numero di pagina iniziale, "" se assente.
    """
    return (article.findtext("MedlineCitation/Article/Pagination/StartPage") or "").strip()


def format_ep_column(article):
    """
    Colonna EP (Ending Page). Deriva da Article/Pagination/EndPage.

    NOTA: PubMed spesso abbrevia EndPage nella sola parte che differisce da
    StartPage (es. StartPage="854", EndPage="65" per l'intervallo "854-65",
    visto concretamente sul PMID 9742977 - MedlinePgn contiene la forma
    leggibile completa "854-65", ma StartPage/EndPage restano i due valori
    grezzi separati cosi' come pubblicati da PubMed). Questa funzione fa
    pass-through diretto di EndPage senza ricostruire il numero di pagina
    completo: stesso comportamento (nessuna normalizzazione) di
    format_ep_column in openalex_mapper.py, che fa pass-through di
    biblio.last_page senza ipotesi sul formato.

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: valore grezzo di EndPage, "" se assente.
    """
    return (article.findtext("MedlineCitation/Article/Pagination/EndPage") or "").strip()


def format_cr_column(article):
    """
    Colonna CR (Cited References). Deriva da
    PubmedData/ReferenceList/Reference/Citation, gia' testo di citazione
    leggibile (a differenza di OpenAlex, dove referenced_works e' solo una
    lista di ID da risolvere - vedi il modulo docstring).

    ReferenceList e' presente solo per una parte dei record (verificato
    empiricamente: tipicamente articoli con full-text collegato a PMC);
    quando assente, restituisce lista vuota - non e' un errore ne' un dato
    mancante da recuperare altrove, e' una caratteristica nota della
    copertura bibliografica di PubMed (a differenza di OpenAlex, dove
    referenced_works e' quasi sempre presente quando risolvibile).

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        list[str]: una voce per riferimento (testo di Citation), troncata a
        MAX_REFERENCES elementi. Riferimenti senza Citation vengono omessi.
    """
    citations = []
    for reference in article.findall("PubmedData/ReferenceList/Reference"):
        citation = (reference.findtext("Citation") or "").strip()
        if citation:
            citations.append(citation)
        if len(citations) >= MAX_REFERENCES:
            break
    return citations


def format_c1_column(article):
    """
    Colonna C1 (Authors Affiliation). Costruita nel formato WoS-style
    "[NomeAutore] testo-affiliazione-intero", senza alcun parsing di paese
    (a differenza di format_c1_column in openalex_mapper.py, che separa
    institution.display_name da institution.country_code): PubMed espone
    l'affiliazione come un'unica stringa di testo libero, non come dato
    strutturato - vedi il modulo docstring per l'analisi completa di questa
    differenza.

    Conseguenza pratica per metatagextraction.py::AU_CO/AU1_CO (che deriva il
    paese da C1 cercando `c1.split(",")[-1].strip().upper()` nella whitelist
    www/static/countries.txt): funziona comunque "gratis" sulle righe C1
    prodotte da questa funzione quando l'affiliazione grezza termina
    genuinamente con il nome del paese (caso comune, verificato sui campioni
    analizzati: "..., Afyonkarahisar, Turkey." dopo lo strip del punto finale
    fatto da quella funzione) - non serve una lookup dedicata come
    ISO_COUNTRY_CODE_TO_NAME in openalex_mapper.py perche' il paese, quando
    presente, e' gia' testo libero nella stessa lingua/convenzione che
    quell'euristica si aspetta.

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        list[str]: una stringa "[NomeAutore] Affiliazione" per ogni
        combinazione (autore, AffiliationInfo) presente. Autori senza
        AffiliationInfo non producono alcuna riga. Lista vuota se nessun
        autore ha affiliazioni.
    """
    affiliations = []
    for author in _author_elements(article):
        author_name = _author_display_name(author)
        if not author_name:
            continue

        for affiliation_info in author.findall("AffiliationInfo"):
            text = (affiliation_info.findtext("Affiliation") or "").strip()
            if text:
                affiliations.append(f"[{author_name}] {text}")

    return affiliations


def format_db_column(article):
    """
    Colonna DB (Database). Costante: tutti i record prodotti da questo
    mapper provengono dalla sorgente PubMed.

    Args:
        article: elemento <PubmedArticle> (non usato).

    Returns:
        str: sempre "PUBMED".
    """
    return "PUBMED"


def format_de_column(article):
    """
    Colonna DE (Author Keywords). Deriva da KeywordList/Keyword, filtrando
    per l'attributo Owner="NOTNLM" del KeywordList genitore quando presente:
    quel valore identifica le keyword fornite dall'editore/autore (non dal
    processo di indicizzazione NLM), quindi e' il segnale piu' fedele al
    significato originale di DE (Author Keywords) - vedi il modulo docstring.

    Se un KeywordList non ha l'attributo Owner (raro nei campioni osservati,
    ma non escluso dallo schema), le sue keyword vengono comunque incluse:
    l'assenza dell'attributo non e' un segnale che la lista sia di tipo
    diverso da NOTNLM, solo che il dato non e' dichiarato esplicitamente.

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        list[str]: keyword estratte, lista vuota se KeywordList e' assente o
        vuoto. Duplicati preservati cosi' come restituiti da PubMed (nessuna
        deduplicazione, a differenza di AU_UN/C1: qui l'ordine e le eventuali
        ripetizioni riflettono direttamente cio' che l'editore ha dichiarato).
    """
    keywords = []
    for keyword_list in article.findall("MedlineCitation/KeywordList"):
        owner = keyword_list.get("Owner")
        if owner is not None and owner != "NOTNLM":
            continue
        for keyword in keyword_list.findall("Keyword"):
            text = "".join(keyword.itertext()).strip()
            if text:
                keywords.append(text)
    return keywords


def format_di_column(article):
    """
    Colonna DI (DOI). Deriva da PubmedData/ArticleIdList/ArticleId con
    IdType="doi" (posizione piu' affidabile: presente per la quasi totalita'
    degli articoli moderni), con fallback su
    Article/ELocationID con EIdType="doi" se il primo e' assente (verificato
    che entrambi possono comparire per lo stesso articolo con lo stesso
    valore, es. PMID 42472980: ELocationID doi="10.1007/s10143-026-04405-8" -
    ArticleIdList e' preferita come fonte primaria perche' e' la posizione
    "canonica" per gli identificatori dell'articolo nello schema PubMed).

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: DOI nudo, "" se non trovato in nessuna delle due posizioni.
    """
    for article_id in article.findall("PubmedData/ArticleIdList/ArticleId"):
        if article_id.get("IdType") == "doi" and article_id.text:
            return article_id.text.strip()

    for elocation_id in article.findall("MedlineCitation/Article/ELocationID"):
        if elocation_id.get("EIdType") == "doi" and elocation_id.text:
            return elocation_id.text.strip()

    return ""


def format_dt_column(article):
    """
    Colonna DT (Document Type). Deriva da
    Article/PublicationTypeList/PublicationType, che a differenza di
    work["type"] in OpenAlex (un solo valore) puo' contenere PIU' tipi
    contemporaneamente, quasi sempre includendo il generico "Journal
    Article" (verificato su tutti i campioni analizzati).

    Sceglie il primo tipo presente in PUBMED_TYPE_TO_WOS_DT diverso da
    "Journal Article" (piu' informativo, es. "Review"/"Clinical
    Trial"/"Letter"), tradotto nel vocabolario WoS-style; se nessun tipo
    "informativo" e' presente, ricade su "Journal Article" se presente
    nella lista, altrimenti sul primo tipo grezzo cosi' com'e'.

    DEBUGGING LOG: la prima versione di questa funzione sceglieva
    semplicemente "il primo tipo diverso da Journal Article", SENZA
    controllare se fosse presente in PUBMED_TYPE_TO_WOS_DT. Riprodotto
    concretamente un caso in cui questo sceglie il tipo sbagliato: PMID
    10022014 ha PublicationTypeList = ["Journal Article", "Research Support,
    Non-U.S. Gov't", "Research Support, U.S. Gov't, Non-P.H.S."] - la
    versione precedente restituiva "Research Support, Non-U.S. Gov't" come
    DT, un'etichetta amministrativa sulla fonte di finanziamento, non un
    tipo di documento nel senso WoS del termine (l'articolo e' un normale
    "Article"). Corretto qui filtrando sui soli tipi che questo modulo sa
    interpretare come document type genuini (le chiavi di
    PUBMED_TYPE_TO_WOS_DT); un tipo non presente li' non viene piu'
    considerato "informativo" solo perche' diverso da "Journal Article".

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: valore DT mappato, "" se PublicationTypeList e' assente/vuoto.
    """
    types = [
        (pt.text or "").strip()
        for pt in article.findall("MedlineCitation/Article/PublicationTypeList/PublicationType")
        if (pt.text or "").strip()
    ]
    if not types:
        return ""

    informative = next(
        (t for t in types if t != "Journal Article" and t in PUBMED_TYPE_TO_WOS_DT),
        None,
    )
    if informative:
        return PUBMED_TYPE_TO_WOS_DT[informative]

    if "Journal Article" in types:
        return PUBMED_TYPE_TO_WOS_DT["Journal Article"]

    return PUBMED_TYPE_TO_WOS_DT.get(types[0], types[0])


def format_em_column(article):
    """
    Colonna EM (Email). Per decisione esplicita, restituisce sempre stringa
    vuota: pur essendo un'email talvolta presente in coda al testo libero di
    AffiliationInfo/Affiliation (es. PMID 42472980, "...Turkey.
    serhatyildizhan07@gmail.com."), estrarla in modo affidabile
    richiederebbe un parsing euristico del testo libero (non un campo
    strutturato dedicato), stessa scelta di scope gia' fatta per
    format_em_column in openalex_mapper.py.

    Args:
        article: elemento <PubmedArticle> (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_fu_column(article):
    """
    Colonna FU (Funding Details). Campo non popolato per questa pipeline:
    restituisce sempre stringa vuota. PubMed espone un GrantList in alcuni
    record, ma verificato empiricamente in questa sessione che e' ASSENTE
    nella maggioranza dei campioni analizzati (diversamente da MeshHeadingList
    o AuthorList, quasi sempre presenti): implementarlo avrebbe prodotto una
    colonna popolata solo sporadicamente, con beneficio incerto.

    Args:
        article: elemento <PubmedArticle> (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_fx_column(article):
    """
    Colonna FX (Funding Text). Campo non disponibile da PubMed (nessun
    equivalente testuale libero al "Funding Text" di WoS): restituisce
    sempre stringa vuota per decisione esplicita.

    Args:
        article: elemento <PubmedArticle> (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_is_column(article):
    """
    Colonna IS (Issue). Deriva da Journal/JournalIssue/Issue.

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: numero di fascicolo, "" se assente.
    """
    return (article.findtext("MedlineCitation/Article/Journal/JournalIssue/Issue") or "").strip()


def format_ji_column(article):
    """
    Colonna JI (Abbreviated Journal Name). Deriva da
    Journal/ISOAbbreviation, un'abbreviazione standardizzata GENUINA
    (es. "Lancet", "N Engl J Med", verificato sui campioni analizzati) - a
    differenza di OpenAlex, che non fornisce alcuna abbreviazione e per cui
    format_ji_column restituisce sempre "" (vedi quella funzione per il ruolo
    di JI in metatagextraction.py::SR quando vuota).

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: abbreviazione della rivista, "" se ISOAbbreviation e' assente
        (raro, ma non escluso dallo schema PubMed).
    """
    return (article.findtext("MedlineCitation/Article/Journal/ISOAbbreviation") or "").strip()


def format_id_column(article):
    """
    Colonna ID (Index/Keywords Plus). Deriva da
    MeshHeadingList/MeshHeading/DescriptorName: i termini MeSH (Medical
    Subject Headings) sono assegnati da indicizzatori NLM (umani o, per
    IndexingMethod="Automated" come sul PMID 42472980, da un processo
    automatico NLM) da un vocabolario controllato esterno all'autore - vedi
    il modulo docstring per il confronto con l'equivalente OpenAlex
    (concepts, assegnati da un classificatore proprietario diverso).

    A differenza di format_de_column, non filtra per alcun attributo: ogni
    DescriptorName viene incluso, indipendentemente da MajorTopicYN (che
    segnala solo se il termine e' un argomento "principale" dell'articolo,
    non se va incluso o escluso).

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        list[str]: termini MeSH estratti, lista vuota se MeshHeadingList e'
        assente/vuoto (comune per articoli non ancora indicizzati da NLM,
        es. preprint o pubblicazioni molto recenti).
    """
    terms = []
    for descriptor in article.findall("MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName"):
        text = "".join(descriptor.itertext()).strip()
        if text:
            terms.append(text)
    return terms


def format_la_column(article):
    """
    Colonna LA (Language). Pass-through diretto di Article/Language (codice
    a 3 lettere, es. "eng", secondo la convenzione MEDLINE/ISO 639-2) - nota
    granularita' diversa da OpenAlex (codice ISO 639-1 a 2 lettere, es. "en"):
    stesso tipo di scostamento di formato gia' segnalato in
    format_la_column di openalex_mapper.py rispetto al nome esteso usato da
    WoS (es. "English").

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: codice lingua a 3 lettere, "" se Language e' assente.
    """
    return (article.findtext("MedlineCitation/Article/Language") or "").strip()


def format_oa_column(article):
    """
    Colonna OA (Open Access). Restituisce sempre stringa vuota: stesso
    trattamento di TC (vedi format_tc_column), per lo stesso motivo
    concettuale — PubMed non e' una fonte di dati OA.

    L'EFetch non espone alcun flag di stato Open Access equivalente al
    vocabolario controllato di OpenAlex (oa_status: "gold"/"green"/"hybrid"/
    "bronze"/"closed", derivato da Unpaywall). L'unico segnale presente
    nell'XML e' ArticleId[@IdType="pmc"] (presenza del full-text su PubMed
    Central), che e' un proxy approssimativo — "PMC disponibile" non coincide
    con "Open Access" in senso Unpaywall/DOAJ: ci sono articoli OA non in PMC
    e articoli in PMC non genuinamente OA. Questa approssimazione e' stata
    valutata e rifiutata: preferibile "" coerente a un dato fuorviante.

    Args:
        article: elemento <PubmedArticle> (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_oi_column(article, sep=";"):
    """
    Colonna OI (ORCID). Deriva da
    AuthorList/Author/Identifier con attributo Source="ORCID", quando
    presente (verificato sui campioni analizzati: non tutti gli autori hanno
    un ORCID dichiarato, anche nello stesso AuthorList - es. PMID 42472980,
    dove tutti e 4 gli autori campionati hanno un ORCID, mentre altri
    campioni con autori piu' datati non ne hanno alcuno).

    A differenza di OpenAlex (dove OI e' sempre "" per assenza del dato -
    vedi openalex_mapper.py::format_oi_column), qui il dato e' effettivamente
    disponibile e viene riportato. Restituisce una stringa (non una lista,
    coerente con type_contracts.py::COLUMN_SPECS, dove OI e' STRING non
    STRING_LIST): piu' ORCID (uno per autore che li dichiara) vengono uniti
    con `sep`, stesso pattern gia' usato altrove nella codebase per colonne
    scalari multi-valore (es. metatagextraction.py::AU_UN con il parametro
    `sep`).

    Args:
        article: elemento <PubmedArticle>.
        sep: separatore usato per unire piu' ORCID in un'unica stringa.

    Returns:
        str: ORCID uniti da `sep`, "" se nessun autore ne dichiara uno.
    """
    orcids = []
    for author in _author_elements(article):
        for identifier in author.findall("Identifier"):
            if identifier.get("Source") == "ORCID" and identifier.text:
                orcids.append(identifier.text.strip())
    return sep.join(orcids)


def format_pmid_column(article):
    """
    Colonna PMID (PubMed ID). Deriva da MedlineCitation/PMID (percorso
    esplicito, NON un ".//PMID" generico - vedi il modulo docstring per il
    perche': lo stesso documento puo' contenere altri elementi <PMID> per
    articoli correlati dentro CommentsCorrectionsList).

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: PMID nudo, "" se assente (non dovrebbe verificarsi in pratica:
        ogni <PubmedArticle> restituito da EFetch ha un PMID).
    """
    return (article.findtext("MedlineCitation/PMID") or "").strip()


def format_pu_column(article):
    """
    Colonna PU (Publisher). Campo non disponibile da PubMed per questa
    pipeline: restituisce sempre stringa vuota per decisione esplicita.
    MedlineJournalInfo espone il paese di pubblicazione (Country) ma non il
    nome dell'editore.

    Args:
        article: elemento <PubmedArticle> (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_py_column(article):
    """
    Colonna PY (Publication Year). Deriva da
    Journal/JournalIssue/PubDate/Year quando presente. PubMed a volte
    riporta la data come testo libero non strutturato in MedlineDate invece
    che nei campi Year/Month/Day separati (es. intervalli di pubblicazione
    come "1998 Sep-Oct" o date stagionali "Winter 1999"): in quel caso,
    estrae il primo gruppo di 4 cifre consecutive dal testo di MedlineDate
    come fallback, invece di restituire 0 e perdere un dato comunque presente
    ma in formato diverso.

    Stessa scelta di tipo di format_py_column in openalex_mapper.py (vedi
    quella funzione per il bug PY str-vs-int documentato e risolto in questa
    sessione, non specifico di OpenAlex: la stessa classificazione INTEGER
    in type_contracts.py::COLUMN_SPECS vale per tutte le sorgenti, PubMed
    inclusa).

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        int: anno di pubblicazione, 0 se ne' Year ne' un pattern di 4 cifre
        in MedlineDate sono disponibili.
    """
    year_text = article.findtext("MedlineCitation/Article/Journal/JournalIssue/PubDate/Year")
    if year_text:
        try:
            return int(year_text.strip())
        except ValueError:
            pass

    medline_date = article.findtext("MedlineCitation/Article/Journal/JournalIssue/PubDate/MedlineDate")
    if medline_date:
        match = re.search(r"\d{4}", medline_date)
        if match:
            return int(match.group())

    return 0


def format_rp_column(article):
    """
    Colonna RP (Correspondence Address/Reprint Author). Per decisione
    esplicita, restituisce sempre stringa vuota: PubMed non espone un
    indirizzo di corrispondenza strutturato/affidabile equivalente a RP in
    WoS (stessa scelta di scope di format_rp_column in openalex_mapper.py).

    Args:
        article: elemento <PubmedArticle> (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_sc_column(article):
    """
    Colonna SC (Subject Category / Fields of Research). Campo non disponibile
    da PubMed per questa pipeline: restituisce sempre stringa vuota per
    decisione esplicita (i termini MeSH in MeshHeadingList potrebbero in
    parte sovrapporsi concettualmente, ma sono gia' rappresentati in ID -
    vedi format_id_column - e non hanno una gerarchia "categoria disciplinare"
    diretta e affidabile senza logica aggiuntiva di mappatura).

    Args:
        article: elemento <PubmedArticle> (non usato).

    Returns:
        str: sempre "".
    """
    return ""


def format_sn_column(article):
    """
    Colonna SN (ISSN). Deriva da Journal/ISSN (indipendentemente da
    IssnType="Print"/"Electronic": un singolo Journal ha al massimo un
    elemento ISSN in ciascun record EFetch, verificato sui campioni
    analizzati).

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: ISSN, "" se assente (puo' accadere per riviste non ancora
        registrate con ISSN, raro).
    """
    return (article.findtext("MedlineCitation/Article/Journal/ISSN") or "").strip()


def format_so_column(article):
    """
    Colonna SO (Journal/Source). Deriva da Journal/Title.

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: nome della rivista, "" se Title e' assente.
    """
    return (article.findtext("MedlineCitation/Article/Journal/Title") or "").strip()


def format_tc_column(article):
    """
    Colonna TC (Times Cited). PubMed non e' un indice citazionale: non
    esiste alcun conteggio di citazioni associato a un record EFetch (a
    differenza di OpenAlex, dove cited_by_count e' un campo nativo del
    work). Restituisce sempre 0, non un dato mancante recuperabile da
    un'altra posizione dello stesso XML - vedi il modulo docstring.

    Args:
        article: elemento <PubmedArticle> (non usato).

    Returns:
        int: sempre 0.
    """
    return 0


def format_ti_column(article):
    """
    Colonna TI (Title). Deriva da Article/ArticleTitle.

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: titolo dell'articolo, "" se ArticleTitle e' assente.
    """
    return "".join(
        (article.find("MedlineCitation/Article/ArticleTitle").itertext()
         if article.find("MedlineCitation/Article/ArticleTitle") is not None else [])
    ).strip()


def format_ut_column(article):
    """
    Colonna UT (Publication ID / accession number). Per PubMed coincide con
    PMID (stessa scelta gia' fatta dalla pipeline storica - vedi
    format_functions.py::format_ut_column, branch `source == 'PubMed'`:
    `publication_id = entry.get('PMID', '')`): a differenza di OpenAlex, dove
    UT e PMID sono due identificatori DISTINTI (work["id"] vs
    work["ids"]["pmid"], quest'ultimo spesso assente), PubMed non ha un
    accession number separato dal PMID stesso.

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: identico all'output di format_pmid_column(article).
    """
    return format_pmid_column(article)


def format_vl_column(article):
    """
    Colonna VL (Volume). Deriva da Journal/JournalIssue/Volume.

    Args:
        article: elemento <PubmedArticle>.

    Returns:
        str: numero di volume, "" se assente.
    """
    return (article.findtext("MedlineCitation/Article/Journal/JournalIssue/Volume") or "").strip()


def build_sr_bridge_frame(records):
    """
    Costruisce il DataFrame "ponte" da passare, senza alcuna trasformazione,
    a metatagextraction.py::SR(M). Identica a
    openalex_mapper.py::build_sr_bridge_frame (vedi quella funzione per la
    motivazione: le chiavi AU/DB/JI/SO/PY prodotte da questo modulo si
    chiamano gia' come le colonne che SR(M) si aspetta).

    Args:
        records: list[dict], record gia' prodotti da map_article_to_record.

    Returns:
        pandas.DataFrame costruito direttamente da records, una riga per
        record.
    """
    return pd.DataFrame(records)


def compute_sr_for_records(records):
    """
    Calcola SR (e SR_FULL) per un'intera collezione di record gia' mappati,
    riusando SENZA MODIFICHE metatagextraction.py::SR(M) - identica a
    openalex_mapper.py::compute_sr_for_records (vedi quella funzione per il
    perche' SR non ha un equivalente format_sr_column a livello di singolo
    record).

    Args:
        records: list[dict], record gia' mappati con almeno le chiavi AU,
            DB, JI, SO, PY.

    Returns:
        list[dict]: nuovi dict (i record in input non vengono mutati),
        ciascuno arricchito con le chiavi "SR" e "SR_FULL". Lista vuota se
        `records` e' vuota.
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

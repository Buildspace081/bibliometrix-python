from www.services import *


def _split_multivalue_cell(value):
    """
    Ricostruisce una list[str] a partire da una cella Excel contenente una
    rappresentazione "; "-separata (o ";"-separata, senza spazio) di una
    colonna multi-valore (vedi type_contracts.py::COLUMN_SPECS, STRING_LIST).

    Gestisce robustamente i casi limite prodotti da un roundtrip Excel:
    - cella vuota/NaN (tipico di pd.read_excel su una cella Excel vuota,
      che arriva come float NaN, non come stringa vuota) -> lista vuota;
    - stringa vuota o solo spazi -> lista vuota;
    - elementi vuoti generati da separatori ripetuti/spazi spuri -> scartati.

    Args:
        value: contenuto grezzo della cella cosi' come restituito da
            pd.read_excel (str, float NaN, o altro tipo scalare).

    Returns:
        list[str]: elementi ricostruiti, lista vuota se value non contiene
        dati utilizzabili.
    """
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    return [item.strip() for item in re.split(r";\s*", text) if item.strip()]


def get_data(input, database, df, reset_callback=None):
    """
    Handle the data upload and display process.
    
    Args:
        input: An object that provides user input methods.
        database: The name of the database.
        df: A DataFrame object to store the data.
        reset_callback: Function to call to reset analysis results (optional)
        
    Returns:
        A message indicating the status of the data upload.
    """
    file: list[FileInfo] | None = input.Dataset()
    
    if file is None:
        text = ui.h5("Please select a file to begin importing your data.")

    elif input.select() == "1A":
        ui.update_action_button("action_button_save", disabled=False)
        
        source = input.database()
        author = input.author()
        
        try:
            # Check if multiple files are selected
            if len(file) > 1:
                # Process multiple files
                json = process_multiple_files(file, source, author)
                df.set(pd.read_json(StringIO(json)))
                # Reset all analysis results when new dataset is loaded
                if reset_callback:
                    reset_callback()
                text = ui.p(
                    f"{database}'s files uploaded and processed successfully! "
                    f"{len(file)} files have been processed and combined. "
                    f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
                )
            else:
                # Process single file (original logic)
                type = file[0]["name"]
                json = biblio_json(file[0]["datapath"], source, type, author)
                df.set(pd.read_json(StringIO(json)))
                # Reset all analysis results when new dataset is loaded
                if reset_callback:
                    reset_callback()
                
                if type.endswith(".zip"):
                    text = ui.p(
                        f"{database}'s ZIP archive uploaded and extracted successfully! "
                        f"Multiple files have been processed and combined. "
                        f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
                    )
                else:
                    text = ui.p(
                        f"{database}'s file uploaded successfully! You can now proceed to analyze your data. "
                        f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
                    )
        except Exception as e:
            text = ui.div(
                ui.h5("Error processing file(s):", style="color: red;"),
                ui.p(str(e), style="color: red;"),
                ui.p("Please check that your files are in the correct format and try again.", style="color: gray;")
            )

    elif input.select() == "1B":
        loaded = pd.read_excel(file[0]["datapath"])

        # DEBUGGING LOG (secondo esempio di "Poor handling of missing values"
        # nel codice originale, oltre al bug PY str-vs-int): i file .xlsx non
        # possono contenere oggetti Python nativi. Un DataFrame con colonne
        # multi-valore (AU, AF, C1, CR, DE, ID, AU_UN - list[str], vedi
        # type_contracts.py::COLUMN_SPECS) scritto con df.to_excel() viene
        # serializzato da pandas con str(list) per cella (es.
        # "['Autore1', 'Autore2']"), e pd.read_excel() lo rilegge cosi' com'e':
        # una stringa contenente il repr letterale della lista, non una lista
        # vera. Verificato concretamente: senza questa conversione,
        # functions/get_relevant_authors.py va in
        # `ValueError: cannot convert float NaN to integer` perche' AU non e'
        # piu' esplodibile come lista (get_relevant_authors.py:108). Qui
        # ricostruiamo le liste dalla rappresentazione "; "-separata che il
        # nostro export di test scrive al posto del repr Python (vedi
        # standard del brief: multi-valore = stringa unica joinata con "; ").
        multivalue_columns = [
            column for column, spec in COLUMN_SPECS.items()
            if spec["type"] == ColumnType.STRING_LIST
        ]
        for column in multivalue_columns:
            if column in loaded.columns:
                loaded[column] = loaded[column].apply(_split_multivalue_cell)

        df.set(loaded)
        # Reset all analysis results when new dataset is loaded
        if reset_callback:
            reset_callback()
        text = ui.p(
            f"{database}'s file uploaded successfully! You can now proceed to analyze your data. "
            f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
        )

    else:
        text = ""

    return text

# Tesseract OCR — Developer Setup / Configurazione per sviluppatori

FreePDF Suite ships OCR as a **bundled portable binary** next to the application executable. End users should never need to install Tesseract system-wide. This document is for **developers** preparing a portable build.

---

## English

### Why this folder exists

The `tesseract/` directory at the project root holds the Tesseract OCR engine and language data. It is **not committed to Git** (binaries are ~50–200 MB). You must set it up manually before building a portable distribution with OCR support.

At runtime the app looks for Tesseract in this order:

1. `{app_root}/tesseract/tesseract.exe` (Windows) or `{app_root}/tesseract/tesseract` (Linux/macOS)
2. System `PATH` (development convenience only)

When bundled binaries are found, `pytesseract` is configured automatically and `TESSDATA_PREFIX` is set to the `tesseract/` folder.

### Expected layout

```
project_root/
  tesseract/
    tesseract.exe          # Windows (or `tesseract` on Linux/macOS)
    *.dll                  # Windows runtime libraries from the portable build
    tessdata/
      eng.traineddata
      ita.traineddata
      ...                  # other languages as needed
```

The build script copies `tesseract/` beside `FreePDFSuite.exe` when present:

```
dist/FreePDFSuite/
  FreePDFSuite.exe
  tesseract/
    tesseract.exe
    tessdata/
  config/
  assets/
```

### Windows — download and extract

1. Download a **portable or installer build** from the UB Mannheim project:  
   https://github.com/UB-Mannheim/tesseract/wiki
2. Extract or copy the contents so that **`tesseract/tesseract.exe`** exists at the project root.
3. Ensure **`tesseract/tessdata/`** contains the language files you need:
   - `eng.traineddata` — English (recommended minimum)
   - `ita.traineddata` — Italian
   - Additional `.traineddata` files from the same package or from [tessdata](https://github.com/tesseract-ocr/tessdata)

Typical Mannheim layout after copy:

- Copy `tesseract.exe` and companion DLLs into `project_root/tesseract/`
- Copy the `tessdata` folder into `project_root/tesseract/tessdata/`

### Linux / macOS (development)

Place a portable or locally built Tesseract binary at `tesseract/tesseract` with `tesseract/tessdata/` beside it. System Tesseract on `PATH` remains a fallback for local development if the folder is absent.

### Build

From the repository root:

```bash
poetry run python scripts/build.py
```

If `tesseract/` is missing, the build still succeeds but prints a note that OCR will only work when Tesseract is on `PATH`.

### Verify locally (dev)

With `tesseract/` in place:

```bash
poetry run python -c "from core.ocr_engine import check_tesseract_available, bundled_tesseract_path; print(bundled_tesseract_path()); print(check_tesseract_available())"
```

### End-user message

If neither bundled nor system Tesseract is available, the OCR dialog shows:

> Tesseract is not included in this build. Contact the developer or see docs/TESSERACT_SETUP.md.

Portable builds intended for distribution **must** include the `tesseract/` folder.

---

## Italiano

### Perché serve questa cartella

La directory `tesseract/` nella root del progetto contiene il motore OCR Tesseract e i file lingua. **Non è versionata su Git** (i binari pesano ~50–200 MB). Va preparata manualmente prima di creare una build portatile con OCR.

A runtime l'app cerca Tesseract in questo ordine:

1. `{app_root}/tesseract/tesseract.exe` (Windows) o `{app_root}/tesseract/tesseract` (Linux/macOS)
2. `PATH` di sistema (solo comodità in sviluppo)

Se trova i binari bundled, configura automaticamente `pytesseract` e imposta `TESSDATA_PREFIX` sulla cartella `tesseract/`.

### Struttura attesa

```
project_root/
  tesseract/
    tesseract.exe          # Windows (o `tesseract` su Linux/macOS)
    *.dll                  # librerie runtime Windows
    tessdata/
      eng.traineddata
      ita.traineddata
      ...
```

Lo script di build copia `tesseract/` accanto a `FreePDFSuite.exe` se presente.

### Windows — download ed estrazione

1. Scarica una build **portatile o installer** da:  
   https://github.com/UB-Mannheim/tesseract/wiki
2. Estrai o copia i file in modo che esista **`tesseract/tesseract.exe`** nella root del progetto.
3. In **`tesseract/tessdata/`** inserisci i file lingua necessari:
   - `eng.traineddata` — inglese (minimo consigliato)
   - `ita.traineddata` — italiano
   - altri `.traineddata` dal pacchetto o da [tessdata](https://github.com/tesseract-ocr/tessdata)

### Build

```bash
poetry run python scripts/build.py
```

Se `tesseract/` manca, la build completa comunque ma OCR funzionerà solo se Tesseract è nel `PATH`.

### Messaggio per l'utente finale

Se Tesseract non è disponibile né bundled né di sistema, il dialog OCR mostra:

> Tesseract non incluso in questa build. Contatta lo sviluppatore o consulta docs/TESSERACT_SETUP.md.

Le build portatili destinate agli utenti **devono** includere la cartella `tesseract/`.

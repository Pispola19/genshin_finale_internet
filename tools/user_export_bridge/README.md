# Modulo import export utente (file-only, conforme)

**Fase 1 — basso rischio:** nessun token, nessuna chiamata di rete, nessun accesso a API non documentate. L’utente (o un tool terzo autorizzato) produce un **file JSON**; questo modulo lo valida e lo trasforma nel **formato batch** già usato dalla pipeline (`data/pipeline_inbox/README.md`), pronto per `validate` / `ingest`.

## Ruolo architetturale

| Livello | Responsabilità |
|---------|----------------|
| **Fonte esterna** | Export consentito dall’utente (manuale, script personale, futuro export ufficiale se esiste). |
| **user_export_bridge** | Controllo versione, alias chiavi, opzionale riscrittura in batch pipeline. |
| **Pipeline esistente** | Unico punto di validazione forte, normalizzazione, dedup, registry. |

## Formato file in ingresso (`user_export_version`)

File JSON radice:

| Campo | Obbligatorio | Descrizione |
|-------|--------------|-------------|
| `user_export_version` | sì | Intero; attualmente supportato: **1**. |
| `origin_note` | no | Testo libero (es. «Export manuale scheda», «Tool X v0.2»). |
| `personaggi` / `characters` | no | Array di record personaggio (stessi campi del batch pipeline). |
| `armi` / `weapons` | no | Array di record arma. |
| `manufatti` / `artifacts` | no | Array di righe manufatto (set, slot, pezzo, …). |

È ammessa **una sola** famiglia di chiavi per sezione (italiano **oppure** inglese), non mescolate nella stessa sezione con significati diversi.

I record interni devono rispettare le stesse regole documentate per la pipeline (elementi, `STATS`, slot, ecc.). Il bridge applica le stesse normalizzazioni usate da `tools.pipeline.normalize` prima di scrivere l’output.

## Comando

Dalla root del progetto:

```bash
PYTHONPATH=. python3 tools/user_export_bridge/convert_to_pipeline.py \
  -i percorso/export_utente.json \
  -o data/pipeline_inbox/batch_user_export.json
```

- **`--validate-only`**: controlla e stampa esito, **non** scrive file.
- **`--source-tag`**: stringa inserita in `_meta.source` nel JSON prodotto (default: `user_file_export`).

Poi, come per ogni batch:

```bash
PYTHONPATH=. python3 tools/pipeline/cli.py validate --batch data/pipeline_inbox/batch_user_export.json
PYTHONPATH=. python3 tools/pipeline/cli.py ingest --batch data/pipeline_inbox/batch_user_export.json --source pilot-202603
```

## Esempio

Vedi `example_user_export.json` in questa cartella.

## Fase test operativa (pilot)

**Avvio operativo confermato.** Parametri concordati per questo ciclo:

| Parametro | Valore |
|-----------|--------|
| Partecipanti | **5–10** utenti |
| Durata indicativa | **7 giorni** |
| Ingest | **Centralizzato** da un reviewer (non auto-ingest da partecipanti su ambienti condivisi senza review) |
| Tag tracciamento | **`--source pilot-202603`** (uniforme per tutti gli ingest del pilot; adattare il suffisso se il ciclo è in altro mese) |
| Approvazione | **Nessun `--approve`** fino a verifica qualitativa dei dati da parte del reviewer |

Obiettivo: validare il flusso end-to-end in condizioni reali, robustezza del bridge/pipeline e feedback (facilità d’uso, errori, qualità dati) per iterazioni future.

### Prerequisiti per ogni partecipante

- Repository / ambiente con Python 3 e dipendenze progetto.
- File JSON prodotto solo da **fonte che l’utente ritiene consentita** (nessun supporto a token o scraping).
- Esecuzione **in locale** di convert → validate → ingest (o consegna file al reviewer che esegue gli stessi passi).

### Checklist per ogni round di test

1. **Convert:** `convert_to_pipeline.py -i <export.json> --validate-only` → deve terminare con `OK`.
2. **Scrittura batch:** stesso comando con `-o data/pipeline_inbox/batch_pilot_<id>.json`.
3. **Pipeline:** `cli.py validate` sul batch generato → 0 errori.
4. **Ingest (pilot):** solo il **reviewer** esegue `cli.py ingest` **senza** `--approve` fino a verifica qualitativa; sempre `--source pilot-202603` (o tag equivalente concordato per il ciclo).
5. **App:** verifica manuale su scheda personaggio / inventario che i dati attesi compaiano coerentemente (se ingest eseguito).
6. **Nota:** annotare in `origin_note` o in foglio test chi è il partecipante (solo se privacy OK) e versione formato export.

### Criteri di successo minimi

- ≥ 80% dei file forniti passano `--validate-only` al primo tentativo **oppure** dopo una correzione documentata (formato chiaro per il team).
- Nessun crash del bridge o della CLI ingest sui batch pilot.
- Feedback scritto su: difficoltà di preparazione file, campi mancanti, messaggi di errore comprensibili.

### Dati da raccogliere (feedback operativo, entro i 7 giorni)

- **Facilità d’uso:** tempo stimato per preparare l’export; punti di attrito.
- **Errori:** messaggi di validazione più frequenti (testo esatto o screenshot).
- **Qualità dati:** dopo ingest reviewer, coerenza con l’atteso in app (scheda / inventario).
- **Suggerimenti** per `user_export_version: 2` solo se emerge un formato export reale ripetibile (rispettando privacy).

### Chiusura pilot

- Decisione formale: **go** (estendere documentazione + eventuale template export) / **iterate** (revisione schema o messaggi errore) / **hold** (aspettare formato ufficiale).

## Evoluzioni future

Se in futuro esisterà un **formato export ufficiale** (schema stabile), si potrà aggiungere `user_export_version: 2` e un adapter dedicato **senza** modificare la pipeline di ingest.

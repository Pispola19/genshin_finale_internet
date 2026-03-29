# Inbox pipeline dati

Cartella di **deposito JSON** per l’integrazione controllata nel registry (`data/custom_entities.json` o `GINSHIN_DATA_DIR`). Nessun download automatico dal web: solo file curati o generati da cataloghi locali.

**Export utente (file-only, conforme):** per trasformare un JSON prodotto dall’utente da fonte consentita nel formato batch, usare `tools/user_export_bridge/` (vedi `tools/user_export_bridge/README.md`) poi `validate` / `ingest` come per ogni altro file.

## Flusso

1. **Produrre** un batch JSON (vedi formato sotto).
2. **Validare**: `PYTHONPATH=. python3 tools/pipeline/cli.py validate --batch percorso/file.json`
3. **Copiare** il file qui (o generare in loco con `export_from_catalog`).
4. **Ingest** manuale:  
   `PYTHONPATH=. python3 tools/pipeline/cli.py ingest --batch data/pipeline_inbox/nome.json --source team`  
   oppure schedulato: `make pipeline-inbox` / LaunchAgent (vedi `mac/install_launchagent_pipeline.sh`).

## Formato batch

Oggetto con chiavi opzionali `personaggi`, `armi`, `manufatti` (array). Alternativa: array di oggetti con `"_type": "personaggio" | "arma" | "manufatto"`.

### Personaggio

- Obbligatori: `nome`, `elemento` (uno di `config.ELEMENTI`), `arma` (uno di `config.TIPI_ARMA`).
- Opzionale: `base_stats` con `hp`, `atk`, `def` (numeri plausibili).

### Arma

- Obbligatori: `nome`, `tipo` (IT: Spada, Claymore, Lancia, Catalizzatore, Arco).
- Consigliati: `rarita` (1–5), `atk_base`, `stat_secondaria` (valore in `config.STATS`), `valore_stat`.

### Manufatto (riga = un pezzo)

- Obbligatori: `set`, `slot` (`fiore` | `piuma` | `sabbie` | `calice` | `corona` o alias inglesi `sands`, `flower`, …), `pezzo`.
- Opzionali: `bonus_2p`, `bonus_4p` (testo; non usati dal motore DPS, utili per tracciabilità).

## Regole di qualità

- **Nomi**: preferire grafia **italiana ufficiale** del client; la pipeline canonicalizza dove possibile (`personaggi_ufficiali` / `armi_ufficiali`).
- **Stat**: usare esattamente le stringhe ammesse in `config.STATS` (es. `ER%`, `CR%`, `ATK%`).
- **Set completi**: per `approved: true` sui set nel registry servono **tutti e 5 gli slot**; altrimenti restano `approved: false` fino al completamento.
- **Approvazione**: ingest senza `--approve` → voci `approved: false` (sicuro per produzione). Usare `--approve` solo dopo revisione.

## File generati automaticamente

- `.ingest_manifest.json` — stato ingest (non versionare; è in `.gitignore`).
- `../pipeline_logs/*.jsonl` — log append-only degli ingest.

## Comandi rapidi (root repo)

| Azione | Comando |
|--------|---------|
| Rigenera batch seed + valida | `make pipeline-starter` |
| Solo valida i seed | `make pipeline-validate-seeds` |
| Inbox runner | `make pipeline-inbox` |
| TSV → JSON manufatti | `PYTHONPATH=. python3 tools/pipeline/tsv_to_batch.py -i dati.tsv -o batch.json` |
| Export manufatti da codice | `PYTHONPATH=. python3 tools/pipeline/export_from_catalog.py manufatti --out data/pipeline_inbox/generated_manufatti.json` |

I file il cui nome inizia con `generated_` sono **saltati** dal runner predefinito; usare `inbox_runner.py --include-generated` se devono essere processati automaticamente.

---

## Modello operativo (produzione e utilizzo attivo)

Definizione operativa di default per la crescita del dataset; il capoprogetto può assegnare i nomi ai ruoli.

### Ruoli (suggeriti)

| Ruolo | Responsabilità |
|--------|------------------|
| **Maintainer cataloghi** | Aggiorna `personaggi_ufficiali.py`, `core/armi_ufficiali.py`, `core/manufatti_ufficiali.py` a ogni patch; esegue `make pipeline-starter` dopo le modifiche; apre PR/commit con diff leggibile. |
| **Producer dati** | Genera o cura JSON (export, TSV, batch manuali); esegue sempre `validate` prima del deposito in inbox; usa `--source` descrittivo in ingest (es. `team`, `patch4.x`). |
| **Reviewer / approvazione** | Controlla `custom_entities.json` dopo ingest; imposta `approved: true` sulle voci idonee (o riesegue ingest con `--approve` solo dopo verifica). Opzionale: unico referente per `--approve` in produzione. |

Chi non ha il ruolo di reviewer non usa `--approve` su ambienti condivisi.

### Priorità di espansione (ordine consigliato)

1. **Manufatti** — nuovi set e nomi pezzo impattano subito inventario e validazione UI; allineare prima il catalogo in codice, poi eventuale pipeline/registry per set extra approvati.
2. **Armi** — nuove armi per whitelist autocomplete e schede; batch JSON o aggiornamento diretto lista ufficiale + ingest se servono voci solo in registry.
3. **Personaggi** — roster più stabile; espandere quando escono nuovi personaggi giocabili, con elemento e tipo arma corretti.

Questo ordine massimizza utilità per utenti che compilano manufatti e armi quotidianamente.

### Flusso di lavoro standard (team)

1. **Patch / nuovi dati** → Maintainer aggiorna cataloghi Python **oppure** Producer crea `batch_patch_X.json` da fonti già acquisite (no web automatico).
2. `validate` su ogni batch nuovo.
3. File in `data/pipeline_inbox/` con nome versionato (`batch_YYYYMMDD_descrizione.json`).
4. `ingest` senza `--approve` (default sicuro) → revisione diff su `custom_entities.json`.
5. Dopo OK: eventuale secondo pass con `--approve` **solo** se il team ha deciso di promuovere le voci; commit del registry insieme al batch o al changelog interno.
6. Runner schedulato (`make pipeline-inbox`): utile per ambienti dove i file arrivano spesso; in produzione critica si può tenere solo ingest manuale + review.

### Cadenza

- Dopo ogni **aggiornamento contenuti gioco** rilevante: almeno `make pipeline-starter` + test rapidi app.
- **Log**: consultare `data/pipeline_logs/` in caso di contestazioni su chi/cosa ha modificato il registry.

---

## Target operativi e monitoraggio (crescita strutturata)

Obiettivi e soglie sono **decisione del capoprogetto**; qui solo esempi adattabili al carico del team.

### Parametri strategici (file versionato)

I **valori operativi effettivi** sono in **`operational_targets.json`** (stessa cartella): soglie numeriche, ordine priorità sprint e note. Il capoprogetto li modifica lì; `make pipeline-metrics` confronta la **settimana ISO corrente** (lun–dom) con quel file e stampa `[OK]/[KO]` per ciascuna soglia.

**Default attuali (orientativi, regolabili):**

| Parametro | Valore iniziale | Significato |
|-----------|-----------------|-------------|
| `min_ingests_per_calendar_week` | **2** | Almeno due ingest nella settimana. |
| `min_records_sum_per_calendar_week` | **30** | Somma record (pg + armi + righe manufatti) nella settimana. |
| `max_mean_warnings_per_ingest` | **3.0** | Media warning per ingest sopra soglia → rivedere qualità batch. |
| `min_approval_rate_percent` | **25%** | Valutato solo con **≥ 2 ingest** nella settimana; frazione con `--approve`. |
| `sprint_priority_order` | **manufatti → armi → personaggi** | Priorità quando non è definito uno sprint ad hoc. |

Per disattivare un controllo usare `null` o rimuovere la chiave dal JSON.

### Obiettivi suggeriti (soft target)

| Metrica | Esempio minimo | Nota |
|---------|----------------|------|
| Batch validati / giorno lavorativo | ≥ 1 (anche piccolo) | Meglio pochi record stabili che molti con warning. |
| Record netti / settimana | vedi `operational_targets.json` | Allineato a `min_records_sum_per_calendar_week`. |
| Ingest con `--approve` | solo dopo review | Il reviewer usa `--approve` per far salire il tasso sopra `min_approval_rate_percent`. |

I numeri vanno calibrati sulla disponibilità reale; la pipeline penalizza già la bassa qualità (validazione + warning su set incompleti).

### Monitoraggio

- **Report automatico da log** (nessun DB aggiuntivo):

  ```bash
  make pipeline-metrics
  # oppure
  PYTHONPATH=. python3 tools/pipeline/metrics_report.py --from 2026-03-01
  ```

  Output tipico: per giorno — numero ingest, percentuale con flag `approve`, totali personaggi/armi/righe manufatti, media warning per ingest, ripartizione per `--source`.

- **Tempo medio**: i log contengono timestamp assoluti; per un ciclo “deposito → approve” il team può misurare manualmente o estendere in futuro il JSONL con un campo opzionale `duration_ms` (non obbligatorio ora).

- **Tasso di approvazione** = frazione di ingest eseguiti con `--approve` (indicatore di quanto il flusso è ancora in fase “bozza” vs “promosso”).

### Priorità dinamiche

Oltre all’ordine fisso (manufatti → armi → personaggi), il team può **ricalibrare a sprint**:

- molte segnalazioni su manufatti / set mancanti → priorità su manufatti e export catalogo;
- patch armi → priorità su batch armi e whitelist;
- nessun ingest da X giorni (vedi `make pipeline-metrics`) → retroazione su producer/reviewer.

Documentare la priorità dello sprint in note interne o nel messaggio di commit del batch (`--source sprint-manufatti-202603`).

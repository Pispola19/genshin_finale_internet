# Protocollo Test Utenti (Uso Reale)

Obiettivo: validare l'uso reale del prodotto con UX congelata, intervenendo solo su criticita emerse dai test.

## 1) Regole del test

- UX/UI congelata durante il ciclo test.
- Nessun cambiamento cosmetico "a sensazione".
- Si interviene solo su:
  - bug bloccanti
  - errori funzionali riproducibili
  - criticita ad alta frequenza/severita.
- Ogni modifica post-test deve essere legata a evidenza concreta.

## 2) Setup sessione

- Durata per sessione: 20-30 minuti.
- Numero partecipanti consigliato: 3-5 (primo ciclo).
- Profilo utenti:
  - 1 principiante (primo contatto)
  - 1 intermedio
  - 1 esperto/abituale (se disponibile)
- Ambiente:
  - stessa versione app per tutti
  - stesso dataset iniziale (o dataset controllato equivalente)
  - registrazione schermo/facoltativa (con consenso)

## 3) Script moderatore (pronto all'uso)

Testo introduttivo (leggere quasi verbatim):

"Grazie per il tempo. Oggi testiamo l'app, non te. Se qualcosa non e chiaro, e un problema del prodotto, non tuo. Ti chiedo di pensare ad alta voce mentre usi l'app: cosa ti aspetti, cosa cerchi, cosa ti confonde. Non ti aiutero subito: intervengo solo se resti bloccato."

Istruzioni moderazione:

- Non guidare l'utente su dove cliccare.
- Fare domande neutre:
  - "Cosa ti aspetti qui?"
  - "Cosa faresti adesso?"
  - "Cosa ti ha fatto dubitare?"
- Se blocco > 60-90 secondi, dare aiuto minimo e segnare "blocco con assist".

Chiusura:

"Grazie. Ultima domanda: qual e stata la parte piu chiara e la parte meno chiara?"

## 4) Task da eseguire (scenario reale)

### Task 1 - Crea personaggio

Obiettivo utente: creare una scheda personaggio completa e salvarla.

Successo quando:

- personaggio salvato
- nome reperibile nella selezione

### Task 2 - Aggiungi manufatti in magazzino

Obiettivo utente: inserire almeno 3-5 pezzi in Manufatti (Archivio).

Successo quando:

- i pezzi compaiono nel Magazzino

### Task 3 - Equipaggia i 5 slot

Obiettivo utente: assegnare i pezzi al personaggio da Manufatti -> Equip personaggio.

Successo quando:

- 5 slot assegnati (fiore, piuma, sabbie, calice, corona)

### Task 4 - Usa Ottimizzazione

Obiettivo utente: leggere i suggerimenti e aprire il link verso l'azione.

Successo quando:

- utente identifica almeno 1 slot migliorabile
- usa "Vai a Manufatti (equip)" per applicare il suggerimento

### Task 5 - Verifica in Build / Rotazione / Team

Obiettivo utente: aprire una pagina analitica e avviare un calcolo con dati presenti.

Successo quando:

- utente seleziona personaggio e ottiene output senza blocco

## 5) Checklist osservazione (per ogni task)

Compilare SI/NO + note brevi:

- Capisce subito dove iniziare?
- Riconosce il prossimo passo senza aiuto?
- Usa la terminologia come previsto (Personaggio, Manufatti, Equip, Ottimizzazione)?
- Incontra un blocco?
- Recupera da errore in autonomia?
- Completa il task?

Metriche da registrare:

- tempo task (mm:ss)
- numero esitazioni (> 5 secondi)
- numero blocchi
- bisogno di aiuto (SI/NO)

## 6) Scala severita issue

- **Bloccante**: impedisce completamento task.
- **Alta**: completabile solo con aiuto o tentativi multipli.
- **Media**: confusione rilevante ma task completato.
- **Bassa**: frizione lieve, nessun impatto forte.

## 7) Template report sessione

Usa questo formato per ogni utente.

```text
Sessione ID:
Data:
Moderatore:
Profilo utente: (principiante/intermedio/esperto)

TASK 1 - Crea personaggio
- Esito: Successo / Parziale / Fallito
- Tempo:
- Blocchi:
- Note:

TASK 2 - Aggiungi manufatti
- Esito:
- Tempo:
- Blocchi:
- Note:

TASK 3 - Equip 5 slot
- Esito:
- Tempo:
- Blocchi:
- Note:

TASK 4 - Ottimizzazione -> Azione
- Esito:
- Tempo:
- Blocchi:
- Note:

TASK 5 - Build/Rotazione/Team
- Esito:
- Tempo:
- Blocchi:
- Note:

Issue emerse
1) [Severita] Titolo breve
   - Evidenza:
   - Frequenza:
   - Impatto:
   - Riproducibilita:
   - Azione proposta:

Sintesi finale
- Parte piu chiara:
- Parte meno chiara:
- Raccomandazione (fix/no-fix):
```

## 8) Debrief finale (dopo 3-5 sessioni)

Produrre un unico riepilogo:

- top issue per severita
- issue ricorrenti (>= 2 utenti)
- issue isolate (1 utente)
- fix candidati immediati (solo bloccanti/alte)
- backlog differito (medie/basse)

Decisione release:

- GO: nessun bloccante aperto
- GO con riserva: solo issue medie/basse
- NO-GO: almeno un bloccante aperto

## 9) Regola operativa post-test

Ogni modifica deve citare:

- quale issue risolve
- severita
- evidenza (sessioni coinvolte)

Senza evidenza, nessuna modifica UX.

---
name: genera-carosello
description: Prepara i prossimi caroselli di 50onrecord (storie musicali 1960–2010) e li consegna al cancello automatico. Da usare nella routine programmata o quando l'utente chiede di preparare nuovi caroselli.
---

# Genera carosello — 50onrecord

Prepari caroselli Instagram in stile fanzine sulla **storia dietro la musica** (1960–2010), in italiano.
La descrizione completa è in `docs/2026-11-01-50onrecord-design.md`: leggila la prima volta.
Il cancello automatico (`.github/workflows/gate.yml`) rifiuta tutto ciò che viola le regole: scrivere bene
qui evita scarti, ma il cancello resta l'arbitro.

## Quanti

- Esegui `python -m onrecord constraints` e conta i caroselli pronti in `queue/` (`manifest.json` con `"status": "ready"`).
- Se in coda ce ne sono **meno di 6**, prepara **3** caroselli; altrimenti **2**.

## Per ogni carosello

### 1. Scegli la storia
- Rispetta l'output di `constraints`: niente artisti in `avoid_artists`, decennio diverso da `avoid_decade`,
  preferisci `preferred_strand`, e se `need_italian` è `true` scegli un artista italiano.
- Tra un carosello e il successivo che prepari in questa stessa esecuzione: artista e decennio diversi.
- Mai una storia la cui chiave `artista|canzone|filone` è in `used_keys`.
- Filoni: `palco` (concerti, momenti dal vivo), `studio` (nascita delle canzoni), `privata` (vita privata
  **documentata**), `emozione` (significato, parole degli artisti).
- Preferisci storie per cui esistono foto libere su Wikimedia Commons (cerca il nome dell'artista su Commons).

### 2. Ricerca e verifica (regola non negoziabile)
- Ogni fatto deve essere confermato da **almeno 2 fonti indipendenti** (domini diversi; Wikipedia e le sue
  copie contano come una sola fonte). Fonti buone: enciclopedie, testate giornalistiche, biografie, interviste
  originali, siti ufficiali, archivi delle classifiche.
- **Vita privata**: solo fatti dichiarati dagli interessati o riportati da testate serie. Niente pettegolezzi,
  ipotesi, accuse non provate, dettagli su minori.
- **Niente abbellimenti**: stati d'animo, motivazioni, giudizi sul carattere solo se le fonti li riportano.
- **Mai** scrivere "da verificare", "si dice", "pare che", "sembra che", "forse", "secondo alcuni".
  Se un fatto non è verificato, toglilo o cambia storia.
- Ogni **numero** che compare sulle slide (anni, posizioni in classifica, settimane…) deve comparire nel testo
  di almeno un fatto.
- Testi delle canzoni: riassumili con parole tue; al massimo **5 parole** tra virgolette.
- Se il fatto centrale non è verificabile, scarta la storia e scegline un'altra.

### 3. Scrivi `incoming/<id>/story.json`
`<id>` = `anno-artista-canzone` in minuscolo con trattini (es. `1979-police-message-in-a-bottle`).
Segui il modello in `onrecord/models.py` e l'esempio `tests/fixtures/police_message.json`:

- `year` tra 1960 e 2010; `decade` coerente (`"60"`, `"70"`, `"80"`, `"90"`, `"00"` per 2000–2010).
- `facts`: lista di `{claim, sources: [{url, title, publisher}]}`.
- `slides`: da 6 a 8, in quest'ordine di ruoli:
  1. `cover` — `heading_cuts`: 3–5 ritagli brevi (max ~14 caratteri l'uno) che formano un titolo concreto e
     sorprendente; `marker`: nota a pennarello breve; 1–2 foto (`role` `main` e `side`).
  2. `note` — contesto: dove e quando (`heading_cuts` es. `["GERMANIA", "1979"]`), `body` max ~45 parole.
     Se il fatto principale è una dichiarazione dell'artista, metti la fonte in `source_note`
     (es. `"fonte: Sting, note di My Songs (2019)"`).
  3. slide centrali (`note`, `trio` per tre persone con `marker` `"Nome: ruolo | Nome: ruolo | Nome: ruolo"`):
     un'idea per slide, `body` max ~40 parole.
  4. `emotion` — il significato o il momento umano; `marker` = la frase da mandare a qualcuno.
  5. `result` — cosa è successo dopo.
  6. `final` — `heading_cuts: ["E TU?"]`, `marker` es. `"scrivila nei commenti ↓"`, 1 foto `side`.
- `photos`: `{query, commons_file, role}`; se conosci il nome esatto del file su Commons mettilo in `commons_file`.
- `caption_body`: 2–4 frasi da appassionato, solo fatti verificati.
- `question`: la domanda per i commenti.
- `hashtags`: al massimo 5, sempre incluso `#50onrecord`.

### 4. Controlla
Esegui `python -m onrecord build incoming/<id> --no-render`. Se segnala errori, correggi la storia.
Dopo **3** tentativi falliti sulla stessa storia, cancella la cartella e scegline un'altra.

## Consegna
- Fai commit **solo** di `incoming/` e pusha su un branch `claude/carosello-<AAAA-MM-GG>`.
- Non toccare `queue/`, `archive/`, `state.json`, i workflow o il codice.

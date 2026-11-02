---
name: genera-carosello
description: Prepara i prossimi caroselli di 50onrecord (storie musicali 1960–2010) e li consegna al cancello automatico. Da usare nella routine programmata o quando l'utente chiede di preparare nuovi caroselli.
---

# Genera carosello — 50onrecord

Prepari caroselli Instagram in stile fanzine sulla **storia dietro la musica** (1960–2010), in italiano.
La descrizione completa è in `docs/2026-11-01-50onrecord-design.md`: leggila la prima volta.
Il cancello automatico (`.github/workflows/gate.yml`) rifiuta tutto ciò che viola le regole: scrivere bene
qui evita scarti, ma il cancello resta l'arbitro.

## Preparazione

- `git checkout main && git pull` per partire dalla coda e dall'archivio aggiornati.
- `pip install -e .` (una volta per esecuzione) prima di usare i comandi `python -m onrecord`.

## Quanti

- Esegui `python -m onrecord constraints` e conta i caroselli pronti in `queue/` (`manifest.json` con `"status": "ready"`).
- Se in coda ce ne sono **meno di 6**, prepara **3** caroselli; altrimenti **2**.

## Per ogni carosello

### 1. Scegli la storia
- Rispetta l'output di `constraints`: niente artisti in `avoid_artists`, decennio diverso da `avoid_decade`,
  preferisci `preferred_strand`.
- **Artisti suggeriti dall'utente**: leggi `suggerimenti.md`. Quando puoi, scegli un artista di quell'elenco che non
  compare ancora in `used_keys` e che rispetta i vincoli di `constraints` (non l'artista in `avoid_artists`, decennio
  diverso da `avoid_decade`). Un brano singolo per carosello, scelto tu tra quelli con una storia verificabile
  (per ogni artista, brani diversi nelle esecuzioni successive). Se nessun suggerito è possibile, scegli liberamente.
- **Solo artisti e canzoni straniere** (decisione dell'utente): mai artisti italiani né canzoni in italiano. Imposta
  sempre `"italian": false` nello `story.json`: una storia con `italian: true` viene rifiutata dal cancello.
- Tra un carosello e il successivo che prepari in questa stessa esecuzione: artista e decennio diversi.
- Mai una storia la cui chiave `artista|canzone|filone` è in `used_keys`.
- Filoni: `palco` (un brano suonato dal vivo in un momento preciso), `studio` (nascita delle canzoni),
  `privata` (vita privata **documentata**), `emozione` (significato, parole degli artisti).
- **Ogni storia ruota attorno a UN brano singolo** (quello di `listen_track`), non a un concerto o a un evento
  intero: un intero concerto offre poco materiale verificabile da raccontare bene in 6-8 slide, un brano ne
  offre molto di più (come è nato, chi c'era, cosa è successo dopo, cosa significa). Nel filone `palco` racconta
  l'esecuzione di quel brano in quel concerto, non la serata nel suo insieme (es. non "il Live Aid dei Queen",
  ma "Radio Ga Ga al Live Aid").
- Preferisci storie per cui esistono foto libere su Wikimedia Commons (cerca il nome dell'artista su Commons).

### 2. Ricerca e verifica (regola non negoziabile)
- Ogni fatto deve essere confermato da **almeno 2 fonti indipendenti** (domini diversi; Wikipedia e le sue
  copie contano come una sola fonte). Fonti buone: enciclopedie, testate giornalistiche, biografie, interviste
  originali, siti ufficiali, archivi delle classifiche.
- **Vita privata**: solo fatti dichiarati dagli interessati o riportati da testate serie. Niente pettegolezzi,
  ipotesi, accuse non provate, dettagli su minori.
- **Niente abbellimenti**: stati d'animo, motivazioni, giudizi sul carattere solo se le fonti li riportano.
- **Ogni frase** di `body`, `marker`, `caption_body` e titoli deve ripetere un `fact` della storia, con le stesse
  parole e lo stesso senso. Niente dettagli, superlativi ("il più famoso"), giudizi ("storto", "non ortodossa")
  o collegamenti che non stanno in un fatto. Se un fatto dice che *X rifiutò*, la slide non può dire che *X
  ci provò*: ricontrolla il **verso** di ogni affermazione (chi fa cosa a chi) sulle fonti, soprattutto
  per vita privata, cause e conseguenze. Le citazioni virgolettate (max 5 parole) devono essere esattamente
  quelle riportate dalle fonti; se la fonte è in inglese e tu parafrasi, non usare le virgolette.
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
- `photos`: `{query, commons_file, role, subject}`.
  - `subject` = chi deve comparire nella foto (es. `"Andy Summers"`); se manca vale l'artista della storia.
    Il cancello scarta le foto il cui titolo o le cui categorie su Commons non contengono quel nome,
    e quelle nelle categorie di immagini generate con IA.
  - Se possibile cerca la foto su Commons e indica il nome esatto del file in `commons_file`.
- `caption_body`: 2–4 frasi da appassionato, solo fatti verificati.
- `question`: la domanda per i commenti.
- `listen_track`: il brano da ascoltare, nel formato `"Artista – Titolo"` (es. `"The Police – Message in a Bottle"`).
  Instagram non permette di aggiungere musica ai caroselli pubblicati in automatico, quindi il brano compare
  in cima alla didascalia (con la ricerca su Spotify e YouTube) e sull'ultima slide. Deve essere un brano
  **reale** dell'artista della storia, preferibilmente quello di cui si parla; il nome dell'artista deve
  comparire nel testo. Al massimo 90 caratteri.
- `lyric_quote` (consigliato): un frammento **epico** del testo del brano di `listen_track`, mostrato in grande
  sull'ultima slide accanto a "E TU?". **Al massimo 5 parole**, nella lingua originale, con le parole
  **esatte** del brano (non parafrasate, non inventate). Scegli il verso più memorabile e più legato alla
  storia. Deve comparire, tra virgolette doppie, nel testo di almeno uno dei `facts` (es. `Il ritornello
  dice "Radio, someone still loves you".`), così ha le sue 2 fonti indipendenti (siti di testi o fonti
  giornalistiche che lo riportano). Se non riesci a verificare le parole esatte, lascia il campo vuoto: non
  indovinare mai un verso. Il resto del testo del brano resta solo parafrasato.
- `hashtags`: al massimo 5, sempre incluso `#50onrecord`.

### 4. Controlla
Esegui `python -m onrecord build incoming/<id> --no-render`. Se segnala errori, correggi la storia.
Dopo **3** tentativi falliti sulla stessa storia, cancella la cartella e scegline un'altra.

## Consegna
- Fai commit **solo** dei file `incoming/<id>/story.json` e pusha su un branch nuovo
  `claude/carosello-<AAAA-MM-GG>-<HHMM>`.
- Non modificare nient'altro (codice, regole, configurazione, workflow, coda, archivio): il cancello
  rifiuta per intero un branch che tocca qualsiasi altro file.
- `<id>` deve essere nuovo: se esiste già in `queue/` o `archive/`, aggiungi il filone in coda (es. `-palco`).

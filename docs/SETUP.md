# Configurazione di 50onrecord

Questi passaggi si fanno **una volta sola**. Richiedono i tuoi account e le tue autorizzazioni, per questo
non possono essere automatizzati. Dopo, la pagina va avanti da sola.

Tempo stimato: circa 45 minuti.

---

## 1. Repository GitHub

1. Accedi a GitHub con il tuo account.
2. Il repository **pubblico** `50onrecord` viene creato e caricato da Claude, su tua conferma.
   Deve essere pubblico per due motivi: Instagram deve poter scaricare le slide da un indirizzo pubblico, e le
   automazioni GitHub sono gratuite solo per i repository pubblici.
   Nel repository non ci sono password né dati personali: i segreti stanno in un'area protetta (passaggio 4).

## 2. Account Instagram

1. Crea l'account **@50onrecord** dall'app Instagram. Se il nome è già preso, scegli una variante e
   aggiorna `handle` in `config.toml`.
2. Vai su **Impostazioni → Tipo di account e strumenti → Passa a un account professionale** e scegli
   **Creator**, categoria "Musicista/gruppo" o "Blog personale".
3. Imposta foto profilo e bio. Proposta di bio: *"La storia dietro la musica, 1960–2010. Una fanzine al giorno."*

## 3. App Meta per la pubblicazione

Già fatto per 50onrecord (app "50onrecord publisher", gestita dal portfolio business "50onrecord", separato da
qualsiasi altra attività). Per rifarlo da zero:

1. <https://developers.facebook.com/> → **Crea app**, caso d'uso **"Gestisci i messaggi e i contenuti su Instagram"**,
   **senza collegare portfolio esistenti**; poi collega un portfolio nuovo dedicato.
2. **Ruoli dell'app** → aggiungi l'account Instagram come **Tester di Instagram** e accetta l'invito da
   Instagram (Impostazioni → Autorizzazioni app e siti web → Inviti tester).
3. Nel caso d'uso, **"API setup with Unified login"** → passaggio 1 **Crea nuova configurazione** e selezionala.
4. Passaggio 2 **Genera token** accanto all'account. Il token è un token di "utente di sistema" e **non scade**:
   non serve nessun rinnovo. Copialo senza incollarlo in chat.

> Non condividere il token in chat o per email: va inserito solo nei segreti di GitHub (passaggio 4).

## 4. Segreti e variabili su GitHub

Nel repository: **Settings → Secrets and variables → Actions**.

**Secrets** (pulsante "New repository secret"):

| Nome | Valore |
|---|---|
| `IG_USER_ID` | l'ID dell'account Instagram (per @50onrecord: `17841411633576523`) |
| `IG_TOKEN` | il token generato al passaggio 3.4 |

**Variables** (scheda "Variables" → "New repository variable"):

| Nome | Valore |
|---|---|
| `ONRECORD_DRY_RUN` | `true` |

Con `true` il sistema fa tutto **tranne** pubblicare: è la modalità di prova.

Per controllare che il collegamento funzioni: **Actions → verifica-collegamento → Run workflow**. Deve scrivere
"Collegamento riuscito: @50onrecord" e la quota di pubblicazione. Non pubblica niente e non mostra il token.

## 5. Routine Claude

1. Vai su <https://claude.ai/code/routines> e crea una nuova routine.
2. Repository: `50onrecord`.
3. Istruzioni: *"Usa la skill genera-carosello per preparare i prossimi caroselli."*
4. Orario: ogni giorno alle **03:00** (ora italiana).
5. Accesso alla rete: **completo**, oppure una lista che includa almeno il web generale per la ricerca,
   `commons.wikimedia.org` e `upload.wikimedia.org`.

## 6. Prova e messa in onda

1. Imposta `start_date` in `config.toml` sul primo giorno di pubblicazione.
2. Lascia lavorare la routine finché la coda (`queue/`) contiene almeno **6 caroselli**.
3. Claude controlla insieme a te le slide in coda e i log della modalità di prova.
4. Quando dai il via libera, la variabile `ONRECORD_DRY_RUN` diventa `false`: da quel momento la pagina pubblica da sola.

## Se ricevi un'email da GitHub

Un'email "Run failed" su **pubblica** o **cancello** è un avviso. Le cause previste sono:
- due pubblicazioni saltate di fila;
- coda vuota;
- token Instagram in scadenza;
- un post rifiutato da Meta;
- una routine che non ha prodotto nessun carosello valido.

Apri il link nell'email: il messaggio in fondo al log spiega cosa è successo, in italiano.

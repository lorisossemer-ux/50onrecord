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

1. Vai su <https://developers.facebook.com/> e accedi con il tuo account Facebook (o creane uno).
2. **Le mie app → Crea app**, tipo **Business**, nome `50onrecord publisher`.
3. Nell'app aggiungi il prodotto **Instagram** e scegli **API setup with Instagram login**.
4. In **Generate access tokens** aggiungi l'account @50onrecord e accedi con Instagram.
   Concedi i permessi `instagram_business_basic` e `instagram_business_content_publish`.
5. Copia due valori e tienili da parte:
   - l'**ID dell'account Instagram** (un numero lungo);
   - il **token di accesso** (una stringa lunga). Vale 60 giorni, poi il sistema lo rinnova da solo ogni settimana.

> Non condividere il token in chat o per email: va inserito solo nei segreti di GitHub (passaggio 4).

## 4. Segreti e variabili su GitHub

Nel repository: **Settings → Secrets and variables → Actions**.

**Secrets** (pulsante "New repository secret"):

| Nome | Valore |
|---|---|
| `IG_USER_ID` | l'ID dell'account Instagram (passaggio 3.5) |
| `IG_TOKEN` | il token di accesso (passaggio 3.5) |
| `IG_TOKEN_EXPIRES` | la data di scadenza del token, cioè oggi + 60 giorni, nel formato `2027-01-30T00:00:00+00:00` |
| `GH_PAT` | un token GitHub "fine-grained" (vedi sotto) |

Per `GH_PAT`: **GitHub → Settings → Developer settings → Fine-grained tokens → Generate new token**.
Repository: solo `50onrecord`. Permesso: **Secrets: Read and write**. Durata: 1 anno.
Serve solo a rinnovare il token Instagram in automatico.

**Variables** (scheda "Variables" → "New repository variable"):

| Nome | Valore |
|---|---|
| `ONRECORD_DRY_RUN` | `true` |

Con `true` il sistema fa tutto **tranne** pubblicare: è la modalità di prova.

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

# 50onrecord — pagina Instagram automatica di storie musicali (1960–2010)

*Descrizione del progetto · 1 novembre 2026 · stato: da approvare*

Le scelte indicate con **[scelta di Claude]** non sono state decise dall'utente e possono essere cambiate.

---

## 1. Intento e perché

L'utente vuole una pagina Instagram che **cresca fino a generare un guadagno**, senza dover intervenire lui nella produzione.

Il modello di riferimento è @rivoluzione.della.mente (1,1 mln follower, crescita personale), che pubblica 2–3 caroselli al giorno con uno stile grafico fisso, prime slide molto forti, didascalie che chiedono di salvare e condividere, e guadagna raccogliendo contatti via DM.

50onrecord applica lo stesso meccanismo alla **musica dal 1960 al 2010**, raccontando **la storia dietro la musica**: come nascono le canzoni, i momenti sul palco e in studio, la vita privata degli artisti. È lo stesso interesse che ha fatto il successo di film come *Bohemian Rhapsody* sui Queen e del film su Michael Jackson.

La scelta distintiva: in un feed pieno di illustrazioni generate con l'IA, 50onrecord deve sembrare **fatta a mano da un appassionato**, una fanzine con foto vere fotocopiate. L'IA lavora dietro le quinte e non si vede.

## 2. Pubblico

- **Italiano.** Tutti i testi sono in italiano.
- Appassionati di musica e anche **ascoltatori comuni**, non musicisti. Niente tecnica musicale (accordi, teoria, produzione).
- Due motori: la **nostalgia** (chi ha vissuto quegli anni) e la **scoperta** (chi è più giovane e vuole sapere da dove viene la musica che ascolta).

## 3. Obiettivi, non-obiettivi, anti-obiettivi

**Obiettivi**
- Pubblicare caroselli in modo **completamente automatico**, dalla scelta della storia alla pubblicazione, senza intervento dell'utente dopo la configurazione iniziale.
- Far crescere i follower con contenuti che vengono **salvati, mandati in DM e commentati**.
- Lasciare aperte le strade per guadagnare in seguito.

**Non-obiettivi (versione 1)**
- Reels e video.
- Monetizzazione: sponsor, affiliazioni, prodotti, raccolta contatti via DM. Si progetta dopo, quando c'è un pubblico.
- Risposte automatiche a commenti e DM.
- Altre piattaforme (TikTok, Facebook).

**Anti-obiettivi**: cose che renderebbero il progetto un fallimento anche se funziona tecnicamente
- Pubblicare **fatti falsi o non verificati**, soprattutto sulla vita privata di persone reali (rischio di diffamazione).
- Usare **foto protette da copyright** o immagini generate con IA che ritraggono artisti reali.
- Un aspetto da **"contenuto IA in serie"**: illustrazioni generate, testo dal tono artificiale, stile pulito da modello preconfezionato.
- Riprodurre **testi di canzoni** oltre a brevissime citazioni di poche parole.
- Ripetere la stessa storia due volte.

## 4. Identità

**Nome:** *50onrecord* (decisione dell'utente): è il nome dell'account Instagram (@50onrecord) e del progetto. La disponibilità dell'handle su Instagram va verificata al momento della creazione dell'account.

**Stile: fanzine e collage (direzione C, scelta dall'utente).** Il riferimento visivo è il mockup "50onrecord · fanzine n.1" (6 slide su "Message in a Bottle" dei Police), nella cartella `mockup/50onrecord-n1/`.

Elementi fissi, presenti in ogni carosello:
- sfondo carta color crema con leggera grana;
- foto vere in **bianco e nero ad alto contrasto, effetto fotocopia**, leggermente ruotate e fissate con **nastro adesivo**;
- titoli fatti di **lettere ritagliate**: parole su "ritagli" di carattere e colore diversi, leggermente storti;
- **annotazioni a pennarello rosso** (carattere Permanent Marker) come unico colore costante;
- testo del racconto **a macchina da scrivere** (Special Elite) su un foglio bianco attaccato;
- piè di pagina "50ONRECORD · fanzine n.X" e numero di slide ("1/6 →"). Ogni carosello è un numero della fanzine, numerato in progressione.

**Variazione per decennio [scelta di Claude]:** la struttura resta identica, ma i ritagli dei titoli cambiano tavolozza e caratteri in base al decennio della storia (anni '60 più psichedelici, '70 caldi, '80 colori accesi, '90 grunge e sporchi, 2000 più puliti). Serve a non far sembrare la pagina solo punk.

## 5. Contenuti

**Periodo:** 1960–2010.

**Artisti:** in prevalenza **internazionali** (Beatles, Queen, Michael Jackson, Nirvana, Madonna, U2…). **[decisione dell'utente, 2 novembre 2026]** Solo artisti e canzoni straniere: niente artisti italiani né canzoni in italiano (sostituisce la scelta iniziale di circa 1 carosello su 10 italiano).

**Quattro filoni**, alternati nel calendario:
1. **Sul palco:** concerti leggendari e momenti iconici dal vivo.
2. **In studio:** come sono nate le canzoni, incidenti, intuizioni, liti.
3. **Vita privata:** amori, rivalità, tragedie, lati nascosti, **solo se documentati pubblicamente**.
4. **Emozione:** il significato di una canzone, frasi e interviste degli artisti, momenti toccanti.

**Equilibrio [scelta di Claude]:** alternare decenni, generi e filoni, in modo che non escano mai due storie consecutive dello stesso artista o dello stesso decennio.

**Struttura del carosello** (6–8 slide, massimo 10 per il limite tecnico di Instagram):
1. **Copertina:** un titolo di poche parole, concreto e sorprendente, che fa nascere una domanda. Foto principale e annotazione a pennarello.
2. **Contesto:** dove e quando ("Germania, 1979").
3. **Slide centrali:** il racconto, **un'idea per slide**, ognuna che spinge a passare alla successiva.
4. **Slide emotiva:** il significato o il momento umano, la più adatta a essere mandata a qualcuno.
5. **Esito:** cosa è successo dopo (successo, classifica, conseguenze).
6. **Ultima slide:** una domanda per i commenti ("E tu?"), l'invito a salvare e a mandarlo a qualcuno, l'annuncio "prossima uscita: fanzine n.X+1", i crediti delle foto.

**Musica (decisione dell'utente):** ogni carosello indica il brano da ascoltare (`listen_track`). L'API di Instagram non permette di aggiungere la musica del catalogo ai caroselli pubblicati in automatico: la musica è disponibile solo per i Reels. Il brano compare quindi come prima riga della didascalia, con le ricerche pronte su Spotify e YouTube, e come riga "ascolta: Artista – Titolo" sull'ultima slide. I Reels con musica restano un possibile test futuro.

**Didascalia:**
- riassunto del racconto in forma di breve articolo, in un tono caldo e da appassionato;
- invito esplicito a salvare e a mandare il post a una persona precisa;
- una domanda finale;
- **crediti delle foto** (autore e licenza) e **fonti principali**;
- chiusura fissa con l'invito a seguire la pagina;
- pochi hashtag pertinenti. **[scelta di Claude]** al massimo 5.

**Tono:** narrativo, curioso, mai sensazionalistico sui fatti. Il gancio può essere forte, ma deve essere vero.

## 6. Regole sui fatti

- Un fatto entra nel carosello **solo se confermato da almeno due fonti indipendenti e affidabili**: enciclopedie, biografie pubblicate, interviste originali, testate giornalistiche. **[scelta di Claude]**
- **Vita privata:** solo fatti dichiarati dagli interessati o riportati da fonti giornalistiche serie. Niente pettegolezzi, ipotesi, accuse non provate o dettagli su minori. Con gli artisti vivi la prudenza è massima.
- Se il fatto centrale di una storia non si può verificare, la storia **viene scartata** e si passa alla successiva.
- **Si pubblicano solo fatti verificati (decisione dell'utente).** Diciture come "da verificare", "si dice", "pare che" non devono mai comparire né sulle slide né in didascalia. Un fatto non verificato non entra nel carosello, e l'intera frase va riscritta o tolta.
- **Niente abbellimenti inventati.** Anche i dettagli di colore (stati d'animo, motivazioni, giudizi sul carattere come "per noia" o "teste dure") devono essere sostenuti dalle fonti. Altrimenti si scrive solo ciò che è documentato.
- **Fonte visibile sulla slide** quando il fatto principale viene da una dichiarazione dell'artista, per esempio "fonte: Sting, note di My Songs (2019)". Tutte le fonti vanno comunque elencate in didascalia.
- Le fonti di ogni carosello vengono **archiviate** insieme al post.
- **Testi delle canzoni:** si riassumono con parole proprie, e si citano al massimo poche parole.

## 7. Regole sulle immagini

- Solo **foto con licenza libera o di pubblico dominio**: Wikimedia Commons, Flickr con licenze Creative Commons che consentono l'uso, archivi pubblici. Le licenze che vietano l'uso commerciale (NC) o le modifiche (ND) sono escluse, perché la pagina punta a guadagnare e le foto vengono ritagliate e filtrate.
- **Le foto CC BY-SA sono ammesse [scelta di Claude].** Sono la maggioranza delle foto di concerto libere. BY-SA consente l'uso commerciale. In cambio, le slide che le contengono vanno considerate rilasciate anch'esse con licenza CC BY-SA, e questo va scritto nei crediti in didascalia: chiunque potrà riusare quelle slide citando 50onrecord. È un costo accettabile, perché il valore della pagina sta nel flusso continuo di storie, non nelle singole immagini.
- Autore e licenza di ogni foto vanno **in didascalia**. Sulle slide solo un credito sintetico nell'ultima.
- **Mai** immagini generate con IA che ritraggono artisti reali.
- **Variante senza foto:** quando non esistono foto libere adatte, il carosello si costruisce solo con titoli ritagliati, testo e grafica fanzine (biglietti, scalette, appunti), senza ritratti.
- Le foto vanno usate alla **massima risoluzione disponibile**.

## 8. Ritmo di pubblicazione

- **Fase iniziale:** 2 caroselli al giorno.
- **Fase successiva:** 1 carosello al giorno.
- **[scelta di Claude]** Passaggio automatico dopo 8 settimane. Orari 12:30 e 20:30 (ora italiana), poi solo 20:30. Gli orari andranno poi rivisti con le statistiche della pagina.

## 9. Automazione

**Principio:** dopo la configurazione iniziale l'utente non fa nulla.

Il ciclo per ogni pubblicazione:
1. **Scelta della storia** da un calendario editoriale che si rigenera da solo, rispettando l'equilibrio della sezione 5 e l'archivio, per non ripetere mai una storia.
2. **Ricerca e verifica** dei fatti secondo la sezione 6.
3. **Scrittura** di slide e didascalia secondo le sezioni 5 e 6.
4. **Ricerca delle foto** secondo la sezione 7.
5. **Impaginazione** delle slide in stile fanzine e generazione delle immagini (1080×1350, formato verticale 4:5).
6. **Controllo automatico** prima della pubblicazione: testi che non escono dalle slide, numero di slide corretto, crediti presenti, fonti presenti, nessuna ripetizione.
7. **Pubblicazione** su Instagram all'orario previsto.
8. **Archiviazione** di slide, didascalia, fonti, crediti e data.

**Se qualcosa va storto:** meglio saltare una pubblicazione che pubblicare un contenuto sbagliato. Il sistema registra l'errore e riprova con la storia successiva al turno dopo.

**Nessuna revisione umana, nemmeno all'inizio (decisione dell'utente).** La pubblicazione è automatica dal primo carosello. Di conseguenza i controlli automatici su fatti e licenze devono essere severi: nel dubbio, la storia o la foto si scarta.

**Avvisi [scelta di Claude]:** l'utente riceve un'email all'indirizzo del suo account solo quando serve: due pubblicazioni saltate di fila, coda vuota, token di Instagram scaduto o in scadenza, pubblicazione rifiutata da Meta. Nessun avviso per il funzionamento normale.

**Produzione in anticipo [scelta di Claude]:** il sistema tiene pronti alcuni caroselli in coda, così un errore non lascia vuoto un orario.

## 10. Vincoli tecnici e organizzativi

- **Progetto separato:** repository proprio, **completamente separato da Quick Pastry**, che non va toccato.
- **Esecuzione nel cloud**, programmata, così funziona anche con il computer dell'utente spento. **[scelta di Claude]** attività programmata (routine) di Claude Code nel cloud. In alternativa un servizio equivalente, se la generazione delle immagini lì non è possibile.
- **Pubblicazione** tramite le API ufficiali di Instagram per la pubblicazione di contenuti, con un account professionale (Business o Creator). Vincoli noti da verificare sulla documentazione Meta aggiornata:
  - massimo **10 elementi per carosello** via API;
  - le immagini devono essere raggiungibili da un **indirizzo web pubblico** al momento della pubblicazione, quindi serve uno spazio di hosting;
  - limite di pubblicazioni nelle 24 ore (le fonti indicano 50 o 100): ampiamente sopra il ritmo previsto.
- **Budget: solo l'abbonamento Claude dell'utente (decisione dell'utente).** Nessuna API a pagamento e nessun servizio a pagamento. Hosting delle immagini ed esecuzione devono stare nei piani gratuiti (per esempio un repository pubblico con pagine statiche gratuite). Tutto il lavoro di intelligenza artificiale (ricerca, verifica, scrittura) gira nelle routine Claude Code dell'abbonamento, e quindi consuma la quota personale e rispetta i limiti di esecuzione del piano. Conseguenze per il progetto:
  - il sistema deve produrre i caroselli **in anticipo, nei momenti di quota disponibile**, e pubblicarli dalla coda agli orari previsti. Generazione e pubblicazione sono due passaggi separati;
  - va tenuta una **coda di almeno 2–3 giorni** di caroselli pronti;
  - se la quota non basta per due caroselli al giorno, si passa prima del previsto a uno al giorno invece di pubblicare contenuti meno verificati;
  - il costruttore deve verificare i limiti attuali delle routine Claude Code (numero di esecuzioni, durata, accesso alla rete, possibilità di generare immagini con un browser headless) prima di fissare l'architettura.
- **Credenziali** (token Instagram, eventuali chiavi API): mai nel repository, solo come segreti dell'ambiente di esecuzione.
- **Grafica:** le slide si generano da modelli HTML/CSS trasformati in immagini, come nel mockup. Caratteri da Google Fonts: Anton, Alfa Slab One, Archivo Black, Playfair Display, Special Elite, Permanent Marker.

**Cose che deve fare l'utente, una volta sola**, perché richiedono il suo login o la sua autorizzazione:
- creare l'account Instagram e impostarlo come professionale;
- creare l'app sviluppatore Meta e autorizzare la pubblicazione (con una guida passo per passo);
- eventuali account gratuiti per hosting ed esecuzione nel cloud (per esempio GitHub);
- approvare il nome definitivo.

## 11. Cosa resta al costruttore

- Scelta delle librerie e della struttura del codice.
- Scelta del servizio di hosting delle immagini.
- Dettaglio dei modelli di impaginazione (quanti tipi di slide, varianti), purché rispettino lo stile della sezione 4 e il mockup.
- Formato dell'archivio e del calendario editoriale.
- Come il controllo automatico verifica che il testo non esca dalle slide.
- Rinnovo automatico del token di Instagram, che scade periodicamente.


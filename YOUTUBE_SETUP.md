# 📺 Configurazione Upload YouTube

Questa guida ti spiega come configurare l'autenticazione OAuth2 per caricare video su YouTube dalla tab Social dell'applicazione AIVideoMaker.

## 🎯 Prerequisiti

- Un account Google/Gmail
- Accesso a [Google Cloud Console](https://console.cloud.google.com/)
- L'applicazione AIVideoMaker già installata e funzionante

---

## 📝 Step 1: Crea un Progetto Google Cloud

1. Vai su [Google Cloud Console](https://console.cloud.google.com/)
2. Clicca sul menu a tendina del progetto in alto (accanto a "Google Cloud")
3. Clicca **"Nuovo progetto"**
4. Inserisci i dettagli:
   - **Nome progetto**: `AIVideoMaker YouTube`
   - **Organizzazione**: lascia come predefinito o seleziona la tua
5. Clicca **"Crea"**
6. Attendi qualche secondo che il progetto venga creato
7. Seleziona il nuovo progetto dal menu a tendina

---

## ⚙️ Step 2: Abilita YouTube Data API v3

1. Nel menu laterale, vai su **"API e servizi"** → **"Libreria"**
2. Cerca **"YouTube Data API v3"** nella barra di ricerca
3. Clicca sul risultato "YouTube Data API v3"
4. Clicca il pulsante **"Abilita"**
5. Attendi qualche secondo che l'API venga abilitata

---

## 🔐 Step 3: Configura Schermata Consenso OAuth

Prima di creare le credenziali, devi configurare la schermata di consenso OAuth:

1. Nel menu laterale, vai su **"API e servizi"** → **"Schermata consenso OAuth"**
2. Seleziona **"Esterno"** come tipo di utente (per testing personale)
3. Clicca **"Crea"**
4. Compila il form:

### Informazioni dell'app:
- **Nome app**: `AIVideoMaker`
- **Email assistenza utenti**: la tua email Gmail
- **Logo app**: (opzionale, puoi saltare)

### Informazioni di contatto sviluppatore:
- **Indirizzi email**: la tua email Gmail

5. Clicca **"Salva e continua"**

### Ambiti (Scopes):
6. Clicca **"Aggiungi o rimuovi ambiti"**
7. Nella barra di ricerca cerca: `youtube`
8. Seleziona:
   - ✅ `https://www.googleapis.com/auth/youtube.upload`
9. Clicca **"Aggiorna"**
10. Clicca **"Salva e continua"**

### Utenti test:
11. Clicca **"+ Aggiungi utenti"**
12. Inserisci la tua email Gmail (l'account che userai per caricare i video)
13. Clicca **"Aggiungi"**
14. Clicca **"Salva e continua"**

15. Nella schermata di riepilogo, clicca **"Torna alla dashboard"**

---

## 🔑 Step 4: Crea Credenziali OAuth 2.0

1. Nel menu laterale, vai su **"API e servizi"** → **"Credenziali"**
2. Clicca **"+ CREA CREDENZIALI"** in alto
3. Seleziona **"ID client OAuth"**
4. Configura:
   - **Tipo di applicazione**: **"Applicazione web"**
   - **Nome**: `AIVideoMaker Client`

### URI di reindirizzamento autorizzati:
5. Nella sezione **"URI di reindirizzamento autorizzati"**, clicca **"+ Aggiungi URI"**
6. Inserisci esattamente questo URL:
   ```
   http://localhost:8000/api/youtube/oauth2callback
   ```
7. Se usi una porta diversa, modifica `8000` con la tua porta

8. Clicca **"Crea"**

---

## 📥 Step 5: Scarica il File JSON

1. Dopo aver creato le credenziali, apparirà un popup con il client ID e il secret
2. Clicca sul pulsante **"Scarica JSON"** (o l'icona ⬇️ di download)
3. Salva il file sul tuo computer
4. **IMPORTANTE**: Rinomina il file in `client_secrets.json`
5. Sposta il file nella cartella principale di AIVideoMaker1:
   ```
   AIVideoMaker1/
   ├── app.py
   ├── client_secrets.json  ← Posiziona qui il file
   ├── uploads/
   ├── outputs/
   └── ...
   ```

---

## ✅ Step 6: Verifica la Configurazione

Il file `client_secrets.json` dovrebbe avere questa struttura:

```json
{
  "web": {
    "client_id": "123456789-abc...xyz.apps.googleusercontent.com",
    "project_id": "aivideomaker-youtube-...",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "GOCSPX-...",
    "redirect_uris": ["http://localhost:8000/api/youtube/oauth2callback"]
  }
}
```

---

## 🚀 Step 7: Avvia l'Applicazione e Testa

1. Avvia l'applicazione AIVideoMaker:
   ```bash
   cd AIVideoMaker1
   source venv/bin/activate  # Mac/Linux
   # oppure
   venv\Scripts\activate  # Windows

   python app.py
   ```

2. Apri il browser su `http://localhost:8000`

3. Vai sulla tab **"YouTube"** (icona YouTube nella barra di navigazione)

4. Clicca su **"Collega Account"**

5. Si aprirà una finestra popup con la schermata di autorizzazione Google:
   - Seleziona il tuo account Google
   - Leggi i permessi richiesti
   - Clicca **"Consenti"**

6. La finestra si chiuderà automaticamente e vedrai il tuo canale collegato!

7. Ora puoi:
   - Caricare un video (drag & drop o selezione file)
   - Compilare titolo, descrizione e tag
   - Scegliere la visibilità (Privato/Non in elenco/Pubblico)
   - Cliccare **"Carica su YouTube"**

---

## ⚠️ Note Importanti

### Modalità Test
- Quando l'app è in "Modalità test", solo gli utenti aggiunti nella sezione **"Utenti test"** possono autorizzare l'app
- Per uso pubblico, dovrai richiedere la verifica dell'app a Google (processo più lungo)

### Sicurezza
- **NON condividere mai** il file `client_secrets.json` pubblicamente
- **NON committare** `client_secrets.json` su GitHub o altri repository pubblici
- Aggiungi `client_secrets.json` al tuo `.gitignore`:
  ```
  client_secrets.json
  credentials/
  ```

### Quote API YouTube
- Google impone quote giornaliere per l'uso dell'API YouTube
- Quota default: 10.000 unità/giorno
- Un upload video costa circa 1.600 unità
- Quindi puoi caricare circa 6 video al giorno
- Se hai bisogno di più quota, richiedi un aumento nella [Google Cloud Console](https://console.cloud.google.com/iam-admin/quotas)

### Risoluzione Problemi

**Errore: "client_secrets.json non trovato"**
- Assicurati che il file sia nella cartella principale di AIVideoMaker1
- Verifica che il nome sia esattamente `client_secrets.json`

**Errore: "redirect_uri_mismatch"**
- Verifica che l'URI di reindirizzamento nelle credenziali Google corrisponda esattamente a quello dell'app
- Deve essere: `http://localhost:8000/api/youtube/oauth2callback`
- Se usi una porta diversa, aggiornala sia nelle credenziali Google che nell'app

**Errore: "Access denied"**
- Assicurati di aver aggiunto il tuo account negli "Utenti test" della schermata consenso OAuth
- Prova a revocare l'accesso su [Google Account](https://myaccount.google.com/permissions) e riautorizzare

---

## 📚 Risorse Utili

- [YouTube Data API Documentation](https://developers.google.com/youtube/v3)
- [OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Gestione App Autorizzate](https://myaccount.google.com/permissions)

---

## 🎉 Fatto!

Ora sei pronto per caricare i tuoi video direttamente su YouTube dall'applicazione AIVideoMaker!

Per domande o problemi, consulta la documentazione ufficiale di Google o contatta il supporto.

---

**Creato con ❤️ per AIVideoMaker**

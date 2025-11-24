# 🚀 Guida Deployment Produzione AIVideoMaker

Guida completa per mettere online AIVideoMaker in sicurezza.

---

## 📋 PREREQUISITI

Prima di iniziare assicurati di avere:

- [ ] **Dominio acquistato** (es. `aivideomaker.com`)
- [ ] **VPS/Server** (consigliato: DigitalOcean Droplet, AWS EC2, Hetzner)
  - **Minimo**: 2 CPU, 4GB RAM, 50GB SSD
  - **Consigliato**: 4 CPU, 8GB RAM, 100GB SSD
- [ ] **OS**: Ubuntu 22.04 LTS o superiore
- [ ] **Accesso SSH** al server con chiave pubblica/privata
- [ ] **Budget**: ~$20-40/mese (VPS + database + storage)

---

## 🔥 FASE 1: SETUP SERVER (30 min)

### 1.1 Connetti al server

```bash
ssh root@IP_SERVER
```

### 1.2 Crea utente non-root

```bash
adduser aivideomaker
usermod -aG sudo aivideomaker
su - aivideomaker
```

### 1.3 Installa dipendenze sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip nginx postgresql postgresql-contrib \
                    redis-server git curl ufw certbot python3-certbot-nginx \
                    ffmpeg supervisor
```

### 1.4 Configura firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

**Output atteso:**
```
Status: active
To                         Action      From
--                         ------      ----
OpenSSH                    ALLOW       Anywhere
Nginx Full                 ALLOW       Anywhere
```

---

## 🗄️ FASE 2: DATABASE POSTGRESQL (15 min)

### 2.1 Crea database e utente

```bash
sudo -u postgres psql

-- In PostgreSQL shell:
CREATE DATABASE aivideomaker;
CREATE USER aivideomaker WITH PASSWORD 'PASSWORD_SICURA_QUI';
GRANT ALL PRIVILEGES ON DATABASE aivideomaker TO aivideomaker;
\q
```

### 2.2 Testa connessione

```bash
psql -U aivideomaker -d aivideomaker -h localhost
# Inserisci password
# Se funziona, esci con \q
```

### 2.3 Salva DATABASE_URL

```
postgresql://aivideomaker:PASSWORD_SICURA_QUI@localhost:5432/aivideomaker
```

---

## 📦 FASE 3: DEPLOY APPLICAZIONE (20 min)

### 3.1 Clona repository

```bash
cd /home/aivideomaker
git clone https://github.com/TUO_USERNAME/AIVideoMaker.git
cd AIVideoMaker
```

### 3.2 Crea virtual environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3 Crea directory produzione

```bash
sudo mkdir -p /var/www/aivideomaker/{output,uploads,temp}
sudo chown -R aivideomaker:aivideomaker /var/www/aivideomaker
chmod 755 /var/www/aivideomaker
```

### 3.4 Crea .env.production

```bash
cp .env.production.template .env.production
nano .env.production
```

**Compila con i tuoi valori:**

```bash
# 1. Genera SECRET_KEY nuova
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 2. Incolla nel file .env.production:
SECRET_KEY=LA_TUA_SECRET_KEY_GENERATA
DATABASE_URL=postgresql://aivideomaker:PASSWORD@localhost:5432/aivideomaker
ENVIRONMENT=production
DEBUG=false

# 3. Configura Google OAuth (DEVI CREARE NUOVE CREDENZIALI!)
GOOGLE_CLIENT_ID=CLIENT_ID_PRODUZIONE
GOOGLE_CLIENT_SECRET=CLIENT_SECRET_PRODUZIONE
GOOGLE_REDIRECT_URI=https://tuodominio.com/api/v1/auth/google/callback

# 4. API Keys
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=sk_...

# 5. CORS (usa il tuo dominio reale!)
CORS_ORIGINS=https://tuodominio.com,https://www.tuodominio.com
```

### 3.5 Inizializza database

```bash
source venv/bin/activate
python -c "from app.core.database import create_tables; create_tables()"
```

**Output atteso:**
```
✅ Database tables created successfully
```

---

## 🌐 FASE 4: GOOGLE OAUTH PRODUZIONE (10 min)

**IMPORTANTE**: Le credenziali OAuth di sviluppo NON funzionano in produzione!

### 4.1 Vai a Google Cloud Console

https://console.cloud.google.com/apis/credentials

### 4.2 Crea NUOVO "ID client OAuth 2.0"

- **Tipo**: Applicazione web
- **Nome**: AIVideoMaker Production
- **Origini JavaScript autorizzate**: `https://tuodominio.com`
- **URI di reindirizzamento autorizzati**: `https://tuodominio.com/api/v1/auth/google/callback`

### 4.3 Copia credenziali in .env.production

```bash
GOOGLE_CLIENT_ID=XXX-YYY.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-ZZZZZ
GOOGLE_REDIRECT_URI=https://tuodominio.com/api/v1/auth/google/callback
```

---

## 🔒 FASE 5: NGINX + SSL (20 min)

### 5.1 Configura DNS

Prima di continuare, assicurati che il tuo dominio punti al server:

```bash
# Verifica che il DNS sia propagato:
dig +short tuodominio.com
# Deve restituire l'IP del tuo server
```

### 5.2 Crea configurazione Nginx

```bash
sudo nano /etc/nginx/sites-available/aivideomaker
```

**Contenuto:**

```nginx
# Redirect HTTP → HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name tuodominio.com www.tuodominio.com;

    # Certbot challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect a HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name tuodominio.com www.tuodominio.com;

    # SSL certificati (saranno generati da Certbot)
    ssl_certificate /etc/letsencrypt/live/tuodominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tuodominio.com/privkey.pem;

    # SSL settings sicure
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Client max body size (per upload video)
    client_max_body_size 500M;

    # Timeout per video processing
    proxy_read_timeout 600s;
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;

    # Proxy a Uvicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (se usi in futuro)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files (output video)
    location /output/ {
        alias /var/www/aivideomaker/output/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Logs
    access_log /var/log/nginx/aivideomaker_access.log;
    error_log /var/log/nginx/aivideomaker_error.log;
}
```

**IMPORTANTE**: Sostituisci **TUTTE** le occorrenze di `tuodominio.com` con il tuo dominio reale!

### 5.3 Abilita configurazione

```bash
sudo ln -s /etc/nginx/sites-available/aivideomaker /etc/nginx/sites-enabled/
sudo nginx -t
```

**Output atteso:**
```
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

**NON riavviare ancora Nginx!** Prima serve il certificato SSL.

### 5.4 Ottieni certificato SSL con Let's Encrypt

```bash
sudo certbot --nginx -d tuodominio.com -d www.tuodominio.com
```

**Segui wizard interattivo:**
1. Inserisci email
2. Accetta Terms of Service
3. Scegli "2: Redirect" per forzare HTTPS

**Output atteso:**
```
Successfully deployed certificate for tuodominio.com to /etc/nginx/sites-enabled/aivideomaker
Congratulations! You have successfully enabled HTTPS on https://tuodominio.com
```

### 5.5 Test auto-renewal

```bash
sudo certbot renew --dry-run
```

**Output atteso:**
```
Congratulations, all simulated renewals succeeded
```

---

## 🔄 FASE 6: SYSTEMD SERVICE (15 min)

### 6.1 Crea servizio systemd

```bash
sudo nano /etc/systemd/system/aivideomaker.service
```

**Contenuto:**

```ini
[Unit]
Description=AIVideoMaker FastAPI Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=aivideomaker
Group=aivideomaker
WorkingDirectory=/home/aivideomaker/AIVideoMaker
Environment="PATH=/home/aivideomaker/AIVideoMaker/venv/bin"
EnvironmentFile=/home/aivideomaker/AIVideoMaker/.env.production

# Gunicorn con Uvicorn workers
ExecStart=/home/aivideomaker/AIVideoMaker/venv/bin/gunicorn \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --timeout 600 \
    --access-logfile /var/log/aivideomaker/access.log \
    --error-logfile /var/log/aivideomaker/error.log \
    --log-level info \
    main:app

# Restart policy
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### 6.2 Crea directory log

```bash
sudo mkdir -p /var/log/aivideomaker
sudo chown aivideomaker:aivideomaker /var/log/aivideomaker
```

### 6.3 Installa Gunicorn

```bash
source /home/aivideomaker/AIVideoMaker/venv/bin/activate
pip install gunicorn
```

### 6.4 Avvia servizio

```bash
sudo systemctl daemon-reload
sudo systemctl enable aivideomaker
sudo systemctl start aivideomaker
sudo systemctl status aivideomaker
```

**Output atteso:**
```
● aivideomaker.service - AIVideoMaker FastAPI Application
     Loaded: loaded
     Active: active (running)
```

### 6.5 Testa endpoint

```bash
curl http://127.0.0.1:8000/health
```

**Output atteso:**
```json
{"status":"ok","timestamp":"2025-11-11T...","version":"1.0.0"}
```

---

## ✅ FASE 7: VERIFICA FINALE (10 min)

### 7.1 Testa da browser

Apri: `https://tuodominio.com`

**Checklist:**
- [ ] Pagina carica senza errori SSL
- [ ] Login con Google funziona
- [ ] JWT token generato correttamente
- [ ] Endpoint API `/api/v1/health` ritorna 200

### 7.2 Test sicurezza SSL

```bash
curl -I https://tuodominio.com
```

**Verifica headers:**
```
HTTP/2 200
strict-transport-security: max-age=31536000; includeSubDomains
x-frame-options: SAMEORIGIN
x-content-type-options: nosniff
```

### 7.3 Test rate limiting

```bash
for i in {1..110}; do curl -s -o /dev/null -w "%{http_code}\n" https://tuodominio.com/health; done
```

**Dopo 100 richieste deve restituire 429 (Too Many Requests).**

### 7.4 Logs real-time

```bash
# Application logs
sudo journalctl -u aivideomaker -f

# Nginx logs
sudo tail -f /var/log/nginx/aivideomaker_error.log
```

---

## 🔄 FASE 8: BACKUP E MONITORING (20 min)

### 8.1 Backup database automatico

```bash
sudo nano /usr/local/bin/backup-aivideomaker.sh
```

**Contenuto:**

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/aivideomaker"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="aivideomaker"
DB_USER="aivideomaker"

mkdir -p "$BACKUP_DIR"

# Backup database
pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/db_${TIMESTAMP}.sql.gz"

# Backup uploads
tar -czf "$BACKUP_DIR/uploads_${TIMESTAMP}.tar.gz" /var/www/aivideomaker/uploads/

# Rimuovi backup > 30 giorni
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

echo "✅ Backup completato: $TIMESTAMP"
```

**Rendi eseguibile:**
```bash
sudo chmod +x /usr/local/bin/backup-aivideomaker.sh
```

**Testa:**
```bash
sudo /usr/local/bin/backup-aivideomaker.sh
```

### 8.2 Cron job backup giornaliero

```bash
sudo crontab -e
```

**Aggiungi:**
```
# Backup AIVideoMaker ogni giorno alle 3:00 AM
0 3 * * * /usr/local/bin/backup-aivideomaker.sh >> /var/log/aivideomaker/backup.log 2>&1
```

### 8.3 Monitoring con Uptime Robot (FREE)

1. Vai su: https://uptimerobot.com/
2. Crea account gratuito
3. Aggiungi monitor:
   - **Type**: HTTPS
   - **URL**: `https://tuodominio.com/health`
   - **Interval**: 5 minuti
   - **Alert**: Email quando down > 5 minuti

---

## 🚨 TROUBLESHOOTING

### Errore: "502 Bad Gateway"

```bash
# Verifica che l'app sia running
sudo systemctl status aivideomaker

# Se non parte, leggi errori:
sudo journalctl -u aivideomaker -n 50 --no-pager

# Possibili cause:
# 1. .env.production mancante o errato
# 2. Database non raggiungibile
# 3. SECRET_KEY mancante
```

### Errore: "Database connection failed"

```bash
# Testa connessione PostgreSQL
psql -U aivideomaker -d aivideomaker -h localhost

# Verifica che DATABASE_URL sia corretto in .env.production
cat .env.production | grep DATABASE_URL
```

### Errore: "Google OAuth redirect_uri_mismatch"

**Causa**: URI di reindirizzamento non autorizzato in Google Cloud Console.

**Fix**:
1. Vai su https://console.cloud.google.com/apis/credentials
2. Modifica OAuth client ID
3. Aggiungi: `https://tuodominio.com/api/v1/auth/google/callback`
4. Salva e aspetta 5 minuti per propagazione

### Errore: "ModuleNotFoundError"

```bash
# Reinstalla dipendenze
source /home/aivideomaker/AIVideoMaker/venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart aivideomaker
```

---

## 📊 MANUTENZIONE ORDINARIA

### Aggiornamento applicazione

```bash
cd /home/aivideomaker/AIVideoMaker
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart aivideomaker
```

### Pulizia log

```bash
# Configura log rotation
sudo nano /etc/logrotate.d/aivideomaker
```

**Contenuto:**
```
/var/log/aivideomaker/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 aivideomaker aivideomaker
    sharedscripts
    postrotate
        systemctl reload aivideomaker > /dev/null 2>&1 || true
    endscript
}
```

### Monitoraggio spazio disco

```bash
# Verifica spazio disponibile
df -h

# Pulizia file temporanei vecchi
find /var/www/aivideomaker/temp -type f -mtime +7 -delete
```

---

## ✅ CHECKLIST FINALE

Prima di considerare il deployment completo:

### Sicurezza
- [ ] HTTPS forzato su tutte le route (HTTP → HTTPS redirect)
- [ ] Certificato SSL valido (Let's Encrypt)
- [ ] SECRET_KEY generata per produzione (mai riutilizzare dev!)
- [ ] DEBUG=false in .env.production
- [ ] Firewall configurato (solo 22, 80, 443)
- [ ] CORS configurato con domini specifici (no "*")
- [ ] Rate limiting attivo e testato
- [ ] Security headers configurati in Nginx

### Database
- [ ] PostgreSQL configurato (NO SQLite!)
- [ ] Backup automatici configurati (cron daily)
- [ ] Database credential sicure (password complessa)
- [ ] Connection pooling configurato

### OAuth & API
- [ ] Google OAuth credenziali PRODUZIONE create
- [ ] GOOGLE_REDIRECT_URI con dominio reale HTTPS
- [ ] OpenAI API key con rate limits verificati
- [ ] ElevenLabs API key con subscription attiva
- [ ] client_secrets.json per YouTube API (se serve)

### Infrastruttura
- [ ] Nginx come reverse proxy funzionante
- [ ] Gunicorn/Uvicorn con 4+ workers
- [ ] Systemd service abilitato e auto-restart
- [ ] Log rotation configurato
- [ ] Monitoring (Uptime Robot o simile) attivo

### Testing
- [ ] Endpoint `/health` ritorna 200
- [ ] Login con Google funziona
- [ ] Upload video funziona
- [ ] Rate limiting scatta dopo 100 req/min
- [ ] SSL Labs test: grado A o superiore (https://www.ssllabs.com/ssltest/)

---

## 📞 SUPPORTO

Se incontri problemi:

1. **Leggi log**: `sudo journalctl -u aivideomaker -n 100`
2. **Verifica Nginx**: `sudo nginx -t && sudo systemctl status nginx`
3. **Verifica DNS**: `dig +short tuodominio.com`
4. **Test locale**: `curl http://127.0.0.1:8000/health`

---

## 🎉 DEPLOYMENT COMPLETATO!

La tua applicazione AIVideoMaker è online e sicura su:

**🌐 https://tuodominio.com**

**Prossimi step consigliati:**
1. Configura Google Analytics per tracking utenti
2. Imposta Sentry per error tracking: https://sentry.io/
3. Abilita CDN per static files (Cloudflare/BunnyCDN)
4. Configura email transazionali (SendGrid/Mailgun)
5. Implementa sistema pagamenti (Stripe) se serve

---

**Autore**: Claude Code + Ettore
**Versione**: 1.0
**Data**: 2025-11-11
**Licenza**: MIT

# 🚀 Guida Deployment in Produzione - AIVideoMaker

## 📋 INDICE
1. [Prerequisiti](#prerequisiti)
2. [Configurazione .env Produzione](#configurazione-env-produzione)
3. [Setup Server](#setup-server)
4. [HTTPS con Nginx](#https-con-nginx)
5. [Database PostgreSQL](#database-postgresql)
6. [Sicurezza Finale](#sicurezza-finale)
7. [Monitoring](#monitoring)
8. [Backup](#backup)

---

## ✅ PREREQUISITI

### Server Requirements
- **OS**: Ubuntu 22.04 LTS (consigliato) o Debian 11+
- **RAM**: Minimo 2GB, consigliato 4GB+
- **CPU**: 2 cores minimo
- **Storage**: 20GB+ SSD
- **Python**: 3.11+
- **Domain**: Nome dominio puntato al server (es. `tuodominio.com`)

### Software da Installare
```bash
# Update sistema
sudo apt update && sudo apt upgrade -y

# Python e dipendenze
sudo apt install python3.11 python3.11-venv python3-pip -y

# Nginx (reverse proxy)
sudo apt install nginx -y

# Certbot (SSL/HTTPS gratuito)
sudo apt install certbot python3-certbot-nginx -y

# PostgreSQL (database production)
sudo apt install postgresql postgresql-contrib -y

# FFmpeg (video processing)
sudo apt install ffmpeg -y

# Supervisor (process manager)
sudo apt install supervisor -y
```

---

## 🔐 CONFIGURAZIONE .ENV PRODUZIONE

### 1. Copia file .env di esempio
```bash
cp .env .env.production
```

### 2. Modifica `.env.production` con questi parametri:

```bash
# ========================================
# CONFIGURAZIONE AIVIDEMAKER - PRODUCTION
# ========================================

# ==================== SECURITY ====================
# GENERA NUOVA SECRET KEY PER PRODUZIONE (DIVERSA DA DEVELOPMENT!)
# python -c "import secrets; print(secrets.token_urlsafe(64))"
SECRET_KEY=GENERA_UNA_NUOVA_SECRET_KEY_RANDOM_DI_64_CARATTERI_QUI

# ==================== ENVIRONMENT ====================
ENVIRONMENT=production
DEBUG=false  # ⚠️ IMPORTANTE: DEVE ESSERE false IN PRODUZIONE!

# ==================== DATABASE ====================
# Usa PostgreSQL in produzione (NON SQLite!)
DATABASE_URL=postgresql://aivideomaker_user:PASSWORD_SICURA_QUI@localhost:5432/aivideomaker_prod

# ==================== PATHS ====================
FFMPEG_PATH=/usr/bin/ffmpeg
FFPROBE_PATH=/usr/bin/ffprobe
OUTPUT_DIR=/var/www/aivideomaker/output
UPLOAD_DIR=/var/www/aivideomaker/uploads
TEMP_DIR=/var/www/aivideomaker/temp

# ==================== API ====================
API_PREFIX=/api/v1

# ==================== GOOGLE OAUTH 2.0 ====================
# IMPORTANTE: Aggiungi URI produzione in Google Cloud Console!
# https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_ID=TUO_CLIENT_ID_PRODUZIONE
GOOGLE_CLIENT_SECRET=TUO_CLIENT_SECRET_PRODUZIONE
GOOGLE_REDIRECT_URI=https://tuodominio.com/api/v1/auth/google/callback

# ==================== EXTERNAL API KEYS ====================
# OpenAI (per AI features)
OPENAI_API_KEY=TUA_OPENAI_KEY_PRODUZIONE

# ElevenLabs (per dubbing)
ELEVENLABS_API_KEY=TUA_ELEVENLABS_KEY_PRODUZIONE

# ==================== CORS (PRODUCTION) ====================
# ⚠️ IMPORTANTE: Specifica SOLO i domini autorizzati, NO "*"!
CORS_ORIGINS=https://tuodominio.com,https://www.tuodominio.com

# ==================== RATE LIMITING (PRODUCTION) ====================
# Rate limit più restrittivo in produzione
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=50  # Ridotto da 100

# ==================== DEMO USER (PRODUCTION) ====================
# ⚠️ DISABILITA DEMO USER IN PRODUZIONE!
DEMO_USER_ENABLED=false
```

### 3. Permessi file .env
```bash
# IMPORTANTE: Proteggi il file .env in produzione!
chmod 600 .env.production
sudo chown www-data:www-data .env.production
```

---

## 🖥️ SETUP SERVER

### 1. Crea utente dedicato
```bash
sudo useradd -m -s /bin/bash aivideomaker
sudo usermod -aG www-data aivideomaker
```

### 2. Clona repository
```bash
cd /var/www
sudo git clone https://github.com/TUO_USERNAME/AIVideoMaker.git
sudo chown -R aivideomaker:www-data AIVideoMaker
cd AIVideoMaker
```

### 3. Setup Python virtual environment
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Crea directory necessarie
```bash
sudo mkdir -p /var/www/aivideomaker/{output,uploads,temp,logs,backup}
sudo chown -R aivideomaker:www-data /var/www/aivideomaker
sudo chmod -R 755 /var/www/aivideomaker
```

### 5. Copia e configura .env
```bash
cp .env.production .env
nano .env  # Modifica con i valori corretti
chmod 600 .env
```

---

## 🔒 HTTPS CON NGINX

### 1. Configurazione Nginx

Crea file `/etc/nginx/sites-available/aivideomaker`:

```nginx
# HTTP - Redirect a HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name tuodominio.com www.tuodominio.com;

    # Certbot challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect tutto a HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name tuodominio.com www.tuodominio.com;

    # SSL Certificates (generati da Certbot)
    ssl_certificate /etc/letsencrypt/live/tuodominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tuodominio.com/privkey.pem;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # File upload size
    client_max_body_size 500M;
    client_body_timeout 300s;

    # Logs
    access_log /var/log/nginx/aivideomaker_access.log;
    error_log /var/log/nginx/aivideomaker_error.log;

    # Static files
    location /static/ {
        alias /var/www/AIVideoMaker/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Output files (video generati)
    location /output/ {
        alias /var/www/aivideomaker/output/;
        expires 7d;
        add_header Cache-Control "private";
    }

    # Proxy to Uvicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (se necessario)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

### 2. Attiva configurazione Nginx
```bash
sudo ln -s /etc/nginx/sites-available/aivideomaker /etc/nginx/sites-enabled/
sudo nginx -t  # Test configurazione
sudo systemctl restart nginx
```

### 3. Ottieni certificato SSL con Certbot
```bash
# Ottieni certificato SSL GRATUITO da Let's Encrypt
sudo certbot --nginx -d tuodominio.com -d www.tuodominio.com

# Auto-renewal (già configurato da Certbot)
sudo certbot renew --dry-run
```

---

## 🗄️ DATABASE POSTGRESQL

### 1. Crea database e utente
```bash
sudo -u postgres psql

-- In PostgreSQL console:
CREATE DATABASE aivideomaker_prod;
CREATE USER aivideomaker_user WITH ENCRYPTED PASSWORD 'PASSWORD_SICURA_QUI';
GRANT ALL PRIVILEGES ON DATABASE aivideomaker_prod TO aivideomaker_user;
\q
```

### 2. Test connessione
```bash
psql -h localhost -U aivideomaker_user -d aivideomaker_prod
```

### 3. Inizializza database
```bash
cd /var/www/AIVideoMaker
source venv/bin/activate
python -c "from app.core.database import init_db; init_db()"
```

---

## ⚙️ SUPERVISOR (PROCESS MANAGER)

### 1. Crea configurazione Supervisor

File `/etc/supervisor/conf.d/aivideomaker.conf`:

```ini
[program:aivideomaker]
command=/var/www/AIVideoMaker/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
directory=/var/www/AIVideoMaker
user=aivideomaker
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/www/aivideomaker/logs/aivideomaker.err.log
stdout_logfile=/var/www/aivideomaker/logs/aivideomaker.out.log
environment=PATH="/var/www/AIVideoMaker/venv/bin"
```

### 2. Avvia servizio
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start aivideomaker
sudo supervisorctl status aivideomaker
```

### 3. Comandi utili
```bash
# Restart applicazione
sudo supervisorctl restart aivideomaker

# Stop applicazione
sudo supervisorctl stop aivideomaker

# Visualizza logs
sudo tail -f /var/www/aivideomaker/logs/aivideomaker.out.log
```

---

## 🔐 CHECKLIST SICUREZZA FINALE

### Prima di andare in produzione, verifica:

- [ ] **DEBUG=false** in `.env`
- [ ] **SECRET_KEY** diversa da development (64+ caratteri random)
- [ ] **HTTPS** configurato e funzionante (certificato SSL valido)
- [ ] **CORS_ORIGINS** impostato solo ai domini autorizzati (NO `*`)
- [ ] **DEMO_USER_ENABLED=false** (disabilita utente demo)
- [ ] **PostgreSQL** configurato invece di SQLite
- [ ] **Firewall** attivo (UFW):
  ```bash
  sudo ufw allow 22/tcp   # SSH
  sudo ufw allow 80/tcp   # HTTP
  sudo ufw allow 443/tcp  # HTTPS
  sudo ufw enable
  ```
- [ ] **Backup automatici** configurati (vedi sotto)
- [ ] **Rate limiting** attivo e configurato
- [ ] **File `.env`** con permessi `600` (non leggibile da altri)
- [ ] **API Keys** di produzione (diverse da development)
- [ ] **Google OAuth** redirect URI aggiornato in Google Cloud Console
- [ ] **Monitoring** attivo (vedi sotto)

---

## 📊 MONITORING

### 1. Log Rotation
File `/etc/logrotate.d/aivideomaker`:

```bash
/var/www/aivideomaker/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0640 aivideomaker www-data
}
```

### 2. Monitoring Endpoint
L'app ha già endpoint di health check:
- `GET /health` - Status applicazione
- `GET /api-status` - Dettagli versione

Usa servizi esterni come:
- **UptimeRobot** (gratuito): https://uptimerobot.com
- **Pingdom**: https://www.pingdom.com
- **Better Uptime**: https://betteruptime.com

---

## 💾 BACKUP

### 1. Script Backup Database

Crea `/var/www/aivideomaker/backup/backup_db.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/www/aivideomaker/backup"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="aivideomaker_prod"
DB_USER="aivideomaker_user"

# Backup database
pg_dump -U $DB_USER -d $DB_NAME > "$BACKUP_DIR/db_backup_$DATE.sql"

# Comprimi backup
gzip "$BACKUP_DIR/db_backup_$DATE.sql"

# Mantieni solo ultimi 30 giorni
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete

echo "✅ Backup completato: db_backup_$DATE.sql.gz"
```

### 2. Rendi eseguibile e aggiungi a crontab
```bash
chmod +x /var/www/aivideomaker/backup/backup_db.sh

# Aggiungi a crontab (backup giornaliero alle 3:00 AM)
sudo crontab -e
# Aggiungi questa riga:
0 3 * * * /var/www/aivideomaker/backup/backup_db.sh >> /var/www/aivideomaker/logs/backup.log 2>&1
```

---

## 🚀 DEPLOY UPDATES

### Quando fai modifiche al codice:

```bash
cd /var/www/AIVideoMaker

# Pull modifiche da GitHub
git pull origin main

# Aggiorna dipendenze (se necessario)
source venv/bin/activate
pip install -r requirements.txt

# Restart applicazione
sudo supervisorctl restart aivideomaker

# Verifica status
sudo supervisorctl status aivideomaker
curl https://tuodominio.com/health
```

---

## ⚠️ TROUBLESHOOTING

### Server non risponde
```bash
# Verifica status Supervisor
sudo supervisorctl status aivideomaker

# Verifica logs
sudo tail -f /var/www/aivideomaker/logs/aivideomaker.err.log

# Verifica Nginx
sudo nginx -t
sudo systemctl status nginx
```

### Database connection error
```bash
# Verifica PostgreSQL attivo
sudo systemctl status postgresql

# Test connessione
psql -h localhost -U aivideomaker_user -d aivideomaker_prod
```

### Certificato SSL scaduto
```bash
# Rinnova manualmente
sudo certbot renew

# Restart Nginx
sudo systemctl restart nginx
```

---

## 📞 SUPPORTO

### Documentazione
- FastAPI: https://fastapi.tiangolo.com
- Nginx: https://nginx.org/en/docs/
- Certbot: https://certbot.eff.org/instructions
- PostgreSQL: https://www.postgresql.org/docs/

### Issues GitHub
Per problemi o domande: https://github.com/TUO_USERNAME/AIVideoMaker/issues

---

## ✅ CHECKLIST FINALE PRE-LAUNCH

Prima di rendere l'applicazione pubblica:

1. [ ] Tutti i test passano
2. [ ] Database backup configurato
3. [ ] HTTPS funzionante (A+ su SSL Labs)
4. [ ] Monitoring attivo
5. [ ] Firewall configurato
6. [ ] Log rotation attivo
7. [ ] Demo user disabilitato
8. [ ] API keys produzione configurate
9. [ ] Google OAuth redirect URI aggiornato
10. [ ] Performance test eseguiti (load testing)

---

**🎉 Buon deployment in produzione!**

Mantieni questo file aggiornato con le configurazioni specifiche del tuo server.

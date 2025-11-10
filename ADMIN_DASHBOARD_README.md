# Admin Dashboard - Guida Completa

## 🎯 Overview

Dashboard amministrativa completa per gestione utenti, statistiche, abbonamenti e analytics.

**URL:** http://localhost:8000/admin

## 📊 Features Implementate

### ✅ 1. Protezione Auth
- Accesso solo per utenti con `is_admin = True`
- Redirect automatico a /login se non autenticato
- Verifica token JWT via `/api/v1/auth/me`

### ✅ 2. Statistiche Globali
Card overview:
- Utenti totali / attivi
- Job totali
- **Ricavi totali (€)** - Somma `total_spent` di tutti gli utenti

### ✅ 3. Grafici Chart.js
- **Pie Chart**: Distribuzione abbonamenti (free/basic/pro/enterprise)
- **Bar Chart**: Job per stato (completed/failed/processing)

### ✅ 4. Gestione Utenti

**Tabella utenti con:**
- Username, Email, Data registrazione
- **Ultimo login** (`last_login_at`)
- **Subscription tier** (badge colorato)
- **Totale speso (€)**
- **Job count + azioni totali**
- Stato (attivo/inattivo)

**Filtri:**
- Search bar real-time
- Filtri: Tutti / Attivi / Inattivi / Admin

**Azioni:**
- 👁️ **View** - Modal con dettagli completi + top 10 funzionalità usate
- ✏️ **Edit** - Form inline per modificare:
  - Email, Full Name
  - Subscription tier, scadenza, totale speso
  - Stato account (attivo/disattivo)
  - Ruolo (user/admin)
  - Password (opzionale)
- 🗑️ **Delete** - Modal conferma con warning (elimina user + job + pipeline + API keys)

### ✅ 5. Export CSV
Button "Esporta CSV" per download completo utenti con:
- ID, Username, Email, Full Name
- Is Active, Is Admin
- Created At, Last Login
- Subscription Tier, Subscription End
- Total Spent, Total Jobs, Total Pipelines, Total Actions

**File:** `users_export_YYYYMMDD_HHMMSS.csv`

### ✅ 6. Usage Tracking

**Modello `UsageLog`:**
```python
- user_id: UUID
- action_type: str (chromakey, video_download, seo_analyze, etc.)
- action_details: JSON (parametri azione)
- timestamp: DateTime
- ip_address: str
- user_agent: str
```

**Helper function:**
```python
from app.core.usage_tracker import track_action

track_action(
    db=db,
    user_id=current_user.id,
    action_type='chromakey',
    action_details={'job_id': job_id, 'quality': 'high'},
    request=request  # Opzionale, per IP e user agent
)
```

**Tracking implementato in:**
- ✅ `/chromakey/process` (chromakey.py)
- 🔄 TODO altri endpoints: video_download, seo, youtube, transcription, etc.

**Pattern per aggiungere tracking:**
1. Importa: `from app.core.usage_tracker import track_action`
2. Dopo creazione job, aggiungi:
   ```python
   track_action(db, user_id, 'action_type', {'details': 'value'}, request)
   ```

### ✅ 7. Modal System
Sostituiti tutti `alert()` e `confirm()` con modal eleganti:
- `showSuccess(message)` - Verde
- `showError(message)` - Rosso
- `showWarning(message)` - Rosa
- `showInfo(message)` - Blu
- `showConfirm(message, onConfirm, onCancel)` - Cyan

### ✅ 8. Subscription System (Skeleton)

**Campi User:**
- `subscription_tier`: free | basic | pro | enterprise
- `subscription_start`: DateTime
- `subscription_end`: DateTime
- `total_spent`: Decimal (EUR)

**Stripe Service** (`app/services/stripe_service.py`):
- `create_checkout_session()` - Crea pagamento
- `handle_webhook_event()` - Gestisce eventi Stripe
- `cancel_subscription()` - Cancella abbonamento
- `get_subscription_status()` - Stato subscription

**TODO implementazione completa:**
1. `pip install stripe`
2. Aggiungi in `.env`:
   ```
   STRIPE_SECRET_KEY=sk_test_xxx
   STRIPE_PUBLISHABLE_KEY=pk_test_xxx
   STRIPE_WEBHOOK_SECRET=whsec_xxx
   ```
3. Crea Price IDs in Stripe Dashboard per ogni tier
4. Implementa webhook route in `main.py`
5. Testa con Stripe CLI: `stripe listen --forward-to localhost:8000/stripe/webhook`

### ✅ 9. Email Notifications (Skeleton)

**Email Service** (`app/services/email_service.py`):
- `send_welcome_email()` - Dopo registrazione
- `send_subscription_expiry_warning()` - 7 giorni prima scadenza
- `send_subscription_expired_email()` - Giorno scadenza
- `send_payment_successful_email()` - Conferma pagamento
- `send_payment_failed_email()` - Pagamento fallito

**Scheduled task:**
```python
async def check_expiring_subscriptions()
```
Esegue check giornaliero e invia email warning.

**TODO implementazione completa:**
1. `pip install fastapi-mail`
2. Configura SMTP in `.env`:
   ```
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your@email.com
   SMTP_PASSWORD=your_app_password
   SMTP_FROM_EMAIL=noreply@yourapp.com
   ```
3. Crea template HTML email
4. Schedula task con APScheduler:
   ```python
   from apscheduler.schedulers.asyncio import AsyncIOScheduler

   scheduler = AsyncIOScheduler()
   scheduler.add_job(check_expiring_subscriptions, 'cron', hour=9)
   scheduler.start()
   ```

## 🗄️ Database Migration

**Script:** `migrate_db_subscription.py`

Esegui dopo update modelli:
```bash
python migrate_db_subscription.py
```

Crea:
- Colonne `subscription_*` e `total_spent` in `users`
- Tabella `usage_logs`

## 🚀 Deploy Production

1. **Proteggi endpoint admin:**
   - Aggiungi rate limiting
   - Abilita HTTPS only
   - Log accessi admin

2. **Email setup:**
   - Usa SendGrid/Mailgun in production
   - Template professionali
   - Tracking email aperture

3. **Stripe setup:**
   - Usa live keys (non test)
   - Webhook signature validation
   - Gestione errori robusto

4. **Monitoring:**
   - Log tutti i cambiamenti admin
   - Alert su azioni critiche (delete user, change admin)
   - Backup database frequenti

## 📝 API Endpoints

### Admin Routes (prefix: `/api/v1/admin`)

| Method | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/users` | Lista utenti con statistiche |
| GET | `/users/{id}` | Dettagli utente completi |
| PATCH | `/users/{id}` | Modifica utente |
| DELETE | `/users/{id}` | Elimina utente |
| GET | `/stats` | Statistiche sistema |
| GET | `/users/export/csv` | Export CSV utenti |

**Auth:** Tutti richiedono `Authorization: Bearer <token>` con `is_admin=True`

## 🎨 Personalizzazione

### Colori Tier
Modifica in CSS:
```css
.badge.free { background: #e0e0e0; }
.badge.basic { background: #4facfe; }
.badge.pro { background: #f093fb; }
.badge.enterprise { background: #38ef7d; }
```

### Pricing
Modifica in `app/services/stripe_service.py`:
```python
PRICING = {
    'basic': {'price': 9.99, 'limits': {'videos_per_month': 100}},
    # ...
}
```

### Chart Colors
Modifica in `admin_dashboard.html`:
```javascript
backgroundColor: ['#e0e0e0', '#4facfe', '#f093fb', '#38ef7d']
```

## 🐛 Troubleshooting

**Error: "Admin privileges required"**
- Soluzione: Promovi utente a admin con `promote_admin.py`

**Export CSV non funziona**
- Verifica token JWT valido
- Check permessi is_admin nel database

**Modal non appare**
- Verifica FontAwesome caricato
- Check console browser per errori JS

## 📈 Metriche Importanti

Monitora:
- **Conversion rate**: free → paid subscribers
- **Churn rate**: Cancellazioni subscription / Totale subscribers
- **Average Revenue Per User (ARPU)**: Ricavi / Utenti attivi
- **Most used features**: Da usage_logs per prioritizzare sviluppo
- **User lifetime**: Tempo medio dall'iscrizione a churn

## 🔐 Security Best Practices

1. **Never log sensitive data** (password, payment info)
2. **Audit log** per tutte le azioni admin
3. **Two-factor auth** per account admin
4. **IP whitelist** per accesso admin (opzionale)
5. **Session timeout** ridotto per admin
6. **CSRF protection** su form edit/delete

## 📚 Next Steps

1. Implementa Stripe completamente
2. Setup email service con template
3. Aggiungi grafici temporali (registrazioni per mese)
4. Analytics avanzato (funnel conversion, cohort analysis)
5. Dashboard user (non-admin) con loro statistiche
6. API usage limits per tier
7. Integrazione Stripe billing portal
8. Export PDF report statistiche

---

**Creato:** 2025-11-10
**Versione:** 1.0
**Author:** AIVideoMaker Team

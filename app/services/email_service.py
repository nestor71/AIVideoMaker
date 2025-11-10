"""
Email Service - Gestione invio email
====================================
SKELETON per email notifications (subscription expiry, welcome, etc.)

TODO per implementazione completa:
1. pip install fastapi-mail
2. Configurare SMTP server in .env (Gmail, SendGrid, Mailgun, etc.)
3. Creare template HTML per email
4. Schedulare task periodici per check scadenze
"""

from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path

# NOTE: fastapi-mail non ancora installato
# from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
# from app.core.config import settings


class EmailService:
    """
    Servizio per invio email notifications

    Email da inviare:
    - Welcome email (dopo registrazione)
    - Subscription expiry warning (7 giorni prima)
    - Subscription expired (giorno scadenza)
    - Payment successful (dopo pagamento)
    - Payment failed (pagamento fallito)
    """

    # TODO: Configurare connection
    # conf = ConnectionConfig(
    #     MAIL_USERNAME=settings.smtp_username,
    #     MAIL_PASSWORD=settings.smtp_password,
    #     MAIL_FROM=settings.smtp_from_email,
    #     MAIL_PORT=settings.smtp_port,
    #     MAIL_SERVER=settings.smtp_server,
    #     MAIL_STARTTLS=True,
    #     MAIL_SSL_TLS=False,
    #     USE_CREDENTIALS=True
    # )
    # fm = FastMail(conf)

    @staticmethod
    async def send_welcome_email(user_email: str, username: str):
        """
        Invia email di benvenuto dopo registrazione

        Args:
            user_email: Email utente
            username: Username per personalizzazione
        """
        # TODO: Implementare
        # html = f"""
        # <h1>Benvenuto {username}!</h1>
        # <p>Grazie per esserti registrato su AIVideoMaker.</p>
        # <p>Inizia a creare video professionali con AI!</p>
        # <a href="https://myapp.com/dashboard">Vai alla Dashboard</a>
        # """
        #
        # message = MessageSchema(
        #     subject="Benvenuto su AIVideoMaker!",
        #     recipients=[user_email],
        #     body=html,
        #     subtype="html"
        # )
        #
        # await EmailService.fm.send_message(message)
        pass

    @staticmethod
    async def send_subscription_expiry_warning(
        user_email: str,
        username: str,
        days_left: int,
        tier: str
    ):
        """
        Invia alert scadenza subscription (7 giorni prima)

        Args:
            user_email: Email utente
            username: Username
            days_left: Giorni rimanenti
            tier: Tier abbonamento corrente
        """
        # TODO: Implementare
        # html = f"""
        # <h1>Ciao {username},</h1>
        # <p>Il tuo abbonamento <strong>{tier.upper()}</strong> scadrà tra <strong>{days_left} giorni</strong>.</p>
        # <p>Rinnova ora per continuare a usare tutte le funzionalità premium!</p>
        # <a href="https://myapp.com/billing">Rinnova Abbonamento</a>
        # """
        #
        # message = MessageSchema(
        #     subject=f"⚠️ Il tuo abbonamento scade tra {days_left} giorni",
        #     recipients=[user_email],
        #     body=html,
        #     subtype="html"
        # )
        #
        # await EmailService.fm.send_message(message)
        pass

    @staticmethod
    async def send_subscription_expired_email(
        user_email: str,
        username: str,
        tier: str
    ):
        """
        Invia notifica subscription scaduta

        Args:
            user_email: Email utente
            username: Username
            tier: Tier scaduto
        """
        # TODO: Implementare
        pass

    @staticmethod
    async def send_payment_successful_email(
        user_email: str,
        username: str,
        amount: float,
        tier: str,
        invoice_url: str
    ):
        """
        Invia conferma pagamento

        Args:
            user_email: Email utente
            username: Username
            amount: Importo pagato
            tier: Tier acquistato
            invoice_url: Link fattura Stripe
        """
        # TODO: Implementare
        pass

    @staticmethod
    async def send_payment_failed_email(
        user_email: str,
        username: str,
        retry_date: datetime
    ):
        """
        Invia notifica pagamento fallito

        Args:
            user_email: Email utente
            username: Username
            retry_date: Data prossimo tentativo
        """
        # TODO: Implementare
        pass


# ==================== SCHEDULED TASKS ====================

async def check_expiring_subscriptions():
    """
    Task periodico per check subscription in scadenza

    Da schedulare con APScheduler o Celery:
    - Esegui ogni giorno alle 9:00
    - Trova utenti con subscription_end tra 7 giorni
    - Invia email warning

    Example:
        ```python
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            check_expiring_subscriptions,
            'cron',
            hour=9,
            minute=0
        )
        scheduler.start()
        ```
    """
    from app.core.database import SessionLocal
    from app.models.user import User

    db = SessionLocal()

    # Trova subscriptions che scadono tra 7 giorni
    target_date = datetime.utcnow() + timedelta(days=7)
    users = db.query(User).filter(
        User.subscription_end.between(
            target_date.date(),
            (target_date + timedelta(days=1)).date()
        ),
        User.subscription_tier != 'free'
    ).all()

    for user in users:
        await EmailService.send_subscription_expiry_warning(
            user.email,
            user.username,
            days_left=7,
            tier=user.subscription_tier
        )

    db.close()

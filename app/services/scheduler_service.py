"""
Scheduler Service - Gestione job programmati con APScheduler
=============================================================
Servizio singleton per schedulare registrazioni screen in futuro
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Servizio singleton per gestione scheduler

    Usa APScheduler in background per eseguire job programmati.
    Ogni job schedulato viene salvato nel database (ScheduledJob)
    e tracciato in APScheduler.
    """

    _instance: Optional['SchedulerService'] = None
    _scheduler: Optional[BackgroundScheduler] = None

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Inizializza scheduler (solo prima volta)"""
        if self._scheduler is None:
            self._initialize_scheduler()

    def _initialize_scheduler(self):
        """Configura APScheduler"""
        jobstores = {
            'default': MemoryJobStore()
        }

        executors = {
            'default': ThreadPoolExecutor(max_workers=5)
        }

        job_defaults = {
            'coalesce': True,  # Se job si accumula, esegui solo l'ultimo
            'max_instances': 1,  # Max 1 istanza per job
            'misfire_grace_time': 300  # 5 minuti di tolleranza se in ritardo
        }

        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )

        logger.info("APScheduler inizializzato")

    def start(self):
        """Avvia scheduler (chiamato all'avvio app)"""
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
            logger.info("APScheduler avviato")

    def shutdown(self):
        """Ferma scheduler (chiamato alla chiusura app)"""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("APScheduler fermato")

    def schedule_job(
        self,
        job_id: str,
        func: Callable,
        run_date: datetime,
        **kwargs
    ) -> str:
        """
        Schedula job per esecuzione futura

        Args:
            job_id: ID univoco job (UUID del ScheduledJob)
            func: Funzione da eseguire
            run_date: Quando eseguire
            **kwargs: Argomenti da passare alla funzione

        Returns:
            ID job in APScheduler

        Raises:
            ValueError: Se run_date è nel passato
        """
        if run_date <= datetime.utcnow():
            raise ValueError("run_date deve essere nel futuro")

        if not self._scheduler:
            raise RuntimeError("Scheduler non inizializzato")

        # Schedula job
        job = self._scheduler.add_job(
            func=func,
            trigger='date',
            run_date=run_date,
            id=job_id,
            kwargs=kwargs,
            replace_existing=True
        )

        logger.info(f"Job schedulato: {job_id} per {run_date}")
        return job.id

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancella job schedulato

        Args:
            job_id: ID job da cancellare

        Returns:
            True se cancellato, False se non trovato
        """
        if not self._scheduler:
            return False

        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"Job cancellato: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Job {job_id} non trovato: {e}")
            return False

    def get_job(self, job_id: str):
        """Ottieni job schedulato"""
        if not self._scheduler:
            return None
        return self._scheduler.get_job(job_id)

    def get_all_jobs(self):
        """Ottieni tutti job schedulati"""
        if not self._scheduler:
            return []
        return self._scheduler.get_jobs()

    @property
    def is_running(self) -> bool:
        """Verifica se scheduler è attivo"""
        return self._scheduler is not None and self._scheduler.running


# Singleton globale
scheduler_service = SchedulerService()

"""
Admin Routes
============
Route per amministrazione sistema (admin-only)
Gestione utenti, statistiche, configurazione
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, EmailStr, field_serializer
from datetime import datetime
import csv
import io

from app.core.database import get_db
from app.core.security import require_admin, get_password_hash
from app.models.user import User
from app.models.job import Job, JobStatus
from app.models.pipeline import Pipeline
from app.models.api_key import APIKey
from app.models.usage_log import UsageLog

router = APIRouter()


# ==================== Pydantic Schemas ====================

class UserListResponse(BaseModel):
    """Schema per lista utenti"""
    id: UUID
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login_at: Optional[datetime]
    subscription_tier: str
    subscription_end: Optional[datetime]
    total_spent: float
    total_jobs: int
    total_pipelines: int
    total_actions: int

    @field_serializer('id')
    def serialize_id(self, value: UUID) -> str:
        return str(value)

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    """Schema dettagliato utente"""
    id: UUID
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]

    # Subscription
    subscription_tier: str
    subscription_start: Optional[datetime]
    subscription_end: Optional[datetime]
    total_spent: float

    # Statistiche
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_pipelines: int
    total_api_keys: int
    total_actions: int
    most_used_features: dict

    @field_serializer('id')
    def serialize_id(self, value: UUID) -> str:
        return str(value)

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """Schema per aggiornamento utente"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    password: Optional[str] = None

    # Subscription fields
    subscription_tier: Optional[str] = None
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    total_spent: Optional[float] = None


class SystemStatsResponse(BaseModel):
    """Schema per statistiche sistema"""
    total_users: int
    active_users: int
    admin_users: int
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    processing_jobs: int
    total_pipelines: int
    total_api_keys: int


# ==================== Routes ====================

@router.get("/users", response_model=List[UserListResponse])
async def list_all_users(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    is_admin: Optional[bool] = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Lista TUTTI gli utenti del sistema

    **Richiede privilegi admin.**

    Query parameters:
    - **skip**: Numero utenti da saltare (pagination, default: 0)
    - **limit**: Numero massimo utenti (default: 100)
    - **is_active**: Filtra per utenti attivi/disattivi (opzionale)
    - **is_admin**: Filtra per admin/non-admin (opzionale)

    Returns:
    - Lista utenti con statistiche base (job count, pipeline count)
    """
    query = db.query(User)

    # Filtri opzionali
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    if is_admin is not None:
        query = query.filter(User.is_admin == is_admin)

    users = query.offset(skip).limit(limit).all()

    # Arricchisci con statistiche
    result = []
    for user in users:
        total_jobs = db.query(Job).filter(Job.user_id == user.id).count()
        total_pipelines = db.query(Pipeline).filter(Pipeline.user_id == user.id).count()
        total_actions = db.query(UsageLog).filter(UsageLog.user_id == user.id).count()

        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at,
            "subscription_tier": user.subscription_tier,
            "subscription_end": user.subscription_end,
            "total_spent": float(user.total_spent) if user.total_spent else 0.0,
            "total_jobs": total_jobs,
            "total_pipelines": total_pipelines,
            "total_actions": total_actions
        })

    return result


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_details(
    user_id: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Ottieni dettagli completi di un utente

    **Richiede privilegi admin.**

    - **user_id**: ID dell'utente da consultare

    Returns:
    - Dettagli utente completi con statistiche approfondite
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utente non trovato"
        )

    # Statistiche dettagliate
    total_jobs = db.query(Job).filter(Job.user_id == user.id).count()
    completed_jobs = db.query(Job).filter(
        Job.user_id == user.id,
        Job.status == JobStatus.COMPLETED
    ).count()
    failed_jobs = db.query(Job).filter(
        Job.user_id == user.id,
        Job.status == JobStatus.FAILED
    ).count()
    total_pipelines = db.query(Pipeline).filter(Pipeline.user_id == user.id).count()
    total_api_keys = db.query(APIKey).filter(APIKey.user_id == user.id).count()
    total_actions = db.query(UsageLog).filter(UsageLog.user_id == user.id).count()

    # Funzionalità più utilizzate
    usage_stats = db.query(
        UsageLog.action_type,
        func.count(UsageLog.id).label('count')
    ).filter(
        UsageLog.user_id == user.id
    ).group_by(
        UsageLog.action_type
    ).order_by(
        func.count(UsageLog.id).desc()
    ).limit(10).all()

    most_used_features = {action: count for action, count in usage_stats}

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login_at": user.last_login_at,
        "subscription_tier": user.subscription_tier,
        "subscription_start": user.subscription_start,
        "subscription_end": user.subscription_end,
        "total_spent": float(user.total_spent) if user.total_spent else 0.0,
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "total_pipelines": total_pipelines,
        "total_api_keys": total_api_keys,
        "total_actions": total_actions,
        "most_used_features": most_used_features
    }


@router.patch("/users/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: str,
    update_data: UserUpdateRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Modifica utente

    **Richiede privilegi admin.**

    - **user_id**: ID dell'utente da modificare

    Campi modificabili:
    - **email**: Nuova email
    - **full_name**: Nome completo
    - **is_active**: Attiva/disattiva utente
    - **is_admin**: Promuovi/rimuovi privilegi admin
    - **password**: Nuova password (verrà hashata)

    ⚠️ **Attenzione:**
    - Non puoi disattivare te stesso
    - Non puoi rimuovere i tuoi privilegi admin se sei l'unico admin
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utente non trovato"
        )

    # Protezioni
    if str(user.id) == str(admin_user.id):
        if update_data.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Non puoi disattivare te stesso"
            )

        if update_data.is_admin is False:
            # Verifica se ci sono altri admin
            other_admins = db.query(User).filter(
                User.is_admin == True,
                User.id != admin_user.id
            ).count()

            if other_admins == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Non puoi rimuovere i tuoi privilegi admin: sei l'unico admin"
                )

    # Aggiorna campi
    if update_data.email is not None:
        # Verifica email unica
        existing = db.query(User).filter(
            User.email == update_data.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email già in uso"
            )
        user.email = update_data.email

    if update_data.full_name is not None:
        user.full_name = update_data.full_name

    if update_data.is_active is not None:
        user.is_active = update_data.is_active

    if update_data.is_admin is not None:
        user.is_admin = update_data.is_admin

    if update_data.password is not None:
        user.hashed_password = get_password_hash(update_data.password)

    # Update subscription fields
    if update_data.subscription_tier is not None:
        user.subscription_tier = update_data.subscription_tier

    if update_data.subscription_start is not None:
        user.subscription_start = update_data.subscription_start

    if update_data.subscription_end is not None:
        user.subscription_end = update_data.subscription_end

    if update_data.total_spent is not None:
        user.total_spent = update_data.total_spent

    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    # Ritorna dettagli aggiornati
    return await get_user_details(str(user.id), admin_user, db)


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Elimina utente

    **Richiede privilegi admin.**

    - **user_id**: ID dell'utente da eliminare

    ⚠️ **ATTENZIONE - Azione irreversibile:**
    - Elimina l'utente
    - Elimina TUTTI i suoi job
    - Elimina TUTTE le sue pipeline
    - Elimina TUTTE le sue API keys

    **Protezioni:**
    - Non puoi eliminare te stesso
    - Non puoi eliminare l'ultimo admin

    Returns:
    - Messaggio conferma con conteggio risorse eliminate
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utente non trovato"
        )

    # Protezione: non puoi eliminare te stesso
    if str(user.id) == str(admin_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Non puoi eliminare te stesso"
        )

    # Protezione: non puoi eliminare l'ultimo admin
    if user.is_admin:
        other_admins = db.query(User).filter(
            User.is_admin == True,
            User.id != user_id
        ).count()

        if other_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Non puoi eliminare l'ultimo admin del sistema"
            )

    # Conta risorse prima di eliminare
    jobs_count = db.query(Job).filter(Job.user_id == user.id).count()
    pipelines_count = db.query(Pipeline).filter(Pipeline.user_id == user.id).count()
    api_keys_count = db.query(APIKey).filter(APIKey.user_id == user.id).count()

    # Elimina (cascade delete gestito da SQLAlchemy relationships)
    db.delete(user)
    db.commit()

    return {
        "success": True,
        "message": f"Utente '{user.username}' eliminato con successo",
        "deleted_resources": {
            "jobs": jobs_count,
            "pipelines": pipelines_count,
            "api_keys": api_keys_count
        }
    }


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Ottieni statistiche sistema

    **Richiede privilegi admin.**

    Returns:
    - Conteggi utenti (totali, attivi, admin)
    - Conteggi job (totali, completati, falliti, in elaborazione)
    - Conteggi pipeline
    - Conteggi API keys
    """
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users = db.query(User).filter(User.is_admin == True).count()

    total_jobs = db.query(Job).count()
    completed_jobs = db.query(Job).filter(Job.status == JobStatus.COMPLETED).count()
    failed_jobs = db.query(Job).filter(Job.status == JobStatus.FAILED).count()
    processing_jobs = db.query(Job).filter(Job.status == JobStatus.PROCESSING).count()

    total_pipelines = db.query(Pipeline).count()
    total_api_keys = db.query(APIKey).count()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "admin_users": admin_users,
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "processing_jobs": processing_jobs,
        "total_pipelines": total_pipelines,
        "total_api_keys": total_api_keys
    }


@router.get("/users/export/csv")
async def export_users_csv(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Esporta tutti gli utenti in formato CSV

    **Richiede privilegi admin.**

    Returns:
        CSV file con tutti gli utenti e statistiche

    CSV Columns:
        - ID, Username, Email, Full Name, Is Active, Is Admin
        - Created At, Last Login, Subscription Tier, Subscription End
        - Total Spent, Total Jobs, Total Pipelines, Total Actions
    """
    # Ottieni tutti gli utenti
    users = db.query(User).all()

    # Crea CSV in memoria
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'ID', 'Username', 'Email', 'Full Name', 'Is Active', 'Is Admin',
        'Created At', 'Last Login', 'Subscription Tier', 'Subscription End',
        'Total Spent (EUR)', 'Total Jobs', 'Total Pipelines', 'Total Actions'
    ])

    # Dati
    for user in users:
        total_jobs = db.query(Job).filter(Job.user_id == user.id).count()
        total_pipelines = db.query(Pipeline).filter(Pipeline.user_id == user.id).count()
        total_actions = db.query(UsageLog).filter(UsageLog.user_id == user.id).count()

        writer.writerow([
            str(user.id),
            user.username,
            user.email,
            user.full_name or '',
            'Yes' if user.is_active else 'No',
            'Yes' if user.is_admin else 'No',
            user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else '',
            user.last_login_at.strftime('%Y-%m-%d %H:%M:%S') if user.last_login_at else 'Never',
            user.subscription_tier,
            user.subscription_end.strftime('%Y-%m-%d') if user.subscription_end else '',
            float(user.total_spent) if user.total_spent else 0.0,
            total_jobs,
            total_pipelines,
            total_actions
        ])

    # Reset stream position
    output.seek(0)

    # Return CSV as download
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=users_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )

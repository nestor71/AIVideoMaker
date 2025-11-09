"""
User Settings Routes
====================
API per salvare/caricare impostazioni utente
Supporto multi-utente con isolamento per user_id
"""

from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_serializer
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.user_settings import UserSettings, DEFAULT_SETTINGS

router = APIRouter()


# ==================== Pydantic Schemas ====================

class SettingsResponse(BaseModel):
    """Schema risposta settings"""
    id: UUID
    user_id: UUID
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_serializer('id', 'user_id')
    def serialize_uuid(self, value: UUID) -> str:
        """Serializza UUID come stringa"""
        return str(value)

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    """Schema per aggiornamento settings (parziale o completo)"""
    settings: Dict[str, Any]


# ==================== Helper Functions ====================

def deep_merge(base: dict, update: dict) -> dict:
    """
    Merge ricorsivo di dizionari (deep merge)

    Esempio:
        base = {"a": {"b": 1, "c": 2}}
        update = {"a": {"c": 3, "d": 4}}
        result = {"a": {"b": 1, "c": 3, "d": 4}}
    """
    result = base.copy()

    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


# ==================== Routes ====================

@router.get("/settings", response_model=SettingsResponse)
async def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ottieni impostazioni utente corrente

    - Se l'utente non ha impostazioni salvate, ritorna le impostazioni di default
    - Richiede JWT token
    """
    user_settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()

    # Se non esistono settings, creali con valori di default
    if not user_settings:
        user_settings = UserSettings(
            user_id=current_user.id,
            settings=DEFAULT_SETTINGS.copy()
        )
        db.add(user_settings)
        db.commit()
        db.refresh(user_settings)

    return user_settings


@router.post("/settings", response_model=SettingsResponse)
async def save_user_settings(
    settings_data: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Salva/Aggiorna impostazioni utente (MERGE intelligente)

    - Se l'utente non ha settings, li crea partendo da DEFAULT
    - Se l'utente ha già settings, fa MERGE con i nuovi (non sovrascrive tutto)
    - Supporta aggiornamenti parziali (es. solo chromakey.threshold)
    - Richiede JWT token

    **Esempio 1 - Aggiornamento parziale:**
    ```json
    {
      "settings": {
        "chromakey": {
          "threshold": 50
        }
      }
    }
    ```
    Risultato: aggiorna solo chromakey.threshold, mantiene tutto il resto

    **Esempio 2 - Aggiornamento completo:**
    ```json
    {
      "settings": {
        "chromakey": {...},
        "logo": {...},
        "translation": {...}
      }
    }
    ```
    """
    user_settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()

    if not user_settings:
        # Prima volta: crea settings partendo da DEFAULT e applica modifiche
        merged_settings = deep_merge(DEFAULT_SETTINGS.copy(), settings_data.settings)

        user_settings = UserSettings(
            user_id=current_user.id,
            settings=merged_settings
        )
        db.add(user_settings)
    else:
        # Aggiorna: merge con settings esistenti
        user_settings.settings = deep_merge(
            user_settings.settings,
            settings_data.settings
        )

    db.commit()
    db.refresh(user_settings)

    return user_settings


@router.delete("/settings", status_code=status.HTTP_200_OK)
async def reset_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ripristina impostazioni di default

    - Elimina tutte le impostazioni personalizzate
    - Ricrea settings con valori di default
    - Richiede JWT token

    **Utile per:**
    - Button "Ripristina Impostazioni Default" nelle Settings
    - Reset completo dello stato UI
    """
    user_settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()

    if user_settings:
        # Reset: sovrascrivi con DEFAULT
        user_settings.settings = DEFAULT_SETTINGS.copy()
        db.commit()
        db.refresh(user_settings)
    else:
        # Non esistevano settings: creali con DEFAULT
        user_settings = UserSettings(
            user_id=current_user.id,
            settings=DEFAULT_SETTINGS.copy()
        )
        db.add(user_settings)
        db.commit()
        db.refresh(user_settings)

    return {
        "message": "Impostazioni ripristinate ai valori di default",
        "settings": user_settings.settings
    }


@router.patch("/settings/{setting_path:path}", response_model=SettingsResponse)
async def update_single_setting(
    setting_path: str,
    value: Any,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Aggiorna una singola impostazione via path notation

    - **setting_path**: Path con dot notation (es. "chromakey.threshold")
    - **value**: Nuovo valore (qualsiasi tipo JSON)
    - Richiede JWT token

    **Esempi:**
    ```
    PATCH /settings/chromakey.threshold
    Body: 50

    PATCH /settings/youtube.privacy
    Body: "public"

    PATCH /settings/ui_state.current_tab
    Body: "metadata"
    ```

    **Utile per:**
    - Auto-save su singolo campo modificato
    - Performance (invio solo campo cambiato, non tutto il JSON)
    """
    user_settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()

    if not user_settings:
        user_settings = UserSettings(
            user_id=current_user.id,
            settings=DEFAULT_SETTINGS.copy()
        )
        db.add(user_settings)

    # Naviga nel dizionario usando il path
    keys = setting_path.split('.')
    current_dict = user_settings.settings

    # Naviga fino al penultimo livello
    for key in keys[:-1]:
        if key not in current_dict:
            current_dict[key] = {}
        current_dict = current_dict[key]

    # Aggiorna il valore finale
    current_dict[keys[-1]] = value

    db.commit()
    db.refresh(user_settings)

    return user_settings

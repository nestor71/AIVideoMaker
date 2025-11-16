"""
Pipeline Routes
===============
Route per sistema AUTO - Pipeline orchestration
Esegue più job in sequenza automaticamente
"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.pipeline import Pipeline, PipelineStatus
from app.pipelines.orchestrator import PipelineOrchestrator
from app.services.file_service import cleanup_upload_folder

router = APIRouter()


# ==================== Pydantic Schemas ====================

class PipelineStep(BaseModel):
    """Schema per singolo step pipeline"""
    step_number: int
    job_type: str  # "chromakey", "translation", "thumbnail", "youtube_upload"
    enabled: bool = True
    parameters: dict  # Parametri specifici per ogni job type


class PipelineCreateRequest(BaseModel):
    """Schema per creazione pipeline"""
    name: str
    description: Optional[str] = None
    steps: List[PipelineStep]
    stop_on_error: bool = True  # Ferma pipeline se uno step fallisce


class PipelineResponse(BaseModel):
    """Schema per risposta pipeline"""
    pipeline_id: str
    name: str
    status: str
    current_step: int
    total_steps: int
    enabled_steps_count: int
    progress: int
    message: str


class PipelineExecuteResponse(BaseModel):
    """Schema per risposta esecuzione pipeline"""
    pipeline_id: str
    status: str
    message: str
    estimated_duration: Optional[str] = None


class PipelineDetailResponse(BaseModel):
    """Schema dettagliato pipeline"""
    pipeline_id: str
    name: str
    description: Optional[str]
    status: str
    current_step: int
    total_steps: int
    steps: List[dict]
    stop_on_error: bool
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    result: Optional[dict]
    error_message: Optional[str]


# ==================== Helper Functions ====================

def create_pipeline(
    user: User,
    request: PipelineCreateRequest,
    db: Session
) -> Pipeline:
    """Crea pipeline nel database"""
    pipeline = Pipeline(
        user_id=user.id,
        name=request.name,
        description=request.description,
        steps=[step.dict() for step in request.steps],
        total_steps=len(request.steps),
        stop_on_error=request.stop_on_error
    )

    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)

    return pipeline


def execute_pipeline_task(pipeline_id: str, db: Session):
    """Task background per esecuzione pipeline"""
    # Converti pipeline_id da stringa a UUID per query SQLAlchemy
    try:
        pipeline_uuid = UUID(pipeline_id)
    except (ValueError, AttributeError):
        return  # UUID non valido, esci silenziosamente

    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_uuid).first()

    if not pipeline:
        return

    try:
        # 🗑️ CLEANUP: Elimina vecchi file dalla cartella upload mantenendo solo quelli necessari
        cleanup_result = cleanup_upload_folder(pipeline, db)

        # Aggiorna status
        pipeline.status = PipelineStatus.RUNNING
        pipeline.current_step = 0
        db.commit()

        # Crea orchestrator
        orchestrator = PipelineOrchestrator(db, settings)

        # Callback per aggiornare progresso
        def progress_callback(step_number: int, progress: int):
            pipeline.current_step = step_number
            db.commit()

        # Esegui pipeline
        result = orchestrator.execute_pipeline(pipeline, progress_callback)

        # Aggiorna pipeline
        if result.get("success"):
            pipeline.status = PipelineStatus.COMPLETED
        else:
            pipeline.status = PipelineStatus.FAILED
            pipeline.error = result.get("error")

        pipeline.result = result
        db.commit()

    except Exception as e:
        pipeline.status = PipelineStatus.FAILED
        pipeline.error = str(e)
        db.commit()


# ==================== Routes ====================

@router.post("/create", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_new_pipeline(
    request: PipelineCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crea nuova pipeline AUTO

    **Pipeline** = Sequenza di step eseguiti automaticamente.

    Ogni step può essere:
    - **chromakey**: Elaborazione green screen
    - **translation**: Traduzione video
    - **thumbnail**: Generazione thumbnail
    - **youtube_upload**: Upload su YouTube

    **Caratteristiche**:
    - Output di uno step → Input del successivo
    - Ogni step può essere enabled/disabled
    - stop_on_error: se true, ferma tutto al primo errore

    **Esempio**:
    ```json
    {
      "name": "Video Completo AUTO",
      "steps": [
        {
          "step_number": 1,
          "job_type": "chromakey",
          "enabled": true,
          "parameters": {
            "foreground_video": "video.mp4",
            "background_video": "sfondo.mp4"
          }
        },
        {
          "step_number": 2,
          "job_type": "thumbnail",
          "enabled": true,
          "parameters": {
            "source_type": "video_frame",
            "video_path": "@previous",  # Usa output step precedente
            "prompt": "Thumbnail accattivante"
          }
        },
        {
          "step_number": 3,
          "job_type": "youtube_upload",
          "enabled": false,  # Disabilitato - verrà saltato
          "parameters": {
            "video_path": "@step1",  # Usa output step 1
            "title": "Il mio video"
          }
        }
      ],
      "stop_on_error": true
    }
    ```

    **Parametri speciali**:
    - `"@previous"`: Usa output dello step precedente
    - `"@step1"`, `"@step2"`: Usa output di step specifico

    Richiede JWT token.
    """
    # Validazioni
    if len(request.steps) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline deve avere almeno 1 step"
        )

    # Verifica job_type validi (tutti i servizi disponibili)
    valid_job_types = [
        "chromakey", "translation", "thumbnail", "youtube_upload",
        "logo_overlay", "transcription", "metadata_extraction", "seo_metadata"
    ]
    for step in request.steps:
        if step.job_type not in valid_job_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"job_type non valido: {step.job_type}. Validi: {valid_job_types}"
            )

    # Crea pipeline
    pipeline = create_pipeline(current_user, request, db)

    enabled_count = len(pipeline.enabled_steps)

    return {
        "pipeline_id": str(pipeline.id),
        "name": pipeline.name,
        "status": pipeline.status.value,
        "current_step": pipeline.current_step,
        "total_steps": pipeline.total_steps,
        "enabled_steps_count": enabled_count,
        "progress": 0,
        "message": f"Pipeline creata con {enabled_count} step abilitati su {pipeline.total_steps} totali"
    }


@router.post("/{pipeline_id}/execute", response_model=PipelineExecuteResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_pipeline(
    pipeline_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Esegui pipeline AUTO

    Avvia esecuzione pipeline in background.

    **Processo**:
    1. Esegue step 1 (se enabled)
    2. Passa output step 1 → input step 2
    3. Esegue step 2 (se enabled)
    4. E così via...

    **Nota**: Solo step con `enabled: true` vengono eseguiti.

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Converti pipeline_id da stringa a UUID
    try:
        pipeline_uuid = UUID(pipeline_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline ID non valido"
        )

    # Verifica pipeline esiste e appartiene all'utente
    pipeline = db.query(Pipeline).filter(
        Pipeline.id == pipeline_uuid,
        Pipeline.user_id == current_user.id
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline non trovata"
        )

    # Verifica status
    if pipeline.status == PipelineStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pipeline già in esecuzione"
        )

    # Conta step abilitati
    enabled_count = len(pipeline.enabled_steps)
    if enabled_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline non ha step abilitati. Abilita almeno 1 step."
        )

    # Avvia esecuzione in background
    background_tasks.add_task(execute_pipeline_task, str(pipeline.id), db)

    # Stima durata (molto approssimativa)
    estimated_minutes = enabled_count * 3  # ~3 min per step

    return {
        "pipeline_id": str(pipeline.id),
        "status": "accepted",
        "message": f"Pipeline avviata con {enabled_count} step abilitati. Usa GET /pipelines/{pipeline_id} per monitorare.",
        "estimated_duration": f"~{estimated_minutes} minuti"
    }


@router.get("/{pipeline_id}", response_model=PipelineDetailResponse)
async def get_pipeline(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ottieni dettagli pipeline

    - **pipeline_id**: ID pipeline

    Mostra status, step corrente, risultati, etc.

    Richiede JWT token. Puoi vedere solo le tue pipeline.
    """
    # Converti pipeline_id da stringa a UUID
    try:
        pipeline_uuid = UUID(pipeline_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline ID non valido"
        )

    pipeline = db.query(Pipeline).filter(
        Pipeline.id == pipeline_uuid,
        Pipeline.user_id == current_user.id
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline non trovata"
        )

    return {
        "pipeline_id": str(pipeline.id),
        "name": pipeline.name,
        "description": pipeline.description,
        "status": pipeline.status.value,
        "current_step": pipeline.current_step,
        "total_steps": pipeline.total_steps,
        "steps": pipeline.steps,
        "stop_on_error": pipeline.stop_on_error,
        "created_at": pipeline.created_at.isoformat(),
        "started_at": pipeline.started_at.isoformat() if pipeline.started_at else None,
        "completed_at": pipeline.completed_at.isoformat() if pipeline.completed_at else None,
        "result": pipeline.result,
        "error_message": pipeline.error
    }


@router.get("/", response_model=List[PipelineResponse])
async def list_pipelines(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = None,
    limit: int = 50
):
    """
    Lista tutte le pipeline dell'utente

    - **status_filter**: Filtra per status (opzionale): "pending", "running", "completed", "failed"
    - **limit**: Max risultati (default: 50)

    Richiede JWT token.
    """
    query = db.query(Pipeline).filter(Pipeline.user_id == current_user.id)

    # Applica filtro status
    if status_filter:
        try:
            status_enum = PipelineStatus[status_filter.upper()]
            query = query.filter(Pipeline.status == status_enum)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status non valido: {status_filter}"
            )

    # Ordina per data creazione (più recenti prima)
    query = query.order_by(Pipeline.created_at.desc()).limit(limit)

    pipelines = query.all()

    return [
        {
            "pipeline_id": str(p.id),
            "name": p.name,
            "status": p.status.value,
            "current_step": p.current_step,
            "total_steps": p.total_steps,
            "enabled_steps_count": len(p.enabled_steps),
            "progress": int((p.current_step / p.total_steps) * 100) if p.total_steps > 0 else 0,
            "message": p.error or "In esecuzione" if p.status == PipelineStatus.RUNNING else "Completata"
        }
        for p in pipelines
    ]


@router.patch("/{pipeline_id}/toggle-step/{step_number}")
async def toggle_step(
    pipeline_id: str,
    step_number: int,
    enabled: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Abilita/disabilita step in pipeline

    - **pipeline_id**: ID pipeline
    - **step_number**: Numero step (1-based)
    - **enabled**: true per abilitare, false per disabilitare

    Utile per eseguire solo alcuni step della pipeline.

    Esempio: Disabilita step 3 (YouTube upload) per testare solo chromakey + thumbnail.

    Richiede JWT token.
    """
    # Converti pipeline_id da stringa a UUID
    try:
        pipeline_uuid = UUID(pipeline_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline ID non valido"
        )

    pipeline = db.query(Pipeline).filter(
        Pipeline.id == pipeline_uuid,
        Pipeline.user_id == current_user.id
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline non trovata"
        )

    # Non modificabile se in esecuzione
    if pipeline.status == PipelineStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossibile modificare pipeline in esecuzione"
        )

    # Trova step
    step_found = False
    for step in pipeline.steps:
        if step["step_number"] == step_number:
            step["enabled"] = enabled
            step_found = True
            break

    if not step_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step {step_number} non trovato"
        )

    # Marca come modificato per SQLAlchemy
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(pipeline, "steps")

    db.commit()

    return {
        "status": "success",
        "message": f"Step {step_number} {'abilitato' if enabled else 'disabilitato'}",
        "enabled_steps_count": len(pipeline.enabled_steps)
    }


@router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Elimina pipeline

    - **pipeline_id**: ID pipeline da eliminare

    Non puoi eliminare pipeline in esecuzione.

    Richiede JWT token. Puoi eliminare solo le tue pipeline.
    """
    # Converti pipeline_id da stringa a UUID
    try:
        pipeline_uuid = UUID(pipeline_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline ID non valido"
        )

    pipeline = db.query(Pipeline).filter(
        Pipeline.id == pipeline_uuid,
        Pipeline.user_id == current_user.id
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline non trovata"
        )

    if pipeline.status == PipelineStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossibile eliminare pipeline in esecuzione"
        )

    db.delete(pipeline)
    db.commit()

    return None

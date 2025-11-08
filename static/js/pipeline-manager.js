/**
 * Pipeline Manager - Sistema AUTO Workflow
 * =========================================
 * Gestisce l'esecuzione automatica di pipeline multi-step
 * utilizzando il PipelineOrchestrator backend.
 */

// ==================== STATO GLOBALE ====================

let currentPipelineId = null;
let pipelineMonitorInterval = null;
let uploadedFiles = {
    mainVideo: null,
    logoImage: null,
    ctaVideo: null
};

// ==================== CONFIGURAZIONE ====================

const PIPELINE_CONFIG = {
    // Polling interval per monitoring (ms)
    monitorIntervalMs: 2000,

    // Job types supportati
    supportedJobTypes: [
        'logo_overlay',
        'chromakey',
        'transcription',
        'translation',
        'thumbnail',
        'seo_metadata',
        'youtube_upload'
    ],

    // Mapping checkbox ID → job_type
    checkboxMapping: {
        'logoOverlay': 'logo_overlay',
        'callToAction': 'chromakey',
        'videoTranscription': 'transcription',
        'audioTranslation': 'translation',
        'coverGeneration': 'thumbnail',
        'metadataGeneration': 'seo_metadata',
        'youtubeUpload': 'youtube_upload'
    }
};

// ==================== UTILITY FUNCTIONS ====================

/**
 * Mostra alert personalizzato
 */
function showAlert(message, type = 'info') {
    // Usa sistema alert esistente se disponibile
    if (typeof window.showAlert === 'function') {
        window.showAlert(message, type);
        return;
    }

    // Fallback: console + alert browser
    console.log(`[${type.toUpperCase()}] ${message}`);
    alert(message);
}

/**
 * Ottieni file caricato corrente
 */
function getMainVideoPath() {
    // Controlla variabili globali esistenti
    if (window.backgroundVideoFileId) {
        return `/uploads/${window.backgroundVideoFileId}`;
    }

    if (uploadedFiles.mainVideo) {
        return uploadedFiles.mainVideo.path;
    }

    return null;
}

// ==================== PIPELINE CREATION ====================

/**
 * Crea configurazione step per logo overlay
 */
function createLogoOverlayStep(stepNumber) {
    const videoPath = getMainVideoPath();

    if (!videoPath) {
        throw new Error('Video principale non caricato');
    }

    return {
        step_number: stepNumber,
        job_type: 'logo_overlay',
        enabled: true,
        parameters: {
            video_path: videoPath,
            logo_path: uploadedFiles.logoImage?.path || null,
            position: 'top-right',
            scale: 0.15,
            opacity: 0.8
        }
    };
}

/**
 * Crea configurazione step per chromakey (CTA overlay)
 */
function createChromakeyStep(stepNumber) {
    return {
        step_number: stepNumber,
        job_type: 'chromakey',
        enabled: true,
        parameters: {
            foreground_path: uploadedFiles.ctaVideo?.path || null,
            background_path: '@previous', // Usa output step precedente
            start_time: 5.0,
            duration: null,
            audio_mode: 'synced',
            position_x: 0.7,
            position_y: 0.7,
            scale: 0.3
        }
    };
}

/**
 * Crea configurazione step per transcription
 */
function createTranscriptionStep(stepNumber) {
    return {
        step_number: stepNumber,
        job_type: 'transcription',
        enabled: true,
        parameters: {
            video_path: '@previous',
            language: 'auto', // Auto-detect
            model: 'base', // Whisper model
            output_formats: ['srt', 'vtt', 'txt']
        }
    };
}

/**
 * Crea configurazione step per translation
 */
function createTranslationStep(stepNumber) {
    // TODO: Aggiungere UI per selezione lingua target
    const targetLanguage = 'en'; // Default inglese

    return {
        step_number: stepNumber,
        job_type: 'translation',
        enabled: true,
        parameters: {
            video_path: '@previous',
            target_language: targetLanguage,
            source_language: 'auto',
            use_elevenlabs: false, // TODO: Aggiungere checkbox
            subtitle_position: 'bottom'
        }
    };
}

/**
 * Crea configurazione step per thumbnail generation
 */
function createThumbnailStep(stepNumber) {
    return {
        step_number: stepNumber,
        job_type: 'thumbnail',
        enabled: true,
        parameters: {
            source_type: 'video_frame',
            video_path: '@previous',
            frame_time: 5.0, // Estrai frame a 5 secondi
            ai_style: 'vibrant',
            text_overlay: '', // TODO: Aggiungere input
            enhance_ctr: true
        }
    };
}

/**
 * Crea configurazione step per SEO metadata
 */
function createSEOMetadataStep(stepNumber) {
    return {
        step_number: stepNumber,
        job_type: 'seo_metadata',
        enabled: true,
        parameters: {
            video_path: '@previous',
            transcription_path: '@transcription', // Usa trascrizione se disponibile
            num_hashtags: 10,
            num_tags: 15,
            language: 'it'
        }
    };
}

/**
 * Crea configurazione step per YouTube upload
 */
function createYouTubeUploadStep(stepNumber) {
    return {
        step_number: stepNumber,
        job_type: 'youtube_upload',
        enabled: true,
        parameters: {
            video_path: '@previous',
            thumbnail_path: '@thumbnail', // Usa thumbnail generata
            metadata: '@seo_metadata', // Usa metadati generati
            title: '', // TODO: Sarà riempito da SEO metadata
            description: '',
            privacy_status: 'private', // TODO: Aggiungere select
            tags: []
        }
    };
}

/**
 * Mappa job_type → funzione creazione step
 */
const STEP_CREATORS = {
    'logo_overlay': createLogoOverlayStep,
    'chromakey': createChromakeyStep,
    'transcription': createTranscriptionStep,
    'translation': createTranslationStep,
    'thumbnail': createThumbnailStep,
    'seo_metadata': createSEOMetadataStep,
    'youtube_upload': createYouTubeUploadStep
};

/**
 * Raccoglie step abilitati da UI
 */
function collectEnabledSteps() {
    const steps = [];
    let stepNumber = 1;

    // Itera su tutti i checkbox
    for (const [checkboxId, jobType] of Object.entries(PIPELINE_CONFIG.checkboxMapping)) {
        const checkbox = document.getElementById(checkboxId);

        if (checkbox && checkbox.checked) {
            // Crea step usando funzione appropriata
            const createStep = STEP_CREATORS[jobType];

            if (createStep) {
                try {
                    const step = createStep(stepNumber);
                    steps.push(step);
                    stepNumber++;
                } catch (error) {
                    console.warn(`⚠️  Errore creazione step ${jobType}:`, error.message);
                    showAlert(`Configurazione ${jobType} incompleta: ${error.message}`, 'warning');
                }
            } else {
                console.warn(`⚠️  Job type ${jobType} non supportato (step creator mancante)`);
            }
        }
    }

    return steps;
}

// ==================== PIPELINE EXECUTION ====================

/**
 * Funzione principale: Avvia workflow automatico
 * Chiamata dal pulsante "Avvia Workflow Automatico"
 */
async function processVideo() {
    try {
        console.log('🚀 Avvio workflow automatico...');

        // Verifica che almeno un video sia caricato
        const videoPath = getMainVideoPath();
        if (!videoPath) {
            showAlert('Carica almeno un video principale prima di avviare il workflow', 'error');
            return;
        }

        // Raccogli step abilitati
        const steps = collectEnabledSteps();

        if (steps.length === 0) {
            showAlert('Seleziona almeno una funzionalità da abilitare', 'warning');
            return;
        }

        console.log(`📋 Configurati ${steps.length} step:`, steps.map(s => s.job_type));

        // Disabilita pulsante
        const btn = document.getElementById('processBtn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creazione pipeline...';
        }

        // 1. Crea pipeline
        const pipelineResponse = await fetch('/api/v1/pipelines/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: `Workflow AUTO - ${new Date().toLocaleString('it-IT')}`,
                description: `Pipeline automatica con ${steps.length} step`,
                steps: steps,
                stop_on_error: true
            })
        });

        if (!pipelineResponse.ok) {
            const error = await pipelineResponse.json();
            throw new Error(error.detail || 'Errore creazione pipeline');
        }

        const pipelineData = await pipelineResponse.json();
        currentPipelineId = pipelineData.pipeline_id;

        console.log(`✅ Pipeline creata: ${currentPipelineId}`);
        showAlert(`Pipeline creata con ${pipelineData.enabled_steps_count} step attivi`, 'success');

        // Aggiorna UI
        if (btn) {
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Esecuzione in corso...';
        }

        // 2. Esegui pipeline
        const executeResponse = await fetch(`/api/v1/pipelines/${currentPipelineId}/execute`, {
            method: 'POST'
        });

        if (!executeResponse.ok) {
            const error = await executeResponse.json();
            throw new Error(error.detail || 'Errore esecuzione pipeline');
        }

        const executeData = await executeResponse.json();
        console.log('✅ Pipeline in esecuzione:', executeData);

        // 3. Avvia monitoring
        startPipelineMonitoring();

    } catch (error) {
        console.error('❌ Errore workflow:', error);
        showAlert(`Errore: ${error.message}`, 'error');

        // Ripristina pulsante
        const btn = document.getElementById('processBtn');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-magic"></i> Avvia Workflow Automatico';
        }
    }
}

// ==================== PIPELINE MONITORING ====================

/**
 * Avvia monitoring progresso pipeline
 */
function startPipelineMonitoring() {
    if (!currentPipelineId) {
        console.error('❌ Nessuna pipeline da monitorare');
        return;
    }

    console.log(`⏰ Avvio monitoring pipeline ${currentPipelineId}`);

    // Ferma monitoring precedente se esiste
    if (pipelineMonitorInterval) {
        clearInterval(pipelineMonitorInterval);
    }

    // Polling ogni 2 secondi
    pipelineMonitorInterval = setInterval(async () => {
        await checkPipelineStatus();
    }, PIPELINE_CONFIG.monitorIntervalMs);

    // Prima chiamata immediata
    checkPipelineStatus();
}

/**
 * Verifica stato pipeline
 */
async function checkPipelineStatus() {
    if (!currentPipelineId) {
        return;
    }

    try {
        const response = await fetch(`/api/v1/pipelines/${currentPipelineId}`);

        if (!response.ok) {
            throw new Error('Errore recupero stato pipeline');
        }

        const pipeline = await response.json();

        console.log(`📊 Pipeline ${pipeline.status} - Step ${pipeline.current_step}/${pipeline.total_steps}`);

        // Aggiorna UI
        updatePipelineUI(pipeline);

        // Se completata o fallita, ferma monitoring
        if (pipeline.status === 'completed' || pipeline.status === 'failed') {
            stopPipelineMonitoring();
            handlePipelineComplete(pipeline);
        }

    } catch (error) {
        console.error('❌ Errore monitoring:', error);
    }
}

/**
 * Ferma monitoring
 */
function stopPipelineMonitoring() {
    if (pipelineMonitorInterval) {
        clearInterval(pipelineMonitorInterval);
        pipelineMonitorInterval = null;
        console.log('⏸️  Monitoring fermato');
    }
}

/**
 * Aggiorna UI con stato pipeline
 */
function updatePipelineUI(pipeline) {
    const btn = document.getElementById('processBtn');
    const progressSection = document.getElementById('pipelineProgress');
    const progressBar = document.getElementById('pipelineProgressBar');
    const statusText = document.getElementById('pipelineStatusText');
    const percentageText = document.getElementById('pipelinePercentage');

    if (!btn) return;

    const progress = Math.round((pipeline.current_step / pipeline.total_steps) * 100);

    let statusIcon = 'fa-spinner fa-spin';
    let statusMessage = `Elaborazione step ${pipeline.current_step}/${pipeline.total_steps}`;

    if (pipeline.status === 'completed') {
        statusIcon = 'fa-check-circle';
        statusMessage = 'Workflow completato!';
    } else if (pipeline.status === 'failed') {
        statusIcon = 'fa-exclamation-triangle';
        statusMessage = 'Errore durante elaborazione';
    }

    // Aggiorna pulsante
    btn.innerHTML = `<i class="fas ${statusIcon}"></i> ${statusMessage}`;

    // Mostra e aggiorna sezione progresso
    if (progressSection) {
        progressSection.style.display = 'block';
    }

    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }

    if (statusText) {
        statusText.textContent = statusMessage;
    }

    if (percentageText) {
        percentageText.textContent = `${progress}%`;
    }

    // Aggiorna lista step (se esiste)
    if (pipeline.steps) {
        updateStepsList(pipeline.steps, pipeline.current_step);
    }
}

/**
 * Aggiorna lista step nella UI
 */
function updateStepsList(steps, currentStep) {
    const stepsList = document.getElementById('pipelineStepsList');
    if (!stepsList) return;

    // Crea/aggiorna step items
    stepsList.innerHTML = '';

    steps.forEach((step, index) => {
        const stepNumber = index + 1;
        const isCompleted = stepNumber < currentStep;
        const isCurrent = stepNumber === currentStep;
        const isPending = stepNumber > currentStep;

        let icon = 'fa-circle';
        let color = '#ccc';

        if (isCompleted) {
            icon = 'fa-check-circle';
            color = '#38ef7d';
        } else if (isCurrent) {
            icon = 'fa-spinner fa-spin';
            color = '#667eea';
        }

        if (!step.enabled) {
            icon = 'fa-times-circle';
            color = '#999';
        }

        const stepHTML = `
            <div style="display: flex; align-items: center; gap: 12px; padding: 12px; background: ${isCurrent ? '#f8f9fa' : 'transparent'}; border-radius: 8px; border-left: 3px solid ${color};">
                <i class="fas ${icon}" style="color: ${color}; font-size: 1.2rem;"></i>
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: #333;">${step.job_type}</div>
                    <div style="font-size: 0.85rem; color: #666;">${step.enabled ? (isCurrent ? 'In elaborazione...' : isCompleted ? 'Completato' : 'In attesa') : 'Disabilitato'}</div>
                </div>
            </div>
        `;

        stepsList.innerHTML += stepHTML;
    });
}

/**
 * Gestisce completamento pipeline
 */
function handlePipelineComplete(pipeline) {
    const btn = document.getElementById('processBtn');

    if (pipeline.status === 'completed') {
        console.log('🎉 Pipeline completata con successo!');
        console.log('📦 Risultati:', pipeline.result);

        showAlert('Workflow completato con successo! 🎉', 'success');

        // Ripristina pulsante dopo 3 secondi
        setTimeout(() => {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-magic"></i> Avvia Workflow Automatico';
            }
            currentPipelineId = null;
        }, 3000);

    } else if (pipeline.status === 'failed') {
        console.error('❌ Pipeline fallita:', pipeline.error_message);

        showAlert(`Workflow fallito: ${pipeline.error_message || 'Errore sconosciuto'}`, 'error');

        // Ripristina pulsante immediatamente
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-magic"></i> Avvia Workflow Automatico';
        }
        currentPipelineId = null;
    }
}

// ==================== FILE UPLOAD TRACKING ====================

/**
 * Track uploaded files (integrare con upload handlers esistenti)
 */
function trackUploadedFile(type, fileData) {
    uploadedFiles[type] = fileData;
    console.log(`✅ File tracciato: ${type}`, fileData);
}

// Esporta funzioni globalmente
window.processVideo = processVideo;
window.trackUploadedFile = trackUploadedFile;

console.log('✅ Pipeline Manager inizializzato');

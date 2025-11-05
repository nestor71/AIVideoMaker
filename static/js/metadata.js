/**
 * METADATA.JS - Logica frontend per Tab Metadati SEO YouTube
 * Gestisce upload, generazione AI, personalizzazione e copia metadati
 */

// Stato globale
let metadataState = {
    uploadedFile: null,
    fileId: null,
    generatedMetadata: null,
    originalMetadata: null
};

// Impostazioni default
const METADATA_DEFAULT_SETTINGS = {
    numHashtags: 5,
    numTags: 12,
    useTranscription: false,
    titleAddon: '',
    titleAddonPosition: 'end',
    descriptionAddon: '',
    descriptionAddonPosition: 'end',
    fixedHashtags: '',
    fixedTags: ''
};

// ============================================================================
// INIZIALIZZAZIONE
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    initMetadataTab();
});

function initMetadataTab() {
    console.log('🎬 Inizializzazione Tab Metadati');

    // Ripristina impostazioni salvate
    loadMetadataSettings();

    // Setup drag & drop
    setupDragAndDrop();

    // Setup file input
    const fileInput = document.getElementById('metadataVideoInput');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }

    // Setup generate button
    const generateBtn = document.getElementById('generateMetadataBtn');
    if (generateBtn) {
        generateBtn.addEventListener('click', generateMetadata);
    }

    // Setup character counters
    setupCharacterCounters();

    // Setup auto-save sui campi impostazioni
    setupAutoSave();
}

// ============================================================================
// DRAG & DROP
// ============================================================================

function setupDragAndDrop() {
    const dropzone = document.getElementById('metadataDropzone');
    if (!dropzone) return;

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.classList.remove('dragover');
        }, false);
    });

    // Handle dropped files
    dropzone.addEventListener('drop', handleDrop, false);
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;

    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

// ============================================================================
// UPLOAD FILE
// ============================================================================

async function handleFile(file) {
    console.log('📁 File selezionato:', file.name);

    // Validazione tipo
    if (!file.type.startsWith('video/')) {
        showAlert('Errore: Seleziona un file video valido', 'error');
        return;
    }

    // Validazione dimensione (500MB)
    const maxSize = 500 * 1024 * 1024;
    if (file.size > maxSize) {
        showAlert(`Errore: File troppo grande. Max 500MB`, 'error');
        return;
    }

    // Salva nello stato
    metadataState.uploadedFile = file;

    // Mostra anteprima
    showFilePreview(file);

    // Upload al server
    await uploadFile(file);
}

function showFilePreview(file) {
    const preview = document.getElementById('metadataFilePreview');
    const dropzone = document.getElementById('metadataDropzone');
    const videoElement = document.getElementById('metadataVideoElement');

    // Mostra info file
    document.getElementById('metadataFileName').textContent = file.name;
    document.getElementById('metadataFileSize').textContent = formatFileSize(file.size);

    // Calcola durata (approssimativa, verrà aggiornata dopo upload)
    document.getElementById('metadataFileDuration').textContent = 'Calcolando...';

    // Crea URL per preview video
    const videoURL = URL.createObjectURL(file);
    videoElement.src = videoURL;

    // Quando il video è caricato, aggiorna la durata
    videoElement.addEventListener('loadedmetadata', function() {
        const duration = videoElement.duration;
        const minutes = Math.floor(duration / 60);
        const seconds = Math.floor(duration % 60);
        document.getElementById('metadataFileDuration').textContent =
            `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }, { once: true });

    // Mostra preview, nascondi dropzone
    dropzone.style.display = 'none';
    preview.style.display = 'block';

    // Abilita pulsante genera
    document.getElementById('generateMetadataBtn').disabled = false;
}

async function uploadFile(file) {
    try {
        showProgress(0, 'Caricamento video...');

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/metadata/upload-video', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Errore upload');
        }

        const result = await response.json();
        console.log('✅ Upload completato:', result);

        // Salva file_id
        metadataState.fileId = result.file_id;

        // Aggiorna durata
        if (result.duration) {
            const minutes = Math.floor(result.duration / 60);
            const seconds = Math.floor(result.duration % 60);
            document.getElementById('metadataFileDuration').textContent =
                `${minutes}:${seconds.toString().padStart(2, '0')}`;
        } else {
            document.getElementById('metadataFileDuration').textContent = 'N/A';
        }

        hideProgress();
        showAlert('Video caricato con successo!', 'success');

    } catch (error) {
        console.error('❌ Errore upload:', error);
        hideProgress();
        showAlert(`Errore upload: ${error.message}`, 'error');
        clearMetadataUpload();
    }
}

function clearMetadataUpload() {
    // Reset stato
    metadataState.uploadedFile = null;
    metadataState.fileId = null;

    // Pulisci video element
    const videoElement = document.getElementById('metadataVideoElement');
    if (videoElement) {
        videoElement.pause();
        videoElement.src = '';
        // Libera memoria URL.createObjectURL
        if (videoElement.src) {
            URL.revokeObjectURL(videoElement.src);
        }
    }

    // Reset UI
    document.getElementById('metadataFilePreview').style.display = 'none';
    document.getElementById('metadataDropzone').style.display = 'block';
    document.getElementById('metadataVideoInput').value = '';
    document.getElementById('generateMetadataBtn').disabled = true;

    // Nascondi risultati
    document.getElementById('metadataResults').style.display = 'none';
    document.getElementById('metadataFinalOutput').style.display = 'none';
}

// ============================================================================
// GENERAZIONE METADATI
// ============================================================================

async function generateMetadata() {
    if (!metadataState.fileId) {
        showAlert('Errore: Nessun file caricato', 'error');
        return;
    }

    try {
        showProgress(10, 'Preparazione generazione...');

        const numHashtags = parseInt(document.getElementById('numHashtags').value);
        const numTags = parseInt(document.getElementById('numTags').value);
        const useTranscription = document.getElementById('useTranscription').checked;

        const formData = new FormData();
        formData.append('file_id', metadataState.fileId);
        formData.append('num_hashtags', numHashtags);
        formData.append('num_tags', numTags);
        formData.append('use_transcription', useTranscription);

        if (useTranscription) {
            showProgress(20, 'Trascrizione audio in corso (1-2 minuti)...');
        } else {
            showProgress(30, 'Generazione metadati...');
        }

        const response = await fetch('/api/metadata/generate', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Errore generazione');
        }

        const result = await response.json();
        console.log('✅ Metadati generati:', result);

        showProgress(90, 'Finalizzazione...');

        // Salva metadati
        metadataState.originalMetadata = result.metadata;
        metadataState.generatedMetadata = result.metadata;

        // Mostra risultati
        displayMetadata(result.metadata);

        hideProgress();

        // Alert con info trascrizione salvata
        let alertMessage = 'Metadati generati!';
        if (useTranscription && result.used_transcription) {
            if (result.transcription_saved && result.transcription_files) {
                alertMessage = `✅ Metadati generati con trascrizione audio!\n📄 Trascrizione salvata: ${result.transcription_files.txt_filename}\n📄 Sottotitoli: ${result.transcription_files.srt_filename}`;
            } else {
                alertMessage = 'Metadati generati con trascrizione audio!';
            }
        }
        showAlert(alertMessage, 'success');

    } catch (error) {
        console.error('❌ Errore generazione:', error);
        hideProgress();
        showAlert(`Errore generazione: ${error.message}`, 'error');
    }
}

function displayMetadata(metadata) {
    // Popola campi
    document.getElementById('metadataTitle').value = metadata.title || '';
    document.getElementById('metadataDescription').value = metadata.description || '';
    document.getElementById('metadataHashtags').value = (metadata.hashtags || []).join(' ');
    document.getElementById('metadataTags').value = (metadata.tags || []).join(', ');

    // Aggiorna contatori
    updateCharacterCounters();

    // Mostra sezioni
    document.getElementById('metadataResults').style.display = 'block';
    document.getElementById('metadataFinalOutput').style.display = 'block';

    // Genera anteprima formattata
    updateFormattedPreview(metadata);

    // Scroll alla sezione risultati
    document.getElementById('metadataResults').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ============================================================================
// PERSONALIZZAZIONE
// ============================================================================

async function applyCustomizations() {
    if (!metadataState.originalMetadata) {
        showAlert('Errore: Genera prima i metadati', 'error');
        return;
    }

    try {
        showProgress(30, 'Applicazione personalizzazioni...');

        const formData = new FormData();
        formData.append('metadata', JSON.stringify(metadataState.originalMetadata));

        // Addon titolo
        const titleAddon = document.getElementById('titleAddon').value.trim();
        if (titleAddon) {
            formData.append('title_addon', titleAddon);
            formData.append('title_addon_position', document.getElementById('titleAddonPosition').value);
        }

        // Addon descrizione
        const descAddon = document.getElementById('descriptionAddon').value.trim();
        if (descAddon) {
            formData.append('description_addon', descAddon);
            formData.append('description_addon_position', document.getElementById('descriptionAddonPosition').value);
        }

        // Hashtag fissi
        const fixedHashtags = document.getElementById('fixedHashtags').value.trim();
        if (fixedHashtags) {
            formData.append('fixed_hashtags', fixedHashtags);
        }

        // Tag fissi
        const fixedTags = document.getElementById('fixedTags').value.trim();
        if (fixedTags) {
            formData.append('fixed_tags', fixedTags);
        }

        // Limiti
        formData.append('max_hashtags', document.getElementById('numHashtags').value);
        formData.append('max_tags', document.getElementById('numTags').value);

        const response = await fetch('/api/metadata/customize', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Errore personalizzazione');
        }

        const result = await response.json();
        console.log('✅ Personalizzazioni applicate:', result);

        // Aggiorna metadati
        metadataState.generatedMetadata = result.metadata;
        displayMetadata(result.metadata);

        hideProgress();
        showAlert('Personalizzazioni applicate!', 'success');

    } catch (error) {
        console.error('❌ Errore personalizzazione:', error);
        hideProgress();
        showAlert(`Errore personalizzazione: ${error.message}`, 'error');
    }
}

async function regenerateMetadata() {
    // Reset personalizzazioni
    document.getElementById('titleAddon').value = '';
    document.getElementById('descriptionAddon').value = '';
    document.getElementById('fixedHashtags').value = '';
    document.getElementById('fixedTags').value = '';

    // Rigenera
    await generateMetadata();
}

// ============================================================================
// ANTEPRIMA E COPIA
// ============================================================================

function updateFormattedPreview(metadata) {
    const formatted = formatMetadataText(metadata);
    document.getElementById('formattedMetadata').textContent = formatted;
}

function formatMetadataText(metadata) {
    let output = [];
    output.push('═══════════════════════════════════════════════════════════');
    output.push('📹 METADATI YOUTUBE - COPIA/INCOLLA');
    output.push('═══════════════════════════════════════════════════════════');
    output.push('');

    output.push('🎯 TITOLO:');
    output.push(metadata.title || '');
    output.push('');

    output.push('📝 DESCRIZIONE:');
    output.push(metadata.description || '');
    output.push('');

    output.push('# HASHTAG:');
    output.push((metadata.hashtags || []).join(' '));
    output.push('');

    output.push('🏷️ TAG (separa con virgola su YouTube):');
    output.push((metadata.tags || []).join(', '));
    output.push('');

    output.push('═══════════════════════════════════════════════════════════');

    return output.join('\n');
}

async function copyAllMetadata() {
    const text = document.getElementById('formattedMetadata').textContent;

    try {
        await navigator.clipboard.writeText(text);
        showAlert('✅ Metadati copiati negli appunti!', 'success');

        // Animazione pulsante
        const btn = event.target;
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-check"></i> Copiato!';
        btn.classList.add('btn-success');
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.classList.remove('btn-success');
        }, 2000);

    } catch (error) {
        console.error('❌ Errore copia:', error);

        // Fallback: selezione manuale
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);

        showAlert('Metadati copiati negli appunti!', 'success');
    }
}

// ============================================================================
// CONTATORI CARATTERI
// ============================================================================

function setupCharacterCounters() {
    const titleField = document.getElementById('metadataTitle');
    const descField = document.getElementById('metadataDescription');

    if (titleField) {
        titleField.addEventListener('input', updateCharacterCounters);
    }

    if (descField) {
        descField.addEventListener('input', updateCharacterCounters);
    }
}

function updateCharacterCounters() {
    // Titolo
    const titleField = document.getElementById('metadataTitle');
    if (titleField) {
        const titleCount = titleField.value.length;
        const titleCounter = document.getElementById('titleCharCount');
        if (titleCounter) {
            titleCounter.textContent = `${titleCount}/100`;
            titleCounter.style.color = titleCount > 70 ? '#28a745' :
                                       titleCount > 45 ? '#ffc107' : '#dc3545';
        }
    }

    // Descrizione
    const descField = document.getElementById('metadataDescription');
    if (descField) {
        const descCount = descField.value.length;
        const descCounter = document.getElementById('descCharCount');
        if (descCounter) {
            descCounter.textContent = `${descCount}/5000`;
            descCounter.style.color = descCount > 150 ? '#28a745' : '#ffc107';
        }
    }

    // Hashtag
    const hashtagField = document.getElementById('metadataHashtags');
    if (hashtagField) {
        const hashtags = hashtagField.value.split(' ').filter(h => h.trim().length > 0);
        const hashtagCounter = document.getElementById('hashtagCount');
        if (hashtagCounter) {
            hashtagCounter.textContent = `${hashtags.length} hashtag`;
        }
    }

    // Tag
    const tagField = document.getElementById('metadataTags');
    if (tagField) {
        const tags = tagField.value.split(',').filter(t => t.trim().length > 0);
        const tagCounter = document.getElementById('tagCount');
        if (tagCounter) {
            tagCounter.textContent = `${tags.length} tag`;
        }
    }
}

// ============================================================================
// PROGRESS BAR
// ============================================================================

function showProgress(percent, message) {
    const progressContainer = document.getElementById('metadataProgress');
    const progressBar = document.getElementById('metadataProgressBar');
    const progressText = document.getElementById('metadataProgressText');

    if (progressContainer) progressContainer.style.display = 'block';
    if (progressBar) {
        progressBar.style.width = `${percent}%`;
        progressBar.textContent = `${percent}%`;
    }
    if (progressText) progressText.textContent = message || 'Elaborazione...';

    // Disabilita pulsante genera
    const btn = document.getElementById('generateMetadataBtn');
    if (btn) btn.disabled = true;
}

function hideProgress() {
    const progressContainer = document.getElementById('metadataProgress');
    if (progressContainer) progressContainer.style.display = 'none';

    // Riabilita pulsante genera
    const btn = document.getElementById('generateMetadataBtn');
    if (btn) btn.disabled = false;
}

// ============================================================================
// UTILITY
// ============================================================================

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function showAlert(message, type = 'info') {
    // Cerca container alert esistente o crealo
    let alertContainer = document.getElementById('metadataAlerts');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'metadataAlerts';
        alertContainer.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 9999; max-width: 400px;';
        document.body.appendChild(alertContainer);
    }

    // Mappa type a classe Bootstrap
    const typeMap = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    };

    // Crea alert
    const alert = document.createElement('div');
    alert.className = `alert ${typeMap[type] || 'alert-info'} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    alertContainer.appendChild(alert);

    // Auto-remove dopo 5 secondi
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 300);
    }, 5000);
}

// ============================================================================
// SALVATAGGIO E RIPRISTINO IMPOSTAZIONI
// ============================================================================

function saveMetadataSettings() {
    const settings = {
        numHashtags: parseInt(document.getElementById('numHashtags')?.value || 5),
        numTags: parseInt(document.getElementById('numTags')?.value || 12),
        useTranscription: document.getElementById('useTranscription')?.checked || false,
        titleAddon: document.getElementById('titleAddon')?.value || '',
        titleAddonPosition: document.getElementById('titleAddonPosition')?.value || 'end',
        descriptionAddon: document.getElementById('descriptionAddon')?.value || '',
        descriptionAddonPosition: document.getElementById('descriptionAddonPosition')?.value || 'end',
        fixedHashtags: document.getElementById('fixedHashtags')?.value || '',
        fixedTags: document.getElementById('fixedTags')?.value || ''
    };

    localStorage.setItem('metadataSettings', JSON.stringify(settings));
    console.log('💾 Impostazioni metadati salvate:', settings);
}

function loadMetadataSettings() {
    try {
        const saved = localStorage.getItem('metadataSettings');
        const settings = saved ? JSON.parse(saved) : METADATA_DEFAULT_SETTINGS;

        console.log('📂 Ripristino impostazioni metadati:', settings);

        // Applica impostazioni ai campi
        const numHashtags = document.getElementById('numHashtags');
        if (numHashtags) numHashtags.value = settings.numHashtags;

        const numTags = document.getElementById('numTags');
        if (numTags) numTags.value = settings.numTags;

        const useTranscription = document.getElementById('useTranscription');
        if (useTranscription) useTranscription.checked = settings.useTranscription;

        const titleAddon = document.getElementById('titleAddon');
        if (titleAddon) titleAddon.value = settings.titleAddon;

        const titleAddonPosition = document.getElementById('titleAddonPosition');
        if (titleAddonPosition) titleAddonPosition.value = settings.titleAddonPosition;

        const descriptionAddon = document.getElementById('descriptionAddon');
        if (descriptionAddon) descriptionAddon.value = settings.descriptionAddon;

        const descriptionAddonPosition = document.getElementById('descriptionAddonPosition');
        if (descriptionAddonPosition) descriptionAddonPosition.value = settings.descriptionAddonPosition;

        const fixedHashtags = document.getElementById('fixedHashtags');
        if (fixedHashtags) fixedHashtags.value = settings.fixedHashtags;

        const fixedTags = document.getElementById('fixedTags');
        if (fixedTags) fixedTags.value = settings.fixedTags;

    } catch (error) {
        console.error('❌ Errore caricamento impostazioni metadati:', error);
        resetMetadataSettings();
    }
}

function resetMetadataSettings() {
    console.log('🔄 Reset impostazioni metadati a default');

    // Applica default
    const numHashtags = document.getElementById('numHashtags');
    if (numHashtags) numHashtags.value = METADATA_DEFAULT_SETTINGS.numHashtags;

    const numTags = document.getElementById('numTags');
    if (numTags) numTags.value = METADATA_DEFAULT_SETTINGS.numTags;

    const useTranscription = document.getElementById('useTranscription');
    if (useTranscription) useTranscription.checked = METADATA_DEFAULT_SETTINGS.useTranscription;

    const titleAddon = document.getElementById('titleAddon');
    if (titleAddon) titleAddon.value = METADATA_DEFAULT_SETTINGS.titleAddon;

    const titleAddonPosition = document.getElementById('titleAddonPosition');
    if (titleAddonPosition) titleAddonPosition.value = METADATA_DEFAULT_SETTINGS.titleAddonPosition;

    const descriptionAddon = document.getElementById('descriptionAddon');
    if (descriptionAddon) descriptionAddon.value = METADATA_DEFAULT_SETTINGS.descriptionAddon;

    const descriptionAddonPosition = document.getElementById('descriptionAddonPosition');
    if (descriptionAddonPosition) descriptionAddonPosition.value = METADATA_DEFAULT_SETTINGS.descriptionAddonPosition;

    const fixedHashtags = document.getElementById('fixedHashtags');
    if (fixedHashtags) fixedHashtags.value = METADATA_DEFAULT_SETTINGS.fixedHashtags;

    const fixedTags = document.getElementById('fixedTags');
    if (fixedTags) fixedTags.value = METADATA_DEFAULT_SETTINGS.fixedTags;

    // Rimuovi da localStorage
    localStorage.removeItem('metadataSettings');

    // Salva default
    saveMetadataSettings();
}

function setupAutoSave() {
    // Lista di tutti i campi da salvare automaticamente
    const fieldsToSave = [
        'numHashtags',
        'numTags',
        'useTranscription',
        'titleAddon',
        'titleAddonPosition',
        'descriptionAddon',
        'descriptionAddonPosition',
        'fixedHashtags',
        'fixedTags'
    ];

    // Aggiungi event listener a tutti i campi
    fieldsToSave.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            const eventType = field.type === 'checkbox' ? 'change' : 'input';
            field.addEventListener(eventType, () => {
                saveMetadataSettings();
            });
        }
    });

    console.log('✅ Auto-save impostazioni metadati attivato');
}

// Esporta funzioni globali per onclick HTML
window.clearMetadataUpload = clearMetadataUpload;
window.applyCustomizations = applyCustomizations;
window.regenerateMetadata = regenerateMetadata;
window.copyAllMetadata = copyAllMetadata;
window.resetMetadataSettings = resetMetadataSettings;

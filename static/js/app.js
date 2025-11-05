// Global Variables
let foregroundFileId = null;
let backgroundFileId = null;
let currentJobId = null;
let processingInterval = null;

// Initialize App
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded - Initializing app...');
    initializeEventListeners();
    initializeSliders();
    showAlert('Applicazione caricata correttamente!', 'success');
});

// Event Listeners
function initializeEventListeners() {
    console.log('Setting up event listeners...');
    
    // File input listeners
    const foregroundFile = document.getElementById('foregroundFile');
    const backgroundFile = document.getElementById('backgroundFile');
    
    if (foregroundFile) {
        foregroundFile.addEventListener('change', (e) => handleFileSelect(e, 'foreground'));
        console.log('Foreground file listener added');
    }
    
    if (backgroundFile) {
        backgroundFile.addEventListener('change', (e) => handleFileSelect(e, 'background'));
        console.log('Background file listener added');
    }
    
    // Close sidebar when clicking outside
    document.addEventListener('click', handleOutsideClick);
    
    // Drag and drop listeners
    setupDragAndDrop();
}

// Initialize Sliders
function initializeSliders() {
    const sliders = [
        { id: 'startTime', defaultValue: 0 },
        { id: 'duration', defaultValue: 5 },
        { id: 'xPos', defaultValue: 0 },
        { id: 'yPos', defaultValue: 0 },
        { id: 'scale', defaultValue: 1.0 },
        { id: 'opacity', defaultValue: 1.0 }
    ];
    
    sliders.forEach(slider => {
        const element = document.getElementById(slider.id);
        element.value = slider.defaultValue;
        updateValue(slider.id, slider.defaultValue);
    });
}

// Sidebar Functions
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const hamburger = document.querySelector('.hamburger');
    
    sidebar.classList.toggle('active');
    hamburger.classList.toggle('active');
}

function handleOutsideClick(event) {
    const sidebar = document.getElementById('sidebar');
    const hamburger = document.querySelector('.hamburger');
    
    if (!sidebar.contains(event.target) && !hamburger.contains(event.target)) {
        sidebar.classList.remove('active');
        hamburger.classList.remove('active');
    }
}

// Drag and Drop Functions
function setupDragAndDrop() {
    const foregroundArea = document.getElementById('foregroundUpload');
    const backgroundArea = document.getElementById('backgroundUpload');
    
    console.log('Setting up drag and drop...');
    console.log('Foreground area:', foregroundArea);
    console.log('Background area:', backgroundArea);
    
    if (foregroundArea) {
        foregroundArea.addEventListener('click', () => {
            console.log('Foreground area clicked');
            document.getElementById('foregroundFile').click();
        });
        foregroundArea.addEventListener('dragover', handleDragOver);
        foregroundArea.addEventListener('dragleave', handleDragLeave);
        foregroundArea.addEventListener('drop', (e) => handleDrop(e, 'foreground'));
        console.log('Foreground drag&drop listeners added');
    }
    
    if (backgroundArea) {
        backgroundArea.addEventListener('click', () => {
            console.log('Background area clicked');
            document.getElementById('backgroundFile').click();
        });
        backgroundArea.addEventListener('dragover', handleDragOver);
        backgroundArea.addEventListener('dragleave', handleDragLeave);
        backgroundArea.addEventListener('drop', (e) => handleDrop(e, 'background'));
        console.log('Background drag&drop listeners added');
    }
}

function handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('dragover');
    console.log('Drag over detected');
}

function handleDragLeave(event) {
    event.currentTarget.classList.remove('dragover');
    console.log('Drag leave detected');
}

function handleDrop(event, type) {
    event.preventDefault();
    event.currentTarget.classList.remove('dragover');
    
    console.log('Drop detected for type:', type);
    console.log('Files dropped:', event.dataTransfer.files);
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        console.log('Processing file:', files[0].name);
        handleFileUpload(files[0], type);
    } else {
        console.log('No files found in drop event');
    }
}

// File Handling Functions
function handleFileSelect(event, type) {
    const file = event.target.files[0];
    if (file) {
        handleFileUpload(file, type);
    }
}

async function handleFileUpload(file, type) {
    console.log('Starting file upload for:', file.name, 'type:', type);
    
    if (!validateFileType(file)) {
        showAlert('Formato file non supportato. Usa MP4, AVI, MOV o MKV.', 'error');
        return;
    }
    
    console.log('File validation passed');
    showLoadingState(type, true);
    
    const formData = new FormData();
    formData.append('file', file);
    
    console.log('Sending upload request to /api/upload');
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        console.log('Upload response status:', response.status);
        
        if (response.ok) {
            const result = await response.json();
            console.log('Upload successful:', result);
            handleUploadSuccess(result, type);
        } else {
            const error = await response.json();
            console.error('Upload failed:', error);
            throw new Error(error.detail || 'Errore nel caricamento del file');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showAlert('Errore di connessione: ' + error.message, 'error');
    } finally {
        showLoadingState(type, false);
    }
}

function validateFileType(file) {
    const allowedTypes = ['.mp4', '.avi', '.mov', '.mkv'];
    const fileName = file.name.toLowerCase();
    return allowedTypes.some(type => fileName.endsWith(type));
}

function handleUploadSuccess(result, type) {
    if (type === 'foreground') {
        foregroundFileId = result.file_id;
        document.getElementById('foregroundName').textContent = result.filename;
        document.getElementById('foregroundInfo').classList.add('active');
    } else {
        backgroundFileId = result.file_id;
        document.getElementById('backgroundName').textContent = result.filename;
        document.getElementById('backgroundInfo').classList.add('active');
    }
    
    showAlert(`File ${result.filename} caricato con successo!`, 'success');
}

function showLoadingState(type, loading) {
    const uploadArea = document.getElementById(`${type}Upload`);
    
    if (!uploadArea) {
        console.error(`Upload area not found for type: ${type}`);
        return;
    }
    
    const icon = uploadArea.querySelector('i');
    
    if (!icon) {
        console.error(`Icon not found in upload area for type: ${type}`);
        return;
    }
    
    if (loading) {
        icon.className = 'fas fa-spinner fa-spin';
        uploadArea.style.pointerEvents = 'none';
        uploadArea.style.opacity = '0.7';
        console.log(`Loading state enabled for ${type}`);
    } else {
        icon.className = 'fas fa-cloud-upload-alt';
        uploadArea.style.pointerEvents = 'auto';
        uploadArea.style.opacity = '1';
        console.log(`Loading state disabled for ${type}`);
    }
}

// Settings Functions
function updateValue(elementId, value) {
    const valueElement = document.getElementById(elementId + 'Value');
    if (valueElement) {
        valueElement.textContent = value;
    }
}

// Processing Functions
async function previewVideo() {
    if (!validateInputs()) return;
    
    showAlert('Funzione anteprima in sviluppo. Per ora usa il processamento completo.', 'info');
}

async function processVideo() {
    if (!validateInputs()) return;
    
    const formData = createProcessingFormData();
    
    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            currentJobId = result.job_id;
            startProcessing();
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Errore nell\'avvio del processamento');
        }
    } catch (error) {
        showAlert('Errore di connessione: ' + error.message, 'error');
    }
}

function createProcessingFormData() {
    const formData = new FormData();
    formData.append('foreground_file_id', foregroundFileId);
    formData.append('background_file_id', backgroundFileId);
    formData.append('start_time', document.getElementById('startTime').value);
    formData.append('duration', document.getElementById('duration').value);
    formData.append('audio_mode', document.getElementById('audioMode').value);
    formData.append('x_pos', document.getElementById('xPos').value);
    formData.append('y_pos', document.getElementById('yPos').value);
    formData.append('scale', document.getElementById('scale').value);
    formData.append('opacity', document.getElementById('opacity').value);
    formData.append('fast_mode', document.getElementById('fastMode').checked);
    formData.append('gpu_mode', document.getElementById('gpuMode').checked);
    
    return formData;
}

function validateInputs() {
    if (!foregroundFileId) {
        showAlert('Seleziona il video Call to Action prima di procedere', 'error');
        return false;
    }
    
    if (!backgroundFileId) {
        showAlert('Seleziona il video di sfondo prima di procedere', 'error');
        return false;
    }
    
    return true;
}

function startProcessing() {
    document.getElementById('processBtn').style.display = 'none';
    document.getElementById('stopBtn').style.display = 'inline-block';
    document.getElementById('progressContainer').classList.add('active');
    document.getElementById('resultContainer').classList.remove('active');
    
    startProgressMonitoring();
}

function startProgressMonitoring() {
    processingInterval = setInterval(async () => {
        if (!currentJobId) return;
        
        try {
            const response = await fetch(`/api/jobs/${currentJobId}`);
            if (response.ok) {
                const job = await response.json();
                updateProgress(job);
                
                if (job.status === 'completed') {
                    clearInterval(processingInterval);
                    showResult(job.output_file);
                } else if (job.status === 'error') {
                    clearInterval(processingInterval);
                    showAlert('Errore durante l\'elaborazione: ' + job.error, 'error');
                    resetUI();
                }
            }
        } catch (error) {
            console.error('Errore nel monitoraggio:', error);
        }
    }, 2000);
}

function updateProgress(job) {
    document.getElementById('progressFill').style.width = job.progress + '%';
    document.getElementById('statusMessage').textContent = job.message;
}

function showResult(outputFile) {
    document.getElementById('progressContainer').classList.remove('active');
    document.getElementById('resultContainer').classList.add('active');
    document.getElementById('resultVideo').src = outputFile;
    
    resetUI();
    showAlert('Video elaborato con successo!', 'success');
}

function stopProcessing() {
    if (processingInterval) {
        clearInterval(processingInterval);
        processingInterval = null;
    }
    
    if (currentJobId) {
        fetch(`/api/jobs/${currentJobId}`, { method: 'DELETE' })
            .catch(error => console.error('Errore nell\'eliminazione del job:', error));
        currentJobId = null;
    }
    
    document.getElementById('progressContainer').classList.remove('active');
    resetUI();
    showAlert('Elaborazione interrotta', 'info');
}

function resetUI() {
    document.getElementById('processBtn').style.display = 'inline-block';
    document.getElementById('stopBtn').style.display = 'none';
}

// Download and Project Functions
async function downloadVideo() {
    if (currentJobId) {
        try {
            const response = await fetch(`/api/download/${currentJobId}`);
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `video_processed_${currentJobId}.mp4`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                showAlert('Download avviato!', 'success');
            } else {
                throw new Error('Errore nel download');
            }
        } catch (error) {
            showAlert('Errore nel download: ' + error.message, 'error');
        }
    }
}

function newProject() {
    // Reset file IDs
    foregroundFileId = null;
    backgroundFileId = null;
    currentJobId = null;
    
    // Reset file info displays
    document.getElementById('foregroundInfo').classList.remove('active');
    document.getElementById('backgroundInfo').classList.remove('active');
    
    // Reset containers
    document.getElementById('resultContainer').classList.remove('active');
    document.getElementById('progressContainer').classList.remove('active');
    
    // Reset form inputs
    document.getElementById('foregroundFile').value = '';
    document.getElementById('backgroundFile').value = '';
    document.getElementById('audioMode').value = 'synced';
    document.getElementById('fastMode').checked = true;
    document.getElementById('gpuMode').checked = false;
    
    // Reset sliders
    const sliders = [
        { id: 'startTime', value: 0 },
        { id: 'duration', value: 5 },
        { id: 'xPos', value: 0 },
        { id: 'yPos', value: 0 },
        { id: 'scale', value: 1.0 },
        { id: 'opacity', value: 1.0 }
    ];
    
    sliders.forEach(slider => {
        document.getElementById(slider.id).value = slider.value;
        updateValue(slider.id, slider.value);
    });
    
    resetUI();
    showAlert('Nuovo progetto creato', 'success');
}

// Alert System
function showAlert(message, type = 'info') {
    const alertContainer = getOrCreateAlertContainer();
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        <span>${message}</span>
        <button class="alert-close">&times;</button>
    `;
    
    // Add close button listener
    const closeBtn = alert.querySelector('.alert-close');
    closeBtn.addEventListener('click', () => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    });
    
    alertContainer.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    }, 5000);
    
    console.log(`Alert (${type}): ${message}`);
}

function getOrCreateAlertContainer() {
    let container = document.getElementById('alertContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'alertContainer';
        container.className = 'alert-container';
        document.body.appendChild(container);
    }
    return container;
}

function closeAlert(button) {
    const alert = button.parentNode;
    if (alert.parentNode) {
        alert.parentNode.removeChild(alert);
    }
}

// Menu Functions
function navigateToSection(sectionId) {
    // Smooth scroll to section (if implementing multiple sections)
    console.log(`Navigating to section: ${sectionId}`);
}

// Utility Functions
function formatFileSize(bytes) {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
}

function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Keyboard Shortcuts
document.addEventListener('keydown', function(event) {
    // Escape key closes sidebar
    if (event.key === 'Escape') {
        const sidebar = document.getElementById('sidebar');
        const hamburger = document.querySelector('.hamburger');
        sidebar.classList.remove('active');
        hamburger.classList.remove('active');
    }
    
    // Ctrl+N for new project
    if (event.ctrlKey && event.key === 'n') {
        event.preventDefault();
        newProject();
    }
});

// Export functions for global access
window.toggleSidebar = toggleSidebar;
window.handleDrop = handleDrop;
window.handleFileSelect = handleFileSelect;
window.updateValue = updateValue;
window.previewVideo = previewVideo;
window.processVideo = processVideo;
window.stopProcessing = stopProcessing;
window.downloadVideo = downloadVideo;
window.newProject = newProject;
window.closeAlert = closeAlert;
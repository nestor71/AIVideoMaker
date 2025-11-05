// Global Variables
let foregroundFileId = null;
let backgroundFileId = null;
let logoFileId = null;
let foregroundFileName = null;
let backgroundFileName = null;
let logoFileName = null;
let currentJobId = null;
let currentVideoName = null;
let processingInterval = null;
let lastReceivedProgress = -1;  // Track last progress to debug updates

// Initialize App
document.addEventListener('DOMContentLoaded', async function() {
    console.log('🚀 Modern AI Video Maker v2.0 - Initializing with preview...');
    
    try {
        initializeEventListeners();
        console.log('✅ Event listeners initialized');
        
        initializeSliders();
        console.log('✅ Sliders initialized');
        
        initializeAdvancedControls();
        console.log('✅ Advanced controls initialized');
        
        // Load saved settings
        await loadSettings();
        console.log('✅ Settings loaded');
        
        // Initialize auto-save for settings
        initializeSettingsAutoSave();
        console.log('✅ Settings auto-save initialized');
        
        console.log('🎉 All initialization completed successfully!');
    } catch (error) {
        console.error('❌ Initialization error:', error);
    }
});

// Event Listeners
function initializeEventListeners() {
    console.log('🔧 Setting up modern event listeners...');
    
    // File input listeners
    const ctaFile = document.getElementById('ctaFile');
    const mainVideoFile = document.getElementById('mainVideoFile');
    const logoFile = document.getElementById('logoFile');
    
    console.log('Found file inputs:', {
        ctaFile: !!ctaFile,
        mainVideoFile: !!mainVideoFile,
        logoFile: !!logoFile
    });
    
    if (ctaFile) {
        ctaFile.addEventListener('change', (e) => handleFileSelect(e, 'foreground'));
        console.log('✅ CTA file listener added');
    } else {
        console.log('❌ CTA file input not found');
    }
    
    if (mainVideoFile) {
        mainVideoFile.addEventListener('change', (e) => handleFileSelect(e, 'background'));
        console.log('✅ Main video file listener added');
    } else {
        console.log('❌ Main video file input not found');
    }
    
    if (logoFile) {
        logoFile.addEventListener('change', (e) => handleFileSelect(e, 'logo'));
        console.log('✅ Logo file listener added');
    } else {
        console.log('❌ Logo file input not found');
    }
    
    // Close sidebar when clicking outside
    document.addEventListener('click', handleOutsideClick);
    
    // Drag and drop listeners
    setupDragAndDrop();
    
    // Initialize default values
    updateValue('startTime', 5);
    updateValue('duration', 10);
    updateValue('xPos', 0);
    updateValue('yPos', 0);
    updateValue('scale', 1.0);
}

// Initialize Sliders
function initializeSliders() {
    const sliders = [
        { id: 'startTime', defaultValue: 5 },
        { id: 'duration', defaultValue: 10 },
        { id: 'xPos', defaultValue: 0 },
        { id: 'yPos', defaultValue: 0 },
        { id: 'scale', defaultValue: 1.0 }
    ];
    
    sliders.forEach(slider => {
        const element = document.getElementById(slider.id);
        if (element) {
            element.value = slider.defaultValue;
            updateValue(slider.id, slider.defaultValue);
        }
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
    
    if (sidebar && hamburger && 
        !sidebar.contains(event.target) && 
        !hamburger.contains(event.target)) {
        sidebar.classList.remove('active');
        hamburger.classList.remove('active');
    }
}

// Tab Functions
function showTab(tabName) {
    // Hide all tab panes
    const tabPanes = document.querySelectorAll('.tab-pane');
    tabPanes.forEach(pane => pane.classList.remove('active'));
    
    // Remove active class from all tab buttons
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => btn.classList.remove('active'));
    
    // Show selected tab pane
    const selectedPane = document.getElementById(tabName + 'Tab');
    if (selectedPane) {
        selectedPane.classList.add('active');
    }
    
    // Add active class to clicked tab button
    const clickedBtn = event.target.closest('.tab-btn');
    if (clickedBtn) {
        clickedBtn.classList.add('active');
    }
    
    console.log('Switched to tab:', tabName);
    
    // Initialize preview if preview tab is shown
    if (tabName === 'preview') {
        setTimeout(() => {
            initializePreview();
        }, 100);
    }
}

// Drag and Drop Functions
function setupDragAndDrop() {
    const ctaUpload = document.getElementById('ctaUpload');
    const mainVideoUpload = document.getElementById('mainVideoUpload');
    const logoUpload = document.getElementById('logoUpload');
    const transcriptionVideoUpload = document.getElementById('transcriptionVideoUpload');

    // Tab Logo e CTA upload areas
    const logoTabMainVideoUpload = document.getElementById('logoTabMainVideoUpload');
    const logoAdvancedUpload = document.getElementById('logoAdvancedUpload');
    const ctaAdvancedUpload = document.getElementById('ctaAdvancedUpload');

    console.log('🔧 Setting up drag and drop...');
    console.log('Found elements:', {
        ctaUpload: !!ctaUpload,
        mainVideoUpload: !!mainVideoUpload,
        logoUpload: !!logoUpload,
        transcriptionVideoUpload: !!transcriptionVideoUpload,
        logoTabMainVideoUpload: !!logoTabMainVideoUpload,
        logoAdvancedUpload: !!logoAdvancedUpload,
        ctaAdvancedUpload: !!ctaAdvancedUpload
    });

    if (ctaUpload) {
        setupUploadArea(ctaUpload, 'ctaFile', 'foreground');
        console.log('✅ CTA upload area configured');
    } else {
        console.log('❌ CTA upload area not found');
    }

    if (mainVideoUpload) {
        setupUploadArea(mainVideoUpload, 'mainVideoFile', 'background');
        console.log('✅ Main video upload area configured');
    } else {
        console.log('❌ Main video upload area not found');
    }

    if (logoUpload) {
        setupUploadArea(logoUpload, 'logoFile', 'logo');
        console.log('✅ Logo upload area configured');
    } else {
        console.log('❌ Logo upload area not found');
    }

    if (transcriptionVideoUpload) {
        setupUploadArea(transcriptionVideoUpload, 'transcriptionVideoFile', 'transcription');
        console.log('✅ Transcription video upload area configured');
    } else {
        console.log('❌ Transcription video upload area not found');
    }

    // Setup drag-and-drop for Logo tab areas
    if (logoTabMainVideoUpload) {
        setupUploadArea(logoTabMainVideoUpload, 'logoTabMainVideoFile', 'background-logo-tab');
        console.log('✅ Logo tab main video upload area configured');
    } else {
        console.log('❌ Logo tab main video upload area not found');
    }

    if (logoAdvancedUpload) {
        setupUploadArea(logoAdvancedUpload, 'logoAdvancedFile', 'logo-advanced');
        console.log('✅ Logo advanced upload area configured');
    } else {
        console.log('❌ Logo advanced upload area not found');
    }

    if (ctaAdvancedUpload) {
        setupUploadArea(ctaAdvancedUpload, 'ctaAdvancedFile', 'cta-advanced');
        console.log('✅ CTA advanced upload area configured');
    } else {
        console.log('❌ CTA advanced upload area not found');
    }
}

function setupUploadArea(uploadArea, fileInputId, type) {
    uploadArea.addEventListener('click', (e) => {
        // Don't trigger if clicking on video controls, buttons, or the video itself
        if (e.target.tagName === 'VIDEO' ||
            e.target.tagName === 'BUTTON' ||
            e.target.closest('button') ||
            e.target.classList.contains('preview-video-overlay')) {
            return;
        }

        console.log(`🖱️ ${type} area clicked`);
        const fileInput = document.getElementById(fileInputId);
        console.log(`🔍 File input found:`, !!fileInput, 'ID:', fileInputId);
        if (fileInput) {
            fileInput.click();
            console.log(`✅ Triggered click on file input ${fileInputId}`);
        } else {
            console.error(`❌ File input ${fileInputId} not found!`);
        }
    });
    
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', (e) => handleDrop(e, type));
}

function handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('dragover');
}

function handleDragLeave(event) {
    event.currentTarget.classList.remove('dragover');
}

function handleDrop(event, type) {
    event.preventDefault();
    event.currentTarget.classList.remove('dragover');

    console.log('Drop detected for type:', type);

    const files = event.dataTransfer.files;
    if (files.length > 0) {
        console.log('Processing file:', files[0].name);

        // Special handling for tabs with event listeners
        if (type === 'transcription') {
            const fileInput = document.getElementById('transcriptionVideoFile');
            if (fileInput) {
                // Create a new DataTransfer to assign the file
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(files[0]);
                fileInput.files = dataTransfer.files;

                // Trigger the change event
                const changeEvent = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(changeEvent);
                console.log('✅ Transcription file assigned and change event triggered');
            }
        } else if (type === 'background-logo-tab') {
            // Video principale nella tab Logo e CTA
            const fileInput = document.getElementById('logoTabMainVideoFile');
            if (fileInput) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(files[0]);
                fileInput.files = dataTransfer.files;

                const changeEvent = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(changeEvent);
                console.log('✅ Logo tab main video file assigned and change event triggered');
            }
        } else if (type === 'logo-advanced') {
            // Logo nella tab Logo e CTA
            const fileInput = document.getElementById('logoAdvancedFile');
            if (fileInput) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(files[0]);
                fileInput.files = dataTransfer.files;

                const changeEvent = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(changeEvent);
                console.log('✅ Logo advanced file assigned and change event triggered');
            }
        } else if (type === 'cta-advanced') {
            // CTA nella tab Logo e CTA
            const fileInput = document.getElementById('ctaAdvancedFile');
            if (fileInput) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(files[0]);
                fileInput.files = dataTransfer.files;

                const changeEvent = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(changeEvent);
                console.log('✅ CTA advanced file assigned and change event triggered');
            }
        } else {
            handleFileUpload(files[0], type);
        }
    }
}

// File Handling Functions
function handleFileSelect(event, type) {
    const file = event.target.files[0];
    if (file) {
        console.log('File selected:', file.name, 'type:', type);
        handleFileUpload(file, type);
    } else {
        console.log('No file selected (user cancelled)');
    }
    
    // Reset the file input to allow selecting the same file again
    event.target.value = '';
}

async function handleFileUpload(file, type) {
    console.log('Starting file upload for:', file.name, 'type:', type);
    
    if (!validateFileType(file, type)) {
        showAlert('Formato file non supportato.', 'error');
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
            handleUploadSuccess(result, type, file);
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

function validateFileType(file, type) {
    const fileName = file.name.toLowerCase();
    
    if (type === 'logo') {
        const allowedImageTypes = ['.png', '.jpg', '.jpeg', '.svg', '.gif'];
        return allowedImageTypes.some(ext => fileName.endsWith(ext));
    } else {
        const allowedVideoTypes = ['.mp4', '.avi', '.mov', '.mkv'];
        return allowedVideoTypes.some(ext => fileName.endsWith(ext));
    }
}

function handleUploadSuccess(result, type, file) {
    // Store file IDs and names globally
    if (type === 'foreground') {
        foregroundFileId = result.file_id;
        foregroundFileName = result.filename;
        currentVideoName = result.filename;
    } else if (type === 'background') {
        backgroundFileId = result.file_id;
        backgroundFileName = result.filename;
    } else if (type === 'logo') {
        logoFileId = result.file_id;
        logoFileName = result.filename;
    }
    
    // Update ALL relevant UI elements across tabs
    updateAllFileDisplays(result, type, file);
    
    // Save settings with new file IDs
    saveSettings();
    
    // Only show alert if not already showing one (prevent duplicates)
    if (!window.lastUploadAlert || Date.now() - window.lastUploadAlert > 1000) {
        showAlert(`File ${result.filename} caricato con successo!`, 'success');
        window.lastUploadAlert = Date.now();
    }
}

function updateAllFileDisplays(result, type, file) {
    const fileNameMap = {
        'foreground': 'ctaName',
        'background': 'mainVideoName',
        'logo': 'logoName'
    };
    
    const fileInfoMap = {
        'foreground': 'ctaInfo',
        'background': 'mainVideoInfo',
        'logo': 'logoInfo'
    };
    
    const previewMap = {
        'foreground': 'ctaPreview',
        'background': 'mainVideoPreview',
        'logo': 'logoPreview'
    };
    
    // Update filename in all tabs
    const nameElement = document.getElementById(fileNameMap[type]);
    if (nameElement) {
        nameElement.textContent = result.filename;
    }
    
    // Show file info in main tab
    const infoElement = document.getElementById(fileInfoMap[type]);
    if (infoElement) {
        infoElement.classList.add('active');
    }
    
    // Update preview in main tab (both regular and overlay)
    const previewElement = document.getElementById(previewMap[type]);
    const previewOverlayMap = {
        'foreground': 'ctaPreviewOverlay',
        'background': 'mainVideoPreviewOverlay',
        'logo': 'logoPreviewOverlay'
    };
    const advancedPreviewOverlayMap = {
        'foreground': 'ctaAdvancedPreviewOverlay',
        'logo': 'logoAdvancedPreviewOverlay'
    };
    const previewOverlay = document.getElementById(previewOverlayMap[type]);
    const advancedPreviewOverlay = document.getElementById(advancedPreviewOverlayMap[type]);
    
    if (file) {
        const fileURL = URL.createObjectURL(file);
        
        // Update regular preview (keep for compatibility but don't show)
        if (previewElement) {
            if (type === 'logo') {
                const img = previewElement.querySelector('.preview-image');
                if (img) {
                    img.src = fileURL;
                    // DON'T add 'active' class to keep it hidden
                }
            } else {
                const video = previewElement.querySelector('.preview-video');
                if (video) {
                    video.src = fileURL;
                    // DON'T add 'active' class to keep it hidden
                }
            }
        }
        
        // Update overlay preview (new feature)
        if (previewOverlay) {
            if (type === 'logo') {
                const overlayImg = previewOverlay.querySelector('.preview-image-overlay');
                if (overlayImg) {
                    overlayImg.src = fileURL;
                    overlayImg.onload = function() {
                        URL.revokeObjectURL(fileURL);
                    };
                    previewOverlay.classList.add('active');
                }
            } else {
                const overlayVideo = previewOverlay.querySelector('.preview-video-overlay');
                if (overlayVideo) {
                    overlayVideo.src = fileURL;
                    overlayVideo.onloadeddata = function() {
                        URL.revokeObjectURL(fileURL);

                        // Update interactive preview canvas if this is the main video
                        if (type === 'background') {
                            console.log('🎬 Main video loaded, updating interactive preview canvas');
                            updateCanvasWithMainVideo();

                            // If logo/CTA already loaded, show them in preview
                            if (logoFileId) {
                                console.log('📌 Logo already loaded, showing in preview');
                                const logoElement = document.getElementById('draggableLogo');
                                if (logoElement && logoElement.querySelector('img').src) {
                                    logoElement.style.display = 'block';
                                    positionElementFromInputs('logo');
                                }
                            }
                            if (foregroundFileId) {
                                console.log('📌 CTA already loaded, showing in preview');
                                const ctaElement = document.getElementById('draggableCTA');
                                if (ctaElement && ctaElement.querySelector('video').src) {
                                    ctaElement.style.display = 'block';
                                    positionElementFromInputs('cta');
                                }
                            }
                        }
                    };
                    previewOverlay.style.display = 'flex';

                    // Nascondi area upload per mostrare solo il video
                    if (type === 'background') {
                        const uploadArea = document.getElementById('mainVideoUpload');
                        const uploadContent = uploadArea?.querySelector('.upload-content');
                        if (uploadContent) {
                            uploadContent.style.display = 'none';
                        }
                    }
                }
            }
        }
        
        // Update advanced overlay preview (new feature)
        if (advancedPreviewOverlay) {
            if (type === 'logo') {
                const advancedOverlayImg = advancedPreviewOverlay.querySelector('.preview-image-overlay');
                if (advancedOverlayImg) {
                    advancedOverlayImg.src = fileURL;
                    advancedPreviewOverlay.classList.add('active');
                }
            } else if (type === 'foreground') {
                const advancedOverlayVideo = advancedPreviewOverlay.querySelector('.preview-video-overlay');
                if (advancedOverlayVideo) {
                    advancedOverlayVideo.src = fileURL;
                    advancedPreviewOverlay.classList.add('active');
                }
            }
        }
    }
    
    // Update advanced tab upload areas
    updateAdvancedUploadAreas(result, type, file);
}

function updateAdvancedUploadAreas(result, type, file) {
    let uploadArea = null;
    
    // Find the corresponding advanced upload area
    if (type === 'logo') {
        uploadArea = document.getElementById('logoAdvancedUpload');
    } else if (type === 'foreground') {
        uploadArea = document.getElementById('ctaAdvancedUpload');
    }
    
    if (uploadArea) {
        const uploadContent = uploadArea.querySelector('.upload-content');
        const icon = uploadContent.querySelector('.upload-icon');
        const button = uploadContent.querySelector('.upload-btn');
        
        // Update icon and button to show success
        if (icon && button) {
            icon.className = 'fas fa-check-circle upload-icon';
            icon.style.color = '#10b981';
            button.innerHTML = '<i class="fas fa-check"></i> ' + result.filename;
            
            uploadArea.style.borderColor = '#10b981';
            uploadArea.style.background = 'rgba(16, 185, 129, 0.1)';
        }
    }
}

function showLoadingState(type, loading) {
    const uploadAreaMap = {
        'foreground': 'ctaUpload',
        'background': 'mainVideoUpload',
        'logo': 'logoUpload'
    };
    
    const uploadArea = document.getElementById(uploadAreaMap[type]);
    
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
        // Restore original icon based on type
        if (type === 'logo') {
            icon.className = 'fas fa-image';
        } else {
            icon.className = type === 'foreground' ? 'fas fa-video' : 'fas fa-cloud-upload-alt';
        }
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
    
    showAlert('Funzione anteprima disponibile presto!', 'info');
}

async function processVideo() {
    console.log('processVideo() called');
    console.log('Current foregroundFileId:', foregroundFileId);
    console.log('Current backgroundFileId:', backgroundFileId);
    console.log('Type of foregroundFileId:', typeof foregroundFileId);
    console.log('Type of backgroundFileId:', typeof backgroundFileId);
    
    if (!validateInputs()) {
        console.log('Validation failed - stopping process');
        return;
    }
    console.log('Validation passed - showing confirmation modal');
    
    // Show confirmation modal instead of processing directly
    showProcessingConfirmModal();
}

function createProcessingFormData() {
    console.log('createProcessingFormData() started');
    const formData = new FormData();
    formData.append('foreground_file_id', foregroundFileId);
    formData.append('background_file_id', backgroundFileId);
    console.log('Basic formData created');
    
    // Use CTA settings from UI
    const ctaStartTime = parseFloat(document.getElementById('ctaStartTime')?.value || 5);
    const ctaEndTimeValue = document.getElementById('ctaEndTime')?.value;
    const ctaDuration = ctaEndTimeValue && ctaEndTimeValue.trim() !== '' ? 
        parseFloat(ctaEndTimeValue) - ctaStartTime : 10;
    const ctaPosition = document.getElementById('ctaPosition')?.value || 'center';
    const ctaSize = parseInt(document.getElementById('ctaSize')?.value || 20) / 100;
    
    // Convert position to coordinates
    console.log('Getting CTA coordinates for position:', ctaPosition);
    const ctaCoords = getPositionCoordinates(ctaPosition, 1920, 1080, false);
    console.log('CTA coordinates:', ctaCoords);
    
    formData.append('start_time', ctaStartTime);
    formData.append('duration', ctaDuration);
    formData.append('audio_mode', document.getElementById('audioMode')?.value || 'synced');
    formData.append('cta_x_pos', ctaCoords.x);
    formData.append('cta_y_pos', ctaCoords.y);
    formData.append('cta_scale', ctaSize);
    formData.append('opacity', 1.0);
    formData.append('fast_mode', true);
    formData.append('gpu_mode', false);
    
    // Add logo settings
    if (logoFileId) {
        formData.append('logo_file_id', logoFileId);
        const logoPosition = document.getElementById('logoPosition')?.value || 'top-left';
        const logoSize = parseInt(document.getElementById('logoSize')?.value || 10) / 100;
        const logoCoords = getPositionCoordinates(logoPosition, 1920, 1080, true);
        
        formData.append('logo_x_pos', logoCoords.x);
        formData.append('logo_y_pos', logoCoords.y);
        formData.append('logo_scale', logoSize);
    }
    
    return formData;
}

function validateInputs() {
    console.log('validateInputs() called');
    console.log('foregroundFileId:', foregroundFileId);
    console.log('backgroundFileId:', backgroundFileId);
    
    // PRIMA PRIORITÀ: Controlla che i file siano caricati
    const missingFiles = [];
    
    if (!foregroundFileId || foregroundFileId === null || foregroundFileId === undefined || foregroundFileId.toString().trim() === '') {
        console.log('Missing foreground file - stopping validation');
        missingFiles.push({ name: 'Video Call to Action', icon: 'fas fa-video', description: 'Il video che apparirà sovrapposto' });
    }
    
    if (!backgroundFileId || backgroundFileId === null || backgroundFileId === undefined || backgroundFileId.toString().trim() === '') {
        console.log('Missing background file - stopping validation');
        missingFiles.push({ name: 'Video Principale', icon: 'fas fa-film', description: 'Il video di base su cui lavorare' });
    }
    
    if (missingFiles.length > 0) {
        console.log('Missing files detected:', missingFiles.map(f => f.name));
        showMissingFilesModal(missingFiles);
        return false;
    }
    
    // VALIDAZIONE TIPO FILE: Controlla che i file caricati siano del tipo corretto
    const fileTypeErrors = [];
    
    if (foregroundFileId && foregroundFileName) {
        const videoExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm'];
        const extension = '.' + foregroundFileName.split('.').pop().toLowerCase();
        if (!videoExtensions.includes(extension)) {
            console.log('Invalid foreground file type:', extension);
            fileTypeErrors.push({
                name: 'Video Call to Action',
                fileName: foregroundFileName,
                expectedType: 'Video (.mp4, .avi, .mov, .mkv)',
                actualType: 'File ' + extension
            });
        }
    }
    
    if (backgroundFileId && backgroundFileName) {
        const videoExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm'];
        const extension = '.' + backgroundFileName.split('.').pop().toLowerCase();
        if (!videoExtensions.includes(extension)) {
            console.log('Invalid background file type:', extension);
            fileTypeErrors.push({
                name: 'Video Principale', 
                fileName: backgroundFileName,
                expectedType: 'Video (.mp4, .avi, .mov, .mkv)',
                actualType: 'File ' + extension
            });
        }
    }
    
    if (fileTypeErrors.length > 0) {
        console.log('File type errors detected:', fileTypeErrors);
        showFileTypeErrorModal(fileTypeErrors);
        return false;
    }
    
    // SECONDA PRIORITÀ: Solo se i file sono caricati e validi, controlla le funzionalità
    console.log('Files are present, checking features...');
    const toggles = [
        'logoOverlay',
        'callToAction',
        'videoTranscription',
        'audioTranslation',
        'coverGeneration',
        'metadataGeneration',
        'youtubeUpload'
    ];
    
    const selectedToggles = toggles.filter(toggleId => {
        const toggle = document.getElementById(toggleId);
        return toggle && toggle.checked;
    });
    
    if (selectedToggles.length === 0) {
        console.log('Files present but no features selected - showing modal');
        showValidationModal();
        return false;
    }
    
    console.log('Validation successful - Files present and features selected:', selectedToggles);
    return true;
}

// Mostra modal per errori di tipo file
function showFileTypeErrorModal(fileTypeErrors) {
    console.log('Showing file type error modal with errors:', fileTypeErrors);
    
    const modalHtml = `
    <div class="modal" id="fileTypeErrorModal" style="display: flex;">
        <div class="modal-content validation-modal-content">
            <div class="modal-header validation-header">
                <div class="validation-icon">
                    <i class="fas fa-exclamation-triangle" style="color: #f59e0b;"></i>
                </div>
                <h2>Tipo File Non Valido</h2>
            </div>
            
            <div class="modal-body validation-body">
                <p>I seguenti file non sono del tipo corretto per l'elaborazione video:</p>
                
                <div class="file-type-errors">
                    ${fileTypeErrors.map(error => `
                        <div class="file-error-item">
                            <div class="file-error-header">
                                <i class="fas fa-file-video"></i>
                                <strong>${error.name}</strong>
                            </div>
                            <div class="file-error-details">
                                <div class="file-name">File: ${error.fileName}</div>
                                <div class="file-types">
                                    <span class="actual-type">Tipo Attuale: ${error.actualType}</span>
                                    <span class="expected-type">Richiesto: ${error.expectedType}</span>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
                
                <div class="file-type-help">
                    <h4>Come risolvere:</h4>
                    <ul>
                        <li><i class="fas fa-upload"></i> Carica file video nei formati supportati</li>
                        <li><i class="fas fa-check-circle"></i> Per Call to Action e Video Principale usa: MP4, AVI, MOV, MKV</li>
                        <li><i class="fas fa-image"></i> Per Logo usa: PNG, JPG, SVG</li>
                    </ul>
                </div>
            </div>
            
            <div class="modal-footer validation-footer">
                <button class="btn-primary" onclick="closeFileTypeErrorModal()">
                    <i class="fas fa-check"></i> Ho Capito
                </button>
            </div>
        </div>
    </div>`;
    
    // Remove existing modal if present
    const existingModal = document.getElementById('fileTypeErrorModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

function closeFileTypeErrorModal() {
    const modal = document.getElementById('fileTypeErrorModal');
    if (modal) {
        modal.remove();
    }
}

// Validation Modal Functions
function showValidationModal() {
    const modal = document.getElementById('validationModal');
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeValidationModal() {
    const modal = document.getElementById('validationModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

function goToFeatures() {
    closeValidationModal();
    
    // Scroll to feature toggles section
    const featureSection = document.querySelector('.feature-toggles');
    if (featureSection) {
        featureSection.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
        });
        
        // Evidenzia visivamente la sezione
        featureSection.style.border = '2px solid #f59e0b';
        featureSection.style.borderRadius = '12px';
        featureSection.style.boxShadow = '0 0 0 4px rgba(245, 158, 11, 0.2)';
        
        // Rimuovi l'evidenziazione dopo 5 secondi
        setTimeout(() => {
            featureSection.style.border = '';
            featureSection.style.borderRadius = '';
            featureSection.style.boxShadow = '';
        }, 5000);
    }
}

// Show processing modal with details
function showProcessingModal(message, percentage, timeRemaining) {
    const modal = document.getElementById('processingModal');
    const percentageEl = document.getElementById('processingPercentage');
    const messageEl = document.getElementById('processingMessage');
    const timeEl = document.getElementById('processingTime');

    if (modal) {
        modal.classList.add('active');
    }
    if (percentageEl) {
        percentageEl.textContent = percentage + '%';
    }
    if (messageEl) {
        messageEl.textContent = message;
    }
    if (timeEl) {
        timeEl.textContent = timeRemaining;
    }
}

// Update processing modal
function updateProcessingModal(message, percentage, timeRemaining) {
    const percentageEl = document.getElementById('processingPercentage');
    const messageEl = document.getElementById('processingMessage');
    const timeEl = document.getElementById('processingTime');

    if (percentageEl) {
        percentageEl.textContent = percentage + '%';
    }
    if (messageEl) {
        messageEl.textContent = message;
    }
    if (timeEl && timeRemaining) {
        timeEl.textContent = timeRemaining;
    }
}

// Hide processing modal
function hideProcessingModal() {
    const modal = document.getElementById('processingModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function startProcessing() {
    console.log('🚀 startProcessing called!');
    const processingModal = document.getElementById('processingModal');

    console.log('🔍 Processing modal found:', !!processingModal);

    // Show processing modal
    if (processingModal) {
        processingModal.classList.add('active');
        console.log('✅ Showing processing modal');
    }

    startProgressMonitoring();
    console.log('🎯 Progress monitoring started');
}

function startProgressMonitoring() {
    // Clear any existing interval first
    if (processingInterval) {
        clearInterval(processingInterval);
    }
    
    // Initialize with starting message
    updateProgressWithMessage(0, "Avvio elaborazione video...");
    
    // Wait a moment before starting polling to let backend initialize
    setTimeout(() => {
        processingInterval = setInterval(async () => {
        if (!currentJobId) {
            console.log('⚠️  No currentJobId, stopping progress monitoring');
            return;
        }
        
        console.log('🔍 Checking progress for job:', currentJobId);
        
        try {
            const response = await fetch(`/api/jobs/${currentJobId}`);
            console.log('📡 Progress check response status:', response.status);
            
            if (!response.ok) {
                if (response.status === 404) {
                    console.log('⚠️ Job not found yet, waiting...');
                    return; // Job might not be created yet, continue polling
                } else {
                    console.error('❌ API error:', response.status, response.statusText);
                    return;
                }
            }
            
            if (response.ok) {
                const job = await response.json();
                console.log('📊 Raw response from /api/jobs:', job);
                console.log('🔢 Progress value type:', typeof job.progress, 'value:', job.progress);
                console.log('📝 Message value:', typeof job.message, 'value:', job.message);
                console.log('📋 Job status:', job.status);
                console.log('🆔 Job ID match:', job.job_id === currentJobId);
                
                // Use backend message if available, otherwise generate one
                const progress = job.progress || 0;
                let statusMessage = job.message || "Elaborazione in corso...";
                
                // Debug progress changes
                if (progress !== lastReceivedProgress) {
                    console.log(`🔄 Progress changed: ${lastReceivedProgress}% → ${progress}%`);
                    lastReceivedProgress = progress;
                } else {
                    console.log(`⏸️ Progress unchanged: ${progress}%`);
                }
                
                // If backend doesn't provide a message, generate one based on progress
                if (!job.message || job.message === "In attesa di elaborazione...") {
                    if (progress < 5) {
                        statusMessage = "Inizializzazione elaborazione...";
                    } else if (progress < 15) {
                        statusMessage = "Caricamento file video...";
                    } else if (progress < 50) {
                        statusMessage = `Applicazione effetti chroma key... (${Math.round(progress)}%)`;
                    } else if (progress < 85) {
                        statusMessage = `Processamento video... (${Math.round(progress)}%)`;
                    } else if (progress < 95) {
                        statusMessage = `Ottimizzazione qualità... (${Math.round(progress)}%)`;
                    } else if (progress < 100) {
                        statusMessage = "Finalizzazione output...";
                    }
                }
                
                // Always update with real progress from backend
                console.log(`🎯 Updating progress to ${progress}% with message: "${statusMessage}"`);
                updateProgressWithMessage(progress, statusMessage);
                
                if (job.status === 'completed') {
                    clearInterval(processingInterval);
                    processingInterval = null;

                    // Show completion message
                    updateProgressWithMessage(100, "✅ Elaborazione completata!");

                    setTimeout(() => {
                        console.log('🎉 Job completed! Output file:', job.output_file);
                        showResult(job);
                    }, 500);
                    
                } else if (job.status === 'error') {
                    clearInterval(processingInterval);
                    processingInterval = null;

                    // Hide processing modal
                    hideProcessingModal();

                    // Reset progress timing
                    progressStartTime = null;
                    lastProgressUpdate = 0;

                    showAlert('Errore durante l\'elaborazione: ' + job.error, 'error');
                    resetUI();
                    return;
                }
            }
        } catch (error) {
            console.error('Errore nel monitoraggio:', error);
        }
        }, 300);  // Check every 300ms for real-time updates
    }, 500);  // Wait 500ms before starting polling
}

function updateProgress(job) {
    console.log('🔄 updateProgress called with:', job);
    updateProgressWithMessage(job.progress, job.message || 'Elaborazione in corso...');
}

// Track progress timing for ETA calculation
let progressStartTime = null;
let lastProgressUpdate = 0;

function updateProgressWithMessage(progress, message) {
    console.log('🔄 updateProgressWithMessage called with progress:', progress, 'message:', message);

    // Initialize start time on first call
    if (!progressStartTime && progress > 0) {
        progressStartTime = Date.now();
    }

    // Calculate estimated time remaining
    let timeRemaining = 'Calcolo tempo rimanente...';
    if (progressStartTime && progress > 5 && progress < 100) {
        const elapsedMs = Date.now() - progressStartTime;
        const progressDone = progress / 100;
        const estimatedTotalMs = elapsedMs / progressDone;
        const remainingMs = estimatedTotalMs - elapsedMs;

        const remainingMinutes = Math.floor(remainingMs / 60000);
        const remainingSeconds = Math.floor((remainingMs % 60000) / 1000);

        if (remainingMinutes > 0) {
            timeRemaining = `Tempo rimanente: circa ${remainingMinutes}m ${remainingSeconds}s`;
        } else if (remainingSeconds > 0) {
            timeRemaining = `Tempo rimanente: circa ${remainingSeconds} secondi`;
        } else {
            timeRemaining = 'Quasi completato...';
        }
    }

    // Update processing modal
    updateProcessingModal(message, Math.round(progress), timeRemaining);

    lastProgressUpdate = progress;
}

function showResult(job) {
    console.log('🎬 Showing result with job:', job);

    // Hide processing modal
    hideProcessingModal();

    // Reset progress timing
    progressStartTime = null;
    lastProgressUpdate = 0;

    resetUI();

    // Prepara dati per il modal
    const modalData = {
        job_id: job.job_id || currentJobId,
        processing_type: 'Elaborazione Video',
        video_name: currentVideoName || 'Video',
        start_time: job.start_time || new Date().toISOString(),
        end_time: job.end_time || new Date().toISOString(),
        output_files: job.output_files || [job.output_file]
    };

    // Mostra modal di completamento
    if (typeof showProcessingCompleteModal === 'function') {
        showProcessingCompleteModal(modalData);
    } else {
        // Fallback se la funzione non è disponibile
        showAlert('✅ Video elaborato con successo! Trovi il file nel File Manager.', 'success');
    }

    console.log('✅ Video processed successfully:', job.output_file);
}

// Open processed video preview modal
function openProcessedVideoModal(videoUrl) {
    // Create modal HTML if it doesn't exist
    let modal = document.getElementById('processedVideoModal');
    if (!modal) {
        const modalHTML = `
            <div class="modal" id="processedVideoModal" onclick="closeProcessedVideoModal()">
                <div class="modal-content" onclick="event.stopPropagation()">
                    <div class="modal-header">
                        <h2><i class="fas fa-video"></i> Video Elaborato - Anteprima</h2>
                        <button class="modal-close-btn" onclick="closeProcessedVideoModal()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    
                    <div class="modal-body">
                        <div class="processed-video-container">
                            <video controls id="processedVideoPreview" class="processed-video">
                                Il tuo browser non supporta il video.
                            </video>
                        </div>
                        
                        <div class="processed-video-actions">
                            <button class="btn-primary" onclick="downloadVideoFromModal()">
                                <i class="fas fa-download"></i> Scarica Video
                            </button>
                            <button class="btn-secondary" onclick="closeProcessedVideoModal()">
                                <i class="fas fa-times"></i> Chiudi
                            </button>
                            <button class="btn-secondary" onclick="newProject()">
                                <i class="fas fa-plus"></i> Nuovo Progetto
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        modal = document.getElementById('processedVideoModal');
    }
    
    // Set video source and show modal
    const video = document.getElementById('processedVideoPreview');
    console.log('Setting video src to:', videoUrl);
    console.log('Video element found:', !!video);
    
    if (video) {
        console.log('🎬 Found video element:', video);
        console.log('🎬 Setting video source to:', videoUrl);
        
        // Clear any existing event listeners
        video.onloadstart = null;
        video.onloadeddata = null;
        video.oncanplay = null;
        video.onerror = null;
        video.onloadedmetadata = null;
        
        // Clear previous source
        video.removeAttribute('src');
        video.load();
        
        // Set up event listeners first
        video.onloadstart = () => {
            console.log('✅ Video load started for:', videoUrl);
        };
        
        video.onloadedmetadata = () => {
            console.log('✅ Video metadata loaded');
            console.log('📐 Video dimensions:', video.videoWidth, 'x', video.videoHeight);
            console.log('⏱️ Video duration:', video.duration);
        };
        
        video.onloadeddata = () => {
            console.log('✅ Video data loaded successfully');
            console.log('📺 Video readyState:', video.readyState);
            console.log('🌐 Video networkState:', video.networkState);
        };
        
        video.oncanplay = () => {
            console.log('✅ Video can play - ready to show');
            // Force visibility
            video.style.display = 'block';
            video.style.visibility = 'visible';
            video.style.opacity = '1';
            video.style.width = 'auto';
            video.style.height = 'auto';
            video.style.maxWidth = '100%';
            video.style.maxHeight = '70vh';
        };
        
        video.onerror = (e) => {
            console.error('❌ Video load error:', e);
            console.error('❌ Failed to load video from:', videoUrl);
            console.error('❌ Video error code:', video.error ? video.error.code : 'unknown');
            console.error('❌ Video error message:', video.error ? video.error.message : 'unknown');
            
            // Test if file exists
            fetch(videoUrl, { method: 'HEAD' })
                .then(response => {
                    console.log('🌐 Video file HTTP HEAD response:', response.status, response.statusText);
                    if (!response.ok) {
                        console.error('❌ Video file not accessible via HTTP');
                        showAlert('Il video elaborato non è accessibile. Controlla se il file esiste.', 'error');
                    } else {
                        console.log('✅ File exists but video element can\'t load it');
                        // Try setting a different way
                        setTimeout(() => {
                            video.setAttribute('src', videoUrl);
                            video.load();
                        }, 500);
                    }
                })
                .catch(err => {
                    console.error('❌ Video file fetch error:', err);
                    showAlert('Errore nel caricamento del video elaborato.', 'error');
                });
        };
        
        // Now set the source
        setTimeout(() => {
            video.setAttribute('src', videoUrl);
            console.log('🔗 Video src attribute set to:', video.getAttribute('src'));
            video.load();
        }, 200);
        
        // Debug after a moment
        setTimeout(() => {
            console.log('🔍 Video element status after 2 seconds:');
            console.log('  - src:', video.src);
            console.log('  - currentSrc:', video.currentSrc);
            console.log('  - readyState:', video.readyState);
            console.log('  - networkState:', video.networkState);
            console.log('  - error:', video.error);
            console.log('  - display:', window.getComputedStyle(video).display);
            console.log('  - visibility:', window.getComputedStyle(video).visibility);
            console.log('  - opacity:', window.getComputedStyle(video).opacity);
        }, 2000);
    }
    
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        console.log('Modal shown successfully');
    }
    
    showAlert('Video elaborato con successo! Guarda l\'anteprima prima di scaricarlo.', 'success');
}

// Close processed video modal
function closeProcessedVideoModal() {
    const modal = document.getElementById('processedVideoModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
        
        // Pause video when closing
        const video = document.getElementById('processedVideoPreview');
        if (video) {
            video.pause();
        }
    }
}

// Download video from modal
function downloadVideoFromModal() {
    downloadVideo();
    closeProcessedVideoModal();
}

// Settings persistence functions
function saveSettings() {
    const settings = {
        // Position and scaling
        xPos: document.getElementById('xPos')?.value || '0',
        yPos: document.getElementById('yPos')?.value || '0',
        scale: document.getElementById('scale')?.value || '1.0',
        
        // Audio settings
        audioMode: document.getElementById('audioMode')?.value || 'synced',
        
        // Logo settings
        logoPosition: document.getElementById('logoPosition')?.value || 'top-right',
        logoSize: document.getElementById('logoSize')?.value || '10',
        logoStartTime: document.getElementById('logoStartTime')?.value || '0',
        logoEndTime: document.getElementById('logoEndTime')?.value || '',
        
        // CTA settings
        ctaPosition: document.getElementById('ctaPosition')?.value || 'center',
        ctaSize: document.getElementById('ctaSize')?.value || '20',
        ctaStartTime: document.getElementById('ctaStartTime')?.value || '5',
        ctaEndTime: document.getElementById('ctaEndTime')?.value || '',
        
        // Chromakey settings
        chromakeyEnabled: document.getElementById('chromakeyEnabled')?.checked || true,
        
        // Quality settings
        qualityPreset: document.getElementById('qualityPreset')?.value || 'ultra',
        
        // File IDs and names - save uploaded files
        foregroundFileId: foregroundFileId,
        backgroundFileId: backgroundFileId,
        logoFileId: logoFileId,
        foregroundFileName: foregroundFileName,
        backgroundFileName: backgroundFileName,
        logoFileName: logoFileName,
        
        // Feature toggles - save functionality settings
        logoOverlay: document.getElementById('logoOverlay')?.checked || false,
        callToAction: document.getElementById('callToAction')?.checked || false,
        videoTranscription: document.getElementById('videoTranscription')?.checked || false,
        audioTranslation: document.getElementById('audioTranslation')?.checked || false,
        coverGeneration: document.getElementById('coverGeneration')?.checked || false,
        metadataGeneration: document.getElementById('metadataGeneration')?.checked || false,
        youtubeUpload: document.getElementById('youtubeUpload')?.checked || false,

        // Thumbnail Generator settings (Tab Copertina)
        coverStyle: document.getElementById('coverStyle')?.value || 'realistic',
        coverDescription: document.getElementById('coverDescription')?.value || '',
        addTextOverlay: document.getElementById('addTextOverlay')?.checked || false,
        coverMainText: document.getElementById('coverMainText')?.value || '',
        textPosition: document.getElementById('textPosition')?.value || 'center',
        textColor: document.getElementById('textColor')?.value || '#FFFFFF',
        textBgColor: document.getElementById('textBgColor')?.value || '#000000',
        textBgOpacity: document.getElementById('textBgOpacity')?.value || '70',
        frameTimestamp: document.getElementById('frameTimestamp')?.value || '5',
        currentImageSource: currentImageSource || 'ai'
    };

    // Save selected chromakey color
    const activeColor = document.querySelector('.color-option.active');
    if (activeColor) {
        settings.chromakeyColor = activeColor.getAttribute('data-color') || 'green';
    }
    
    localStorage.setItem('aiVideoMakerSettings', JSON.stringify(settings));
    console.log('Settings saved with file IDs:', {
        foregroundFileId: settings.foregroundFileId,
        backgroundFileId: settings.backgroundFileId,
        logoFileId: settings.logoFileId
    });
}

async function loadSettings() {
    const savedSettings = localStorage.getItem('aiVideoMakerSettings');
    if (!savedSettings) return;
    
    try {
        const settings = JSON.parse(savedSettings);
        
        // Apply position and scaling settings
        if (settings.xPos && document.getElementById('xPos')) {
            document.getElementById('xPos').value = settings.xPos;
            updateValue('xPos', settings.xPos);
        }
        
        if (settings.yPos && document.getElementById('yPos')) {
            document.getElementById('yPos').value = settings.yPos;
            updateValue('yPos', settings.yPos);
        }
        
        if (settings.scale && document.getElementById('scale')) {
            document.getElementById('scale').value = settings.scale;
            updateValue('scale', settings.scale);
        }
        
        // Apply audio settings
        if (settings.audioMode && document.getElementById('audioMode')) {
            document.getElementById('audioMode').value = settings.audioMode;
        }
        
        // Apply logo settings
        if (settings.logoPosition && document.getElementById('logoPosition')) {
            document.getElementById('logoPosition').value = settings.logoPosition;
        }
        
        if (settings.logoSize && document.getElementById('logoSize')) {
            document.getElementById('logoSize').value = settings.logoSize;
            updateSliderValue('logoSize', settings.logoSize + '%');
        }
        
        if (settings.logoStartTime && document.getElementById('logoStartTime')) {
            document.getElementById('logoStartTime').value = settings.logoStartTime;
        }
        
        if (settings.logoEndTime !== undefined && document.getElementById('logoEndTime')) {
            document.getElementById('logoEndTime').value = settings.logoEndTime;
        }
        
        // Apply CTA settings
        if (settings.ctaPosition && document.getElementById('ctaPosition')) {
            document.getElementById('ctaPosition').value = settings.ctaPosition;
        }
        
        if (settings.ctaSize && document.getElementById('ctaSize')) {
            document.getElementById('ctaSize').value = settings.ctaSize;
            updateSliderValue('ctaSize', settings.ctaSize + '%');
        }
        
        if (settings.ctaStartTime && document.getElementById('ctaStartTime')) {
            document.getElementById('ctaStartTime').value = settings.ctaStartTime;
        }
        
        if (settings.ctaEndTime !== undefined && document.getElementById('ctaEndTime')) {
            document.getElementById('ctaEndTime').value = settings.ctaEndTime;
        }
        
        // Apply chromakey settings
        if (settings.chromakeyEnabled !== undefined && document.getElementById('chromakeyEnabled')) {
            document.getElementById('chromakeyEnabled').checked = settings.chromakeyEnabled;
        }
        
        // Apply chromakey color selection
        if (settings.chromakeyColor) {
            // Remove active from all color options
            document.querySelectorAll('.color-option').forEach(option => {
                option.classList.remove('active');
            });
            
            // Add active to selected color
            const colorOption = document.querySelector(`[data-color="${settings.chromakeyColor}"]`);
            if (colorOption) {
                colorOption.classList.add('active');
            }
        }
        
        // Apply quality settings
        if (settings.qualityPreset && document.getElementById('qualityPreset')) {
            document.getElementById('qualityPreset').value = settings.qualityPreset;
        }
        
        // Restore uploaded files with previews
        if (settings.foregroundFileId) {
            foregroundFileId = settings.foregroundFileId;
            foregroundFileName = settings.foregroundFileName;
            console.log('Restored foregroundFileId:', foregroundFileId);
            await restoreFileWithPreview(settings.foregroundFileId, 'foreground', settings.foregroundFileName);
        }
        
        if (settings.backgroundFileId) {
            backgroundFileId = settings.backgroundFileId;
            backgroundFileName = settings.backgroundFileName;
            console.log('Restored backgroundFileId:', backgroundFileId);
            await restoreFileWithPreview(settings.backgroundFileId, 'background', settings.backgroundFileName);
        }
        
        if (settings.logoFileId) {
            logoFileId = settings.logoFileId;
            logoFileName = settings.logoFileName;
            console.log('Restored logoFileId:', logoFileId);
            await restoreFileWithPreview(settings.logoFileId, 'logo', settings.logoFileName);
        }
        
        // Restore feature toggles
        const toggleIds = ['logoOverlay', 'callToAction', 'videoTranscription', 'audioTranslation', 'coverGeneration', 'metadataGeneration', 'youtubeUpload'];
        toggleIds.forEach(toggleId => {
            if (settings[toggleId] !== undefined && document.getElementById(toggleId)) {
                document.getElementById(toggleId).checked = settings[toggleId];
                console.log(`Restored toggle ${toggleId}:`, settings[toggleId]);
            }
        });

        // Restore Thumbnail Generator settings (Tab Copertina)
        if (settings.coverStyle && document.getElementById('coverStyle')) {
            document.getElementById('coverStyle').value = settings.coverStyle;
        }

        if (settings.coverDescription && document.getElementById('coverDescription')) {
            document.getElementById('coverDescription').value = settings.coverDescription;
        }

        if (settings.addTextOverlay !== undefined && document.getElementById('addTextOverlay')) {
            document.getElementById('addTextOverlay').checked = settings.addTextOverlay;
            toggleTextOptions(); // Show/hide text options based on checkbox
        }

        if (settings.coverMainText && document.getElementById('coverMainText')) {
            document.getElementById('coverMainText').value = settings.coverMainText;
        }

        if (settings.textPosition && document.getElementById('textPosition')) {
            document.getElementById('textPosition').value = settings.textPosition;
        }

        if (settings.textColor && document.getElementById('textColor')) {
            document.getElementById('textColor').value = settings.textColor;
        }

        if (settings.textBgColor && document.getElementById('textBgColor')) {
            document.getElementById('textBgColor').value = settings.textBgColor;
        }

        if (settings.textBgOpacity && document.getElementById('textBgOpacity')) {
            document.getElementById('textBgOpacity').value = settings.textBgOpacity;
            document.getElementById('textBgOpacityValue').textContent = settings.textBgOpacity + '%';
        }

        if (settings.frameTimestamp && document.getElementById('frameTimestamp')) {
            document.getElementById('frameTimestamp').value = settings.frameTimestamp;
        }

        if (settings.currentImageSource) {
            selectImageSource(settings.currentImageSource);
        }

        // Clean up localStorage if any files were cleared
        console.log('🧹 Cleaning up localStorage after file validation...');
        saveSettings();
        
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

async function restoreFileWithPreview(fileId, type, originalFileName) {
    try {
        // Define appropriate extensions based on file type
        let allowedExtensions = [];
        if (type === 'foreground' || type === 'background') {
            // Video files only for foreground and background
            allowedExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm'];
        } else if (type === 'logo') {
            // Image files only for logo
            allowedExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'];
        } else {
            // Fallback to all extensions
            allowedExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'];
        }
        
        let filePath = null;
        let foundExtension = null;

        console.log(`🔍 Trying to restore ${type} file with ID: ${fileId}`);
        console.log(`📂 Original filename: ${originalFileName}`);
        console.log(`📋 Allowed extensions: ${allowedExtensions.join(', ')}`);

        // PRIMA: Se abbiamo il filename completo, prova direttamente con quello
        if (originalFileName) {
            const directPath = `/uploads/${originalFileName}`;
            console.log(`🎯 Trying direct path with full filename: ${directPath}`);
            const response = await fetch(directPath, { method: 'HEAD' });
            if (response.ok) {
                filePath = directPath;
                console.log(`✅ Found file with full filename: ${directPath}`);
            }
        }

        // FALLBACK: Se non trovato, prova con fileId + estensioni
        if (!filePath) {
            console.log(`⚠️ Direct path failed, trying with fileId + extensions...`);
            for (const ext of allowedExtensions) {
                const testPath = `/uploads/${fileId}${ext}`;
                const response = await fetch(testPath, { method: 'HEAD' });
                if (response.ok) {
                    filePath = testPath;
                    foundExtension = ext;
                    console.log(`✅ Found file: ${testPath}`);
                    break;
                }
            }
        }
        
        if (filePath) {
            // File exists, create mock result with actual file path and original name
            const mockResult = {
                file_id: fileId,
                filename: originalFileName || `File salvato: ${fileId}`,
                path: filePath
            };
            
            // Update file info displays
            updateAllFileDisplays(mockResult, type, null);
            
            // Now set up the actual preview by creating elements with the server path
            const previewMap = {
                'foreground': 'ctaPreview',
                'background': 'mainVideoPreview', 
                'logo': 'logoPreview'
            };
            
            const previewOverlayMap = {
                'foreground': 'ctaPreviewOverlay',
                'background': 'mainVideoPreviewOverlay',
                'logo': 'logoPreviewOverlay'
            };
            
            const advancedPreviewOverlayMap = {
                'foreground': 'ctaAdvancedPreviewOverlay',
                'logo': 'logoAdvancedPreviewOverlay'
            };
            
            // Set preview in main tab
            const previewElement = document.getElementById(previewMap[type]);
            if (previewElement) {
                if (type === 'logo') {
                    const img = previewElement.querySelector('.preview-image');
                    if (img) {
                        img.src = filePath;
                    }
                } else {
                    const video = previewElement.querySelector('.preview-video');
                    if (video) {
                        video.src = filePath;
                    }
                }
            }
            
            // Set preview in overlay
            const previewOverlay = document.getElementById(previewOverlayMap[type]);
            if (previewOverlay) {
                if (type === 'logo') {
                    const overlayImg = previewOverlay.querySelector('.preview-image-overlay');
                    if (overlayImg) {
                        overlayImg.src = filePath;
                    }
                } else {
                    const overlayVideo = previewOverlay.querySelector('.preview-video-overlay');
                    if (overlayVideo) {
                        overlayVideo.src = filePath;
                    }
                }
                // Add active class to show the preview overlay
                previewOverlay.classList.add('active');
            }
            
            // Set preview in advanced overlay if exists
            const advancedPreviewOverlay = document.getElementById(advancedPreviewOverlayMap[type]);
            if (advancedPreviewOverlay) {
                if (type === 'logo') {
                    const advancedOverlayImg = advancedPreviewOverlay.querySelector('.preview-image-overlay');
                    if (advancedOverlayImg) {
                        advancedOverlayImg.src = filePath;
                    }
                } else {
                    const advancedOverlayVideo = advancedPreviewOverlay.querySelector('.preview-video-overlay');
                    if (advancedOverlayVideo) {
                        advancedOverlayVideo.src = filePath;
                    }
                }
                // Add active class to show the advanced preview overlay
                advancedPreviewOverlay.classList.add('active');
            }

            // Update interactive preview canvas if needed
            if (type === 'background') {
                // Main video loaded - initialize canvas and show logo/CTA if already loaded
                console.log('🎬 Main video restored, initializing interactive preview');

                // Wait for video to load before updating canvas
                const mainVideo = previewOverlay?.querySelector('.preview-video-overlay');
                if (mainVideo) {
                    mainVideo.addEventListener('loadeddata', () => {
                        console.log('🎬 Main video data loaded from restore');
                        updateCanvasWithMainVideo();

                        // Show logo/CTA if already loaded
                        if (logoFileId) {
                            console.log('📌 Restoring logo in interactive preview');
                            const logoElement = document.getElementById('draggableLogo');
                            const logoImg = document.getElementById('logoPreviewImage');
                            if (logoElement && logoImg) {
                                fetch(`/uploads/${logoFileId}.png`)
                                    .then(r => r.ok ? r.blob() : fetch(`/uploads/${logoFileName}`).then(r2 => r2.blob()))
                                    .then(blob => {
                                        logoImg.src = URL.createObjectURL(blob);
                                        logoElement.style.display = 'block';
                                        positionElementFromInputs('logo');
                                    })
                                    .catch(err => console.error('Error loading logo for preview:', err));
                            }
                        }

                        if (foregroundFileId) {
                            console.log('📌 Restoring CTA in interactive preview');
                            const ctaElement = document.getElementById('draggableCTA');
                            const ctaVideo = document.getElementById('ctaPreviewVideo');
                            if (ctaElement && ctaVideo) {
                                fetch(`/uploads/${foregroundFileId}.mp4`)
                                    .then(r => r.ok ? r.blob() : fetch(`/uploads/${foregroundFileName}`).then(r2 => r2.blob()))
                                    .then(blob => {
                                        ctaVideo.src = URL.createObjectURL(blob);
                                        ctaElement.style.display = 'block';
                                        ctaVideo.load();
                                        ctaVideo.play().catch(() => {});
                                        positionElementFromInputs('cta');
                                    })
                                    .catch(err => console.error('Error loading CTA for preview:', err));
                            }
                        }
                    }, { once: true });
                }
            } else if (type === 'logo' && backgroundFileId) {
                // Logo loaded after main video - update preview
                console.log('📌 Logo restored, updating interactive preview');
                const logoElement = document.getElementById('draggableLogo');
                const logoImg = document.getElementById('logoPreviewImage');
                if (logoElement && logoImg) {
                    logoImg.onload = () => {
                        logoElement.style.display = 'block';
                        positionElementFromInputs('logo');
                        if (!previewState.canvas) {
                            initializePreviewCanvas();
                        }
                        drawVideoFrameOnCanvas();
                    };
                    if (!logoImg.src || logoImg.src === window.location.href) {
                        logoImg.src = filePath;
                    }
                }
            } else if (type === 'foreground' && backgroundFileId) {
                // CTA loaded after main video - update preview
                console.log('📌 CTA restored, updating interactive preview');
                const ctaElement = document.getElementById('draggableCTA');
                const ctaVideo = document.getElementById('ctaPreviewVideo');
                if (ctaElement && ctaVideo) {
                    ctaVideo.addEventListener('loadedmetadata', () => {
                        ctaElement.style.display = 'block';
                        ctaVideo.play().catch(() => {});
                        positionElementFromInputs('cta');
                        if (!previewState.canvas) {
                            initializePreviewCanvas();
                        }
                        drawVideoFrameOnCanvas();
                    }, { once: true });
                    if (!ctaVideo.src || ctaVideo.src === window.location.href) {
                        ctaVideo.src = filePath;
                    }
                }
            }

            console.log(`✅ Restored file preview for ${type}: ${fileId}`);
        } else {
            console.warn(`⚠️  File not found on server for ${type}: ${fileId}`);
            console.log(`🧹 Clearing ${type} file variables`);
            
            // Clear the global variables for missing files
            if (type === 'foreground') {
                foregroundFileId = null;
                foregroundFileName = null;
            } else if (type === 'background') {
                backgroundFileId = null;
                backgroundFileName = null;
            } else if (type === 'logo') {
                logoFileId = null;
                logoFileName = null;
            }
            
            // Don't show anything for missing files - just clear them
            console.log(`🗑️  ${type} file cleared from memory due to missing file`);
        }
    } catch (error) {
        console.error(`❌ Error restoring file preview for ${type}:`, error);
        // Fallback to showing info without preview
        const mockResult = {
            file_id: fileId,
            filename: `Errore caricamento: ${fileId}`,
            path: `/uploads/${fileId}`
        };
        updateAllFileDisplays(mockResult, type, null);
    }
}

// Update file status display
function updateFileStatus(type, status, fileId) {
    const fileNameMap = {
        'foreground': 'ctaName',
        'background': 'mainVideoName',
        'logo': 'logoName'
    };
    
    const statusMap = {
        'foreground': 'ctaStatus',
        'background': 'mainVideoStatus',
        'logo': 'logoStatus'
    };
    
    const nameElement = document.getElementById(fileNameMap[type]);
    const statusElement = document.getElementById(statusMap[type]);
    
    if (nameElement && statusElement) {
        nameElement.textContent = fileId + ' (file salvato)';
        statusElement.textContent = status;
        statusElement.className = 'file-status success';
    }
}

// Add event listeners to auto-save when settings change
function initializeSettingsAutoSave() {
    // List of all input elements that should trigger auto-save
    const settingsInputs = [
        'xPos', 'yPos', 'scale', 'audioMode', 
        'logoPosition', 'logoSize', 'logoStartTime', 'logoEndTime',
        'ctaPosition', 'ctaSize', 'ctaStartTime', 'ctaEndTime',
        'chromakeyEnabled', 'qualityPreset',
        // Feature toggles
        'logoOverlay', 'callToAction', 'videoTranscription', 'audioTranslation',
        'coverGeneration', 'metadataGeneration', 'youtubeUpload'
    ];
    
    // Add event listeners to all settings inputs
    settingsInputs.forEach(inputId => {
        const element = document.getElementById(inputId);
        if (element) {
            if (element.type === 'checkbox') {
                element.addEventListener('change', saveSettings);
            } else if (element.type === 'range') {
                element.addEventListener('input', saveSettings);
            } else {
                element.addEventListener('change', saveSettings);
                element.addEventListener('input', saveSettings);
            }
        }
    });
    
    // Add event listeners to color options
    document.querySelectorAll('.color-option').forEach(option => {
        option.addEventListener('click', () => {
            setTimeout(saveSettings, 100); // Small delay to ensure the active class is set
        });
    });
}

// Reset all settings to defaults
async function resetSettings() {
    const confirmed = await showConfirm(
        'Sei sicuro di voler resettare TUTTO ai valori predefiniti?\n\nQuesto:\n• Cancellerà TUTTI i file caricati (uploads e outputs)\n• Ripristinerà tutte le impostazioni di default\n• Cancellerà posizioni, dimensioni e timing\n• Ripristinerà modalità audio, chromakey e qualità\n\nATTENZIONE: Tutti i file sul server verranno eliminati!\n\nL\'azione NON può essere annullata.',
        {
            title: 'Ripristina Tutto',
            type: 'danger',
            confirmText: 'Sì, Ripristina Tutto',
            cancelText: 'Annulla',
            confirmIcon: 'fa-trash-alt',
            cancelIcon: 'fa-times'
        }
    );

    if (confirmed) {
        try {
            // Show loading message
            showAlert('Cancellazione file e ripristino impostazioni in corso...', 'info');

            // Delete all files from server
            const response = await fetch('/api/files/delete-all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Errore nella cancellazione dei file');
            }

            const result = await response.json();
            console.log('Files deleted:', result);

            // Remove settings from localStorage
            localStorage.removeItem('aiVideoMakerSettings');
            localStorage.removeItem('metadataSettings');

            // Reset metadata settings se la funzione esiste
            if (typeof window.resetMetadataSettings === 'function') {
                window.resetMetadataSettings();
            }

            // Clear global file IDs
            foregroundFileId = null;
            backgroundFileId = null;
            logoFileId = null;
            foregroundFileName = null;
            backgroundFileName = null;
            logoFileName = null;

            // Clear thumbnail generator file IDs
            coverVideoFileId = null;
            coverImageFileId = null;
            coverFrameFileId = null;
            currentImageSource = 'ai';
            thumbnailJobId = null;

            // Show success message
            showAlert(`${result.count} file cancellati. Impostazioni ripristinate!`, 'success');

            // Reload page to apply default values
            setTimeout(() => {
                location.reload();
            }, 1500);

        } catch (error) {
            console.error('Error resetting settings:', error);
            showAlert('Errore nel ripristino: ' + error.message, 'error');
        }
    }
}

// Export settings for backup
function exportSettings() {
    try {
        const settings = localStorage.getItem('aiVideoMakerSettings');
        if (settings) {
            // Add metadata to the export
            const exportData = {
                version: "1.0",
                exported: new Date().toISOString(),
                settings: JSON.parse(settings)
            };
            
            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Generate filename with timestamp
            const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
            a.download = `ai-video-maker-settings-${timestamp}.json`;
            
            a.click();
            URL.revokeObjectURL(url);
            
            showAlert('Impostazioni esportate con successo!', 'success');
        } else {
            showAlert('Nessuna impostazione salvata da esportare.', 'warning');
        }
    } catch (error) {
        console.error('Export error:', error);
        showAlert('Errore durante l\'esportazione delle impostazioni', 'error');
    }
}

// Import settings from backup
function importSettings(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    if (!file.name.toLowerCase().endsWith('.json')) {
        showAlert('Per favore seleziona un file JSON valido.', 'error');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const importedData = JSON.parse(e.target.result);
            let settings;
            
            // Handle both old format (direct settings) and new format (with metadata)
            if (importedData.settings && importedData.version) {
                // New format with metadata
                settings = importedData.settings;
                showAlert(`Impostazioni importate (esportate il: ${new Date(importedData.exported).toLocaleDateString('it-IT')})`, 'success');
            } else {
                // Old format or direct settings
                settings = importedData;
                showAlert('Impostazioni importate con successo!', 'success');
            }
            
            // Validate that it contains expected settings
            if (typeof settings === 'object' && settings !== null) {
                localStorage.setItem('aiVideoMakerSettings', JSON.stringify(settings));
                
                // Reload to apply imported settings
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                throw new Error('Formato impostazioni non valido');
            }
            
        } catch (error) {
            console.error('Import error:', error);
            showAlert('Errore nel caricamento delle impostazioni: file non valido o corrotto.', 'error');
        }
    };
    
    reader.onerror = function() {
        showAlert('Errore nella lettura del file.', 'error');
    };
    
    reader.readAsText(file);
    
    // Clear the input so the same file can be selected again
    event.target.value = '';
}

function stopProcessing() {
    console.log('🛑 stopProcessing() called');
    console.log('🆔 Current job ID:', currentJobId);
    
    if (processingInterval) {
        clearInterval(processingInterval);
        processingInterval = null;
        console.log('✅ Progress monitoring interval cleared');
    }
    
    if (currentJobId) {
        console.log('📡 Sending DELETE request to backend...');
        fetch(`/api/jobs/${currentJobId}`, { method: 'DELETE' })
            .then(response => {
                console.log('📡 DELETE response status:', response.status);
                console.log('📡 DELETE response headers:', response.headers);
                if (response.ok) {
                    return response.json();
                } else {
                    console.error('❌ Backend returned error:', response.status, response.statusText);
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
            })
            .then(data => {
                console.log('✅ DELETE request successful:', data);
                console.log('🎯 Backend response message:', data.message);
            })
            .catch(error => {
                console.error('❌ Errore nell\'eliminazione del job:', error);
                console.error('❌ Error details:', error.message);
            });
        currentJobId = null;
    } else {
        console.log('⚠️ No current job ID to cancel');
    }
    
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) progressContainer.classList.remove('active');
    
    resetUI();
    showAlert('Elaborazione interrotta', 'info');
}

function resetUI() {
    const processBtn = document.getElementById('processBtn');
    const stopBtn = document.getElementById('stopBtn');
    
    if (processBtn) processBtn.style.display = 'inline-flex';
    if (stopBtn) stopBtn.style.display = 'none';
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
    console.log('🆕 Starting new project - clearing all data');
    
    // Reset file IDs and names
    foregroundFileId = null;
    backgroundFileId = null;
    logoFileId = null;
    foregroundFileName = null;
    backgroundFileName = null;
    logoFileName = null;
    currentJobId = null;
    
    // Reset all file displays across tabs
    removeFileFromAllTabs('foreground');
    removeFileFromAllTabs('background'); 
    removeFileFromAllTabs('logo');
    
    // Reset containers
    const resultContainer = document.getElementById('resultContainer');
    const progressContainer = document.getElementById('progressContainer');
    
    if (resultContainer) resultContainer.classList.remove('active');
    if (progressContainer) progressContainer.classList.remove('active');
    
    // Reset advanced file inputs
    const advancedFileInputs = ['ctaAdvancedFile', 'logoAdvancedFile'];
    advancedFileInputs.forEach(id => {
        const element = document.getElementById(id);
        if (element) element.value = '';
    });
    
    // Reset selects
    const audioMode = document.getElementById('audioMode');
    const qualityPreset = document.getElementById('qualityPreset');
    
    if (audioMode) audioMode.value = 'synced';
    if (qualityPreset) qualityPreset.value = 'balanced';
    
    // Reset advanced settings
    const logoPosition = document.getElementById('logoPosition');
    const ctaPosition = document.getElementById('ctaPosition');
    const logoSize = document.getElementById('logoSize');
    const ctaSize = document.getElementById('ctaSize');
    const logoStartTime = document.getElementById('logoStartTime');
    const ctaStartTime = document.getElementById('ctaStartTime');
    const logoEndTime = document.getElementById('logoEndTime');
    const ctaEndTime = document.getElementById('ctaEndTime');
    
    if (logoPosition) logoPosition.value = 'top-right';
    if (ctaPosition) ctaPosition.value = 'center';
    if (logoSize) {
        logoSize.value = 10;
        updateSliderValue('logoSize', '10%');
    }
    if (ctaSize) {
        ctaSize.value = 20;
        updateSliderValue('ctaSize', '20%');
    }
    if (logoStartTime) logoStartTime.value = 0;
    if (ctaStartTime) ctaStartTime.value = 5;
    if (logoEndTime) logoEndTime.value = '';
    if (ctaEndTime) ctaEndTime.value = '';
    
    // Reset toggles
    const callToAction = document.getElementById('callToAction');
    if (callToAction) callToAction.checked = false;
    
    const otherToggles = ['logoOverlay', 'videoTranscription', 'audioTranslation', 'coverGeneration', 'metadataGeneration', 'youtubeUpload'];
    otherToggles.forEach(id => {
        const element = document.getElementById(id);
        if (element) element.checked = false;
    });
    
    resetUI();
    
    // Save the clean state to localStorage
    console.log('💾 Saving clean project state to localStorage');
    saveSettings();
    
    showAlert('Nuovo progetto creato', 'success');
}

// Utility Functions
function showHelp() {
    const helpText = `
🎬 AIVideoMaker - Guida Rapida

1. Carica il tuo video Call to Action (con green screen)
2. Carica il video principale di sfondo  
3. Configura timing e posizionamento nelle impostazioni
4. Clicca 'Elabora Video' per creare il risultato finale
5. Scarica il video completato

Funzionalità Future:
• Generazione automatica copertine
• Traduzione e doppiaggio audio
• Caricamento diretto su YouTube
• Generazione metadati AI
    `;
    
    showAlert(helpText, 'info');
}

// Alert System (reuse from previous version)
function showAlert(message, type = 'info') {
    const alertContainer = getOrCreateAlertContainer();
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        <span>${message}</span>
        <button class="alert-close">&times;</button>
    `;
    
    const closeBtn = alert.querySelector('.alert-close');
    closeBtn.addEventListener('click', () => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    });
    
    alertContainer.appendChild(alert);
    
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

// Keyboard Shortcuts
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const sidebar = document.getElementById('sidebar');
        const hamburger = document.querySelector('.hamburger');
        if (sidebar) sidebar.classList.remove('active');
        if (hamburger) hamburger.classList.remove('active');
    }
    
    if (event.ctrlKey && event.key === 'n') {
        event.preventDefault();
        newProject();
    }
});

// Logo & CTA Advanced Functions
function updateSliderValue(sliderId, value) {
    const valueElement = document.getElementById(sliderId + 'Value');
    if (valueElement) {
        valueElement.textContent = value;
    }
}

function initializeAdvancedControls() {
    // Initialize color picker
    const colorOptions = document.querySelectorAll('.color-option');
    colorOptions.forEach(option => {
        option.addEventListener('click', function() {
            // Remove active class from all options
            colorOptions.forEach(opt => opt.classList.remove('active'));
            // Add active class to clicked option
            this.classList.add('active');
            
            const color = this.getAttribute('data-color');
        });
    });
    
    // Initialize chromakey toggle
    const chromakeyEnabled = document.getElementById('chromakeyEnabled');
    const chromakeyControls = document.getElementById('chromakeyControls');
    
    if (chromakeyEnabled && chromakeyControls) {
        chromakeyEnabled.addEventListener('change', function() {
            if (this.checked) {
                chromakeyControls.classList.remove('disabled');
            } else {
                chromakeyControls.classList.add('disabled');
            }
        });
    }
    
    // Initialize advanced file uploads
    const logoAdvancedFile = document.getElementById('logoAdvancedFile');
    const ctaAdvancedFile = document.getElementById('ctaAdvancedFile');
    const logoTabMainVideoFile = document.getElementById('logoTabMainVideoFile');

    if (logoAdvancedFile) {
        logoAdvancedFile.addEventListener('change', (e) => handleAdvancedFileSelect(e, 'logo-advanced'));
    }

    if (ctaAdvancedFile) {
        ctaAdvancedFile.addEventListener('change', (e) => handleAdvancedFileSelect(e, 'cta-advanced'));
    }

    if (logoTabMainVideoFile) {
        logoTabMainVideoFile.addEventListener('change', (e) => handleAdvancedFileSelect(e, 'background-logo-tab'));
    }
    
    // Initialize slider values
    updateSliderValue('logoSize', '10%');
    updateSliderValue('ctaSize', '20%');

    // Add listeners for position and size changes to update preview
    const logoPosition = document.getElementById('logoPosition');
    const ctaPosition = document.getElementById('ctaPosition');
    const logoSize = document.getElementById('logoSize');
    const ctaSize = document.getElementById('ctaSize');

    if (logoPosition) {
        logoPosition.addEventListener('change', () => {
            if (previewState.logoElement && previewState.logoElement.style.display !== 'none') {
                positionElementFromInputs('logo');
            }
        });
    }

    if (ctaPosition) {
        ctaPosition.addEventListener('change', () => {
            if (previewState.ctaElement && previewState.ctaElement.style.display !== 'none') {
                positionElementFromInputs('cta');
            }
        });
    }

    if (logoSize) {
        logoSize.addEventListener('input', () => {
            if (previewState.logoElement && previewState.logoElement.style.display !== 'none') {
                positionElementFromInputs('logo');
            }
        });
    }

    if (ctaSize) {
        ctaSize.addEventListener('input', () => {
            if (previewState.ctaElement && previewState.ctaElement.style.display !== 'none') {
                positionElementFromInputs('cta');
            }
        });
    }
}

function handleAdvancedFileSelect(event, type) {
    const file = event.target.files[0];
    
    // Reset the file input first
    event.target.value = '';
    
    if (!file) {
        console.log('No file selected in advanced upload');
        return;
    }
    
    console.log('Advanced file selected:', file.name, 'type:', type);
    
    // Map advanced types to normal types
    let normalType;
    let uploadArea;

    if (type === 'logo-advanced') {
        normalType = 'logo';
        uploadArea = document.getElementById('logoAdvancedUpload');
    } else if (type === 'cta-advanced') {
        normalType = 'foreground';
        uploadArea = document.getElementById('ctaAdvancedUpload');
    } else if (type === 'background-logo-tab') {
        normalType = 'background';
        uploadArea = document.getElementById('logoTabMainVideoUpload');
    } else {
        console.error('Unknown advanced file type:', type);
        return;
    }

    // Use the normal file handling logic
    handleFileUpload(file, normalType);
        
    if (uploadArea) {
        const uploadContent = uploadArea.querySelector('.upload-content');
        const previewOverlay = uploadArea.querySelector('.upload-preview');

        // For video uploads (background and CTA), show video preview
        if (type === 'background-logo-tab' || type === 'cta-advanced') {
            if (uploadContent) uploadContent.style.display = 'none';
            if (previewOverlay) {
                const video = previewOverlay.querySelector('video');
                if (video) {
                    video.src = URL.createObjectURL(file);
                    video.load();
                }
                previewOverlay.style.display = 'flex';
            }
        } else if (type === 'logo-advanced') {
            // For logo (image), show image preview
            if (uploadContent) uploadContent.style.display = 'none';
            if (previewOverlay) {
                const img = previewOverlay.querySelector('img');
                if (img) {
                    img.src = URL.createObjectURL(file);
                }
                previewOverlay.style.display = 'flex';
            }

            // Update interactive preview
            updateLogoPreview(file);
        }

        uploadArea.style.borderColor = '#10b981';
        uploadArea.style.background = 'rgba(16, 185, 129, 0.1)';
    }

    // Update CTA preview if it's a CTA video
    if (type === 'cta-advanced') {
        updateCTAPreview(file);
    }

    // Update canvas when main video is loaded
    if (type === 'background-logo-tab') {
        console.log('📹 Main video uploaded in Logo tab, updating canvas');
        // Wait for video element to be ready
        setTimeout(() => {
            updateCanvasWithMainVideo();
        }, 800);
    }
}

function getPositionCoordinates(position, videoWidth = 1920, videoHeight = 1080, isLogo = false) {
    // Scale margins and element sizes based on video dimensions
    const scaleFactor = videoWidth / 1920; // Scale based on width
    const marginHorizontal = isLogo ? (10 * scaleFactor) : (50 * scaleFactor);  // Closer to edges horizontally
    const marginVertical = isLogo ? (25 * scaleFactor) : (50 * scaleFactor);   // More space from top/bottom edges
    const elementWidth = isLogo ? (100 * scaleFactor) : (320 * scaleFactor);  
    const elementHeight = isLogo ? (100 * scaleFactor) : (180 * scaleFactor);
    
    const positions = {
        'top-left': { 
            x: marginHorizontal, 
            y: marginVertical 
        },
        'top-right': { 
            x: videoWidth - elementWidth - marginHorizontal, 
            y: marginVertical 
        },
        'top-center': { 
            x: (videoWidth - elementWidth) / 2, 
            y: marginVertical 
        },
        'center': { 
            x: (videoWidth - elementWidth) / 2, 
            y: (videoHeight - elementHeight) / 2 
        },
        'bottom-left': { 
            x: marginHorizontal, 
            y: videoHeight - elementHeight - marginVertical 
        },
        'bottom-right': { 
            x: videoWidth - elementWidth - marginHorizontal, 
            y: videoHeight - elementHeight - marginVertical 
        },
        'bottom-center': { 
            x: (videoWidth - elementWidth) / 2, 
            y: videoHeight - elementHeight - marginVertical 
        }
    };
    
    return positions[position] || positions['center'];
}

function getChromaKeySettings() {
    const chromakeyEnabled = document.getElementById('chromakeyEnabled');
    if (!chromakeyEnabled || !chromakeyEnabled.checked) {
        return null;
    }
    
    const activeColorOption = document.querySelector('.color-option.active');
    const selectedColor = activeColorOption ? activeColorOption.getAttribute('data-color') : 'green';
    
    // Color presets with HSV values
    const colorPresets = {
        'green': { lower: [40, 40, 40], upper: [80, 255, 255] },
        'blue': { lower: [100, 50, 50], upper: [130, 255, 255] },
        'green2': { lower: [35, 40, 40], upper: [85, 255, 255] },
        'green3': { lower: [45, 50, 50], upper: [75, 255, 255] },
        'blue2': { lower: [90, 40, 40], upper: [120, 255, 255] },
        'custom': { lower: [40, 40, 40], upper: [80, 255, 255] }
    };
    
    return colorPresets[selectedColor] || colorPresets['green'];
}

function resetAdvancedControls() {
    // Reset upload areas
    const logoUpload = document.getElementById('logoAdvancedUpload');
    const ctaUpload = document.getElementById('ctaAdvancedUpload');
    
    if (logoUpload) {
        const icon = logoUpload.querySelector('.upload-icon');
        const button = logoUpload.querySelector('.upload-btn');
        
        icon.className = 'fas fa-image upload-icon';
        icon.style.color = '#3b82f6';
        button.innerHTML = '<i class="fas fa-upload"></i> Carica';
        
        logoUpload.style.borderColor = 'rgba(59, 130, 246, 0.4)';
        logoUpload.style.background = 'rgba(59, 130, 246, 0.05)';
    }
    
    if (ctaUpload) {
        const icon = ctaUpload.querySelector('.upload-icon');
        const button = ctaUpload.querySelector('.upload-btn');
        
        icon.className = 'fas fa-play upload-icon';
        icon.style.color = '#3b82f6';
        button.innerHTML = '<i class="fas fa-upload"></i> Carica';
        
        ctaUpload.style.borderColor = 'rgba(59, 130, 246, 0.4)';
        ctaUpload.style.background = 'rgba(59, 130, 246, 0.05)';
    }
    
    // Reset form values
    const logoPosition = document.getElementById('logoPosition');
    const ctaPosition = document.getElementById('ctaPosition');
    const logoSize = document.getElementById('logoSize');
    const ctaSize = document.getElementById('ctaSize');
    const logoStartTime = document.getElementById('logoStartTime');
    const ctaStartTime = document.getElementById('ctaStartTime');
    const logoEndTime = document.getElementById('logoEndTime');
    const ctaEndTime = document.getElementById('ctaEndTime');
    const chromakeyEnabled = document.getElementById('chromakeyEnabled');
    
    if (logoPosition) logoPosition.value = 'top-right';
    if (ctaPosition) ctaPosition.value = 'center';
    if (logoSize) {
        logoSize.value = 10;
        updateSliderValue('logoSize', '10%');
    }
    if (ctaSize) {
        ctaSize.value = 20;
        updateSliderValue('ctaSize', '20%');
    }
    if (logoStartTime) logoStartTime.value = 0;
    if (ctaStartTime) ctaStartTime.value = 5;
    if (logoEndTime) logoEndTime.value = '';
    if (ctaEndTime) ctaEndTime.value = '';
    if (chromakeyEnabled) chromakeyEnabled.checked = true;
    
    // Reset color selection
    const colorOptions = document.querySelectorAll('.color-option');
    colorOptions.forEach(option => {
        if (option.getAttribute('data-color') === 'green') {
            option.classList.add('active');
        } else {
            option.classList.remove('active');
        }
    });
    
    // Reset file inputs
    const logoFile = document.getElementById('logoAdvancedFile');
    const ctaFile = document.getElementById('ctaAdvancedFile');
    const logoTabVideoFile = document.getElementById('logoTabMainVideoFile');

    if (logoFile) logoFile.value = '';
    if (ctaFile) ctaFile.value = '';
    if (logoTabVideoFile) logoTabVideoFile.value = '';

    // Reset logo tab video upload area
    const logoTabUploadArea = document.getElementById('logoTabMainVideoUpload');
    if (logoTabUploadArea) {
        const uploadContent = logoTabUploadArea.querySelector('.upload-content');
        const previewOverlay = logoTabUploadArea.querySelector('.upload-preview');
        if (uploadContent) uploadContent.style.display = 'flex';
        if (previewOverlay) previewOverlay.style.display = 'none';
        logoTabUploadArea.style.borderColor = '';
        logoTabUploadArea.style.background = '';
    }
}

// Initialization is already handled at the top of the file

// Update newProject function to include advanced controls reset
const originalNewProject = newProject;
newProject = function() {
    originalNewProject();
    resetAdvancedControls();
};

// Preview Functions
let previewCanvas = null;
let previewCtx = null;
let previewMainVideo = null;
let previewLogo = null;
let previewCTA = null;
let isPreviewPlaying = false;
let previewAnimationId = null;

function initializePreview() {
    previewCanvas = document.getElementById('previewCanvas');
    if (previewCanvas) {
        previewCtx = previewCanvas.getContext('2d');
    }
}

function togglePreview() {
    if (!previewCanvas || !previewCtx) {
        initializePreview();
    }
    
    const playBtn = document.getElementById('previewPlayBtn');
    const overlay = document.getElementById('previewOverlay');
    
    if (isPreviewPlaying) {
        pausePreview();
        playBtn.innerHTML = '<i class="fas fa-play"></i> Play';
    } else {
        startPreview();
        playBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
        overlay.classList.add('hidden');
    }
    
    isPreviewPlaying = !isPreviewPlaying;
}

function startPreview() {
    if (!backgroundFileId) {
        showAlert('Carica prima il video principale per vedere l\'anteprima', 'warning');
        return;
    }
    
    setupPreviewVideos();
    renderPreviewFrame();
}

function pausePreview() {
    if (previewAnimationId) {
        cancelAnimationFrame(previewAnimationId);
        previewAnimationId = null;
    }
    
    if (previewMainVideo) {
        previewMainVideo.pause();
    }
}

function resetPreview() {
    pausePreview();
    
    const playBtn = document.getElementById('previewPlayBtn');
    const overlay = document.getElementById('previewOverlay');
    const timeline = document.getElementById('previewTimeline');
    
    playBtn.innerHTML = '<i class="fas fa-play"></i> Play';
    overlay.classList.remove('hidden');
    timeline.value = 0;
    
    if (previewMainVideo) {
        previewMainVideo.currentTime = 0;
    }
    
    updateTimeDisplay(0, previewMainVideo ? previewMainVideo.duration : 0);
    isPreviewPlaying = false;
}

function setupPreviewVideos() {
    // Setup main video
    const mainVideoPreview = document.querySelector('#mainVideoPreview .preview-video');
    if (mainVideoPreview && mainVideoPreview.src) {
        previewMainVideo = document.createElement('video');
        previewMainVideo.src = mainVideoPreview.src;
        previewMainVideo.crossOrigin = 'anonymous';
        previewMainVideo.muted = true;
    }
    
    // Setup CTA video
    const ctaVideoPreview = document.querySelector('#ctaPreview .preview-video');
    if (ctaVideoPreview && ctaVideoPreview.src) {
        previewCTA = document.createElement('video');
        previewCTA.src = ctaVideoPreview.src;
        previewCTA.crossOrigin = 'anonymous';
        previewCTA.muted = true;
    }
    
    // Setup logo image
    const logoImagePreview = document.querySelector('#logoPreview .preview-image');
    if (logoImagePreview && logoImagePreview.src) {
        previewLogo = document.createElement('img');
        previewLogo.src = logoImagePreview.src;
        previewLogo.crossOrigin = 'anonymous';
    }
}

function renderPreviewFrame() {
    if (!previewCanvas || !previewCtx || !previewMainVideo) return;
    
    const canvas = previewCanvas;
    const ctx = previewCtx;
    
    // Set canvas size
    canvas.width = 1280;
    canvas.height = 720;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw main video
    if (previewMainVideo.readyState >= 2) {
        ctx.drawImage(previewMainVideo, 0, 0, canvas.width, canvas.height);
    }
    
    // Get current settings
    const startTime = parseFloat(document.getElementById('startTime').value);
    const duration = parseFloat(document.getElementById('duration').value);
    const currentTime = previewMainVideo.currentTime;
    
    // Check if CTA should be visible
    if (previewCTA && currentTime >= startTime && currentTime <= (startTime + duration)) {
        if (previewCTA.readyState >= 2) {
            const ctaTime = currentTime - startTime;
            previewCTA.currentTime = ctaTime;
            
            // Get position settings
            const xPos = parseInt(document.getElementById('xPos').value);
            const yPos = parseInt(document.getElementById('yPos').value);
            const scale = parseFloat(document.getElementById('scale').value);
            
            const ctaWidth = 320 * scale;
            const ctaHeight = 180 * scale;
            const ctaX = canvas.width - ctaWidth - 50 + xPos;
            const ctaY = 50 + yPos;
            
            ctx.drawImage(previewCTA, ctaX, ctaY, ctaWidth, ctaHeight);
        }
    }
    
    // Draw logo if present
    if (previewLogo && previewLogo.complete) {
        const logoScale = 0.3;
        const logoWidth = previewLogo.width * logoScale;
        const logoHeight = previewLogo.height * logoScale;
        const logoX = canvas.width - logoWidth - 20;
        const logoY = canvas.height - logoHeight - 20;
        
        ctx.drawImage(previewLogo, logoX, logoY, logoWidth, logoHeight);
    }
    
    // Update timeline and time display
    const timeline = document.getElementById('previewTimeline');
    if (previewMainVideo.duration) {
        timeline.max = previewMainVideo.duration;
        timeline.value = previewMainVideo.currentTime;
        updateTimeDisplay(previewMainVideo.currentTime, previewMainVideo.duration);
    }
    
    if (isPreviewPlaying) {
        previewMainVideo.play();
        previewAnimationId = requestAnimationFrame(renderPreviewFrame);
    }
}

function seekPreview(value) {
    if (previewMainVideo) {
        previewMainVideo.currentTime = parseFloat(value);
        renderPreviewFrame();
    }
}

function updateTimeDisplay(current, total) {
    const currentTimeEl = document.getElementById('currentTime');
    const totalTimeEl = document.getElementById('totalTime');
    
    if (currentTimeEl && totalTimeEl) {
        currentTimeEl.textContent = formatTime(current);
        totalTimeEl.textContent = formatTime(total);
    }
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}


// File Removal Functions
function removeFile(type, event) {
    // Stop event propagation to prevent triggering file picker
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    // Clear file IDs
    if (type === 'foreground') {
        foregroundFileId = null;
        foregroundFileName = null;
    } else if (type === 'background') {
        backgroundFileId = null;
        backgroundFileName = null;
        // Clear anche i dati del video scaricato dal web
        window.downloadedWebVideoData = null;
    } else if (type === 'logo') {
        logoFileId = null;
        logoFileName = null;
    }

    // Remove from all tabs
    removeFileFromAllTabs(type);

    // Reset preview if background video was removed
    if (type === 'background') {
        resetPreview();

        // Nascondi pulsante download e ripristina area upload
        const downloadBtn = document.getElementById('downloadMainVideoBtn');
        if (downloadBtn) {
            downloadBtn.style.display = 'none';
        }

        // Ripristina area upload nella tab Caricamento Video
        const uploadArea = document.getElementById('mainVideoUpload');
        const uploadContent = uploadArea?.querySelector('.upload-content');
        const previewOverlay = document.getElementById('mainVideoPreviewOverlay');

        if (uploadContent) {
            uploadContent.style.display = 'flex';
        }
        if (previewOverlay) {
            previewOverlay.style.display = 'none';
        }

        // Ripristina anche area upload nella tab Logo e CTA
        const logoTabUploadArea = document.getElementById('logoTabMainVideoUpload');
        if (logoTabUploadArea) {
            const logoTabUploadContent = logoTabUploadArea.querySelector('.upload-content');
            const logoTabPreviewOverlay = document.getElementById('logoTabMainVideoPreviewOverlay');

            if (logoTabUploadContent) {
                logoTabUploadContent.style.display = 'flex';
            }
            if (logoTabPreviewOverlay) {
                logoTabPreviewOverlay.style.display = 'none';
                // Clear video source
                const video = logoTabPreviewOverlay.querySelector('video');
                if (video) {
                    video.src = '';
                }
            }

            // Reset border and background styles
            logoTabUploadArea.style.borderColor = '';
            logoTabUploadArea.style.background = '';
        }
    }

    // IMPORTANTE: Salva le modifiche nel localStorage per evitare che riappaia al reload
    saveSettings();
    console.log('✅ Settings salvato dopo rimozione file:', type, {
        foregroundFileId,
        backgroundFileId,
        logoFileId
    });

    showAlert(`File ${type === 'foreground' ? 'Call to Action' : type === 'background' ? 'principale' : 'logo'} rimosso`, 'info');
}

function removeFileFromAllTabs(type) {
    const fileInfoMap = {
        'foreground': 'ctaInfo',
        'background': 'mainVideoInfo', 
        'logo': 'logoInfo'
    };
    
    const previewMap = {
        'foreground': 'ctaPreview',
        'background': 'mainVideoPreview',
        'logo': 'logoPreview'
    };
    
    const fileInputMap = {
        'foreground': 'ctaFile',
        'background': 'mainVideoFile',
        'logo': 'logoFile'
    };

    const advancedFileInputMap = {
        'foreground': 'ctaAdvancedFile',
        'background': 'logoTabMainVideoFile',
        'logo': 'logoAdvancedFile'
    };
    
    // Hide file info in main tab
    const fileInfo = document.getElementById(fileInfoMap[type]);
    if (fileInfo) {
        fileInfo.classList.remove('active');
    }
    
    // Hide preview in main tab
    const preview = document.getElementById(previewMap[type]);
    if (preview) {
        preview.classList.remove('active');
        const video = preview.querySelector('video');
        const img = preview.querySelector('img');
        if (video) video.src = '';
        if (img) img.src = '';
    }
    
    // Hide overlay preview
    const previewOverlayMap = {
        'foreground': 'ctaPreviewOverlay',
        'background': 'mainVideoPreviewOverlay',
        'logo': 'logoPreviewOverlay'
    };
    const advancedPreviewOverlayMap = {
        'foreground': 'ctaAdvancedPreviewOverlay',
        'background': 'logoTabMainVideoPreviewOverlay',
        'logo': 'logoAdvancedPreviewOverlay'
    };

    const previewOverlay = document.getElementById(previewOverlayMap[type]);
    if (previewOverlay) {
        previewOverlay.classList.remove('active');
        const overlayVideo = previewOverlay.querySelector('.preview-video-overlay');
        const overlayImg = previewOverlay.querySelector('.preview-image-overlay');
        if (overlayVideo) overlayVideo.src = '';
        if (overlayImg) overlayImg.src = '';
    }

    // Hide advanced overlay preview
    const advancedPreviewOverlay = document.getElementById(advancedPreviewOverlayMap[type]);
    if (advancedPreviewOverlay) {
        // Remove active class if present
        advancedPreviewOverlay.classList.remove('active');
        // Also hide using inline style for tab Logo e CTA
        advancedPreviewOverlay.style.display = 'none';

        const advancedOverlayVideo = advancedPreviewOverlay.querySelector('.preview-video-overlay');
        const advancedOverlayImg = advancedPreviewOverlay.querySelector('.preview-image-overlay');
        if (advancedOverlayVideo) advancedOverlayVideo.src = '';
        if (advancedOverlayImg) advancedOverlayImg.src = '';
    }
    
    // Clear all file inputs
    const fileInput = document.getElementById(fileInputMap[type]);
    if (fileInput) {
        fileInput.value = '';
    }
    
    const advancedFileInput = document.getElementById(advancedFileInputMap[type]);
    if (advancedFileInput) {
        advancedFileInput.value = '';
    }
    
    // Reset advanced upload areas
    resetAdvancedUploadArea(type);
}

function resetAdvancedUploadArea(type) {
    let uploadArea = null;
    let defaultIcon = '';
    let defaultText = '';

    if (type === 'logo') {
        uploadArea = document.getElementById('logoAdvancedUpload');
        defaultIcon = 'fas fa-image upload-icon';
        defaultText = '<i class="fas fa-upload"></i> Carica';
    } else if (type === 'foreground') {
        uploadArea = document.getElementById('ctaAdvancedUpload');
        defaultIcon = 'fas fa-play upload-icon';
        defaultText = '<i class="fas fa-upload"></i> Carica';
    } else if (type === 'background') {
        uploadArea = document.getElementById('logoTabMainVideoUpload');
        defaultIcon = 'fas fa-video upload-icon';
        defaultText = '<i class="fas fa-upload"></i> Carica';
    }

    if (uploadArea) {
        const uploadContent = uploadArea.querySelector('.upload-content');
        const icon = uploadContent?.querySelector('.upload-icon');
        const button = uploadContent?.querySelector('.upload-btn');

        if (icon && button) {
            icon.className = defaultIcon;
            icon.style.color = '#3b82f6';
            button.innerHTML = defaultText;

            uploadArea.style.borderColor = 'rgba(59, 130, 246, 0.4)';
            uploadArea.style.background = 'rgba(59, 130, 246, 0.05)';
        }

        // Show upload content and hide preview
        if (uploadContent) {
            uploadContent.style.display = 'flex';
        }
    }
}

// Enhanced Preview with Chromakey - Now opens modal
async function previewVideo() {
    if (!foregroundFileId || !backgroundFileId) {
        showAlert('Carica sia il video principale che la Call to Action per vedere l\'anteprima', 'warning');
        return;
    }
    
    // Open preview modal
    openPreviewModal();
    
    // Start enhanced preview with chromakey simulation
    setTimeout(() => {
        initializeEnhancedPreview();
    }, 200);
}

// Modal Management Functions
function openPreviewModal() {
    const modal = document.getElementById('previewModal');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden'; // Prevent background scroll
    }
}

function closePreviewModal() {
    const modal = document.getElementById('previewModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = ''; // Restore scroll
        
        // Stop enhanced preview animation
        isPreviewPlaying = false;
        
        // Reset preview overlay to show default message
        const overlay = document.getElementById('previewOverlay');
        if (overlay) {
            overlay.classList.remove('hidden');
            overlay.innerHTML = '<div class="preview-placeholder"><i class="fas fa-play"></i><p>Carica video principale e CTA per vedere l\'anteprima</p></div>';
        }
        
        // Stop preview if playing (legacy)
        pausePreview();
        resetPreview();
    }
}

function processVideoFromPreview() {
    // Close modal and start processing
    closePreviewModal();
    processVideo();
}

function initializeEnhancedPreview() {
    const canvas = document.getElementById('previewCanvas');
    const overlay = document.getElementById('previewOverlay');
    
    console.log('Initializing enhanced preview...');
    
    if (!canvas) {
        console.error('Preview canvas not found');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    canvas.width = 1280;
    canvas.height = 720;
    
    // Debug: Check all possible video selectors
    console.log('Looking for video elements...');
    
    // Get video elements from overlay previews (the new system)
    const mainVideoOverlay = document.querySelector('#mainVideoPreviewOverlay .preview-video-overlay');
    const ctaVideoOverlay = document.querySelector('#ctaPreviewOverlay .preview-video-overlay');
    
    // Try legacy preview elements as fallback
    const mainVideoLegacy = document.querySelector('#mainVideoPreview .preview-video');
    const ctaVideoLegacy = document.querySelector('#ctaPreview .preview-video');
    
    // Also check for video elements directly in upload areas
    const mainVideoUpload = document.querySelector('#mainVideoUpload video');
    const ctaVideoUpload = document.querySelector('#foregroundVideoUpload video, #ctaUpload video');
    
    console.log('Video search results:', {
        mainVideoOverlay: !!mainVideoOverlay,
        ctaVideoOverlay: !!ctaVideoOverlay,
        mainVideoLegacy: !!mainVideoLegacy,
        ctaVideoLegacy: !!ctaVideoLegacy,
        mainVideoUpload: !!mainVideoUpload,
        ctaVideoUpload: !!ctaVideoUpload
    });
    
    const mainVideo = mainVideoOverlay || mainVideoLegacy || mainVideoUpload;
    const ctaVideo = ctaVideoOverlay || ctaVideoLegacy || ctaVideoUpload;
    
    // Get file paths from server instead of blob URLs
    let mainVideoSrc = null;
    let ctaVideoSrc = null;
    
    if (backgroundFileId) {
        mainVideoSrc = `/uploads/${backgroundFileId}.mp4`;
    }
    
    if (foregroundFileId) {
        ctaVideoSrc = `/uploads/${foregroundFileId}.mp4`;
    }
    
    console.log('Selected videos:', {
        mainVideo: !!mainVideo,
        ctaVideo: !!ctaVideo,
        mainSrc: mainVideo?.src,
        ctaSrc: ctaVideo?.src,
        serverMainSrc: mainVideoSrc,
        serverCtaSrc: ctaVideoSrc,
        backgroundFileId: backgroundFileId,
        foregroundFileId: foregroundFileId
    });
    
    if (!mainVideo || !ctaVideo || !mainVideoSrc || !ctaVideoSrc) {
        console.log('Videos not ready - keeping overlay message visible');
        if (overlay) {
            overlay.classList.remove('hidden');
        }
        return;
    }
    
    console.log('Videos found - initializing preview');
    
    // Hide the overlay message since we have videos
    if (overlay) {
        overlay.classList.add('hidden');
    }
    
    // Create video elements for canvas rendering using server paths
    const mainVideoElement = document.createElement('video');
    mainVideoElement.src = mainVideoSrc;
    mainVideoElement.muted = true;
    mainVideoElement.crossOrigin = 'anonymous';
    
    const ctaVideoElement = document.createElement('video');
    ctaVideoElement.src = ctaVideoSrc;
    ctaVideoElement.muted = true;  
    ctaVideoElement.crossOrigin = 'anonymous';
    
    console.log('Created video elements with server sources:', {
        main: mainVideoElement.src,
        cta: ctaVideoElement.src
    });
    
    // Wait for videos to load before starting preview
    let loadedCount = 0;
    const totalVideos = 2;
    
    function onVideoLoaded() {
        loadedCount++;
        console.log(`Video loaded: ${loadedCount}/${totalVideos}`);
        if (loadedCount === totalVideos) {
            console.log('Starting preview rendering...');
            // Start preview rendering
            renderEnhancedPreview(ctx, canvas, mainVideoElement, ctaVideoElement);
        }
    }
    
    function onVideoError(e) {
        console.error('Video loading error:', e.target.src, e);
        // Show error message back
        if (overlay) {
            overlay.classList.remove('hidden');
            overlay.innerHTML = '<div class="preview-placeholder"><i class="fas fa-exclamation-triangle" style="color: #f59e0b;"></i><p>Errore nel caricamento dei video</p><small>Verifica che i file siano validi</small></div>';
        }
    }
    
    mainVideoElement.onloadeddata = onVideoLoaded;
    ctaVideoElement.onloadeddata = onVideoLoaded;
    mainVideoElement.onerror = onVideoError;
    ctaVideoElement.onerror = onVideoError;
    
    // Add timeout to handle cases where videos never load
    setTimeout(() => {
        if (loadedCount < totalVideos) {
            console.warn(`Timeout: Only ${loadedCount}/${totalVideos} videos loaded`);
            if (overlay) {
                overlay.classList.remove('hidden');
                overlay.innerHTML = '<div class="preview-placeholder"><i class="fas fa-clock" style="color: #f59e0b;"></i><p>Timeout nel caricamento</p><small>I video potrebbero essere troppo grandi o corrotti</small></div>';
            }
        }
    }, 5000);
    
    // Load the videos
    mainVideoElement.load();
    ctaVideoElement.load();
}

function renderEnhancedPreview(ctx, canvas, mainVideo, ctaVideo) {
    if (!ctx || !canvas) {
        console.error('Missing canvas or context for preview rendering');
        return;
    }
    
    if (!mainVideo || !ctaVideo) {
        console.error('Missing video elements for preview rendering');
        return;
    }
    
    console.log('Starting preview rendering with videos:', {
        mainVideoReady: mainVideo.readyState,
        ctaVideoReady: ctaVideo.readyState,
        mainVideoSrc: mainVideo.src,
        ctaVideoSrc: ctaVideo.src
    });
    
    // Get CTA settings from UI
    const ctaStartTime = parseFloat(document.getElementById('ctaStartTime')?.value || 5);
    const ctaEndTimeValue = document.getElementById('ctaEndTime')?.value;
    const ctaDuration = ctaEndTimeValue && ctaEndTimeValue.trim() !== '' ? 
        parseFloat(ctaEndTimeValue) - ctaStartTime : 10;
    const ctaPosition = document.getElementById('ctaPosition')?.value || 'center';
    const ctaSize = parseInt(document.getElementById('ctaSize')?.value || 20) / 100; // Convert % to decimal
    
    // Get Logo settings from UI
    const logoStartTime = parseFloat(document.getElementById('logoStartTime')?.value || 0);
    const logoEndTimeValue = document.getElementById('logoEndTime')?.value;
    const logoPosition = document.getElementById('logoPosition')?.value || 'top-right';
    const logoSize = parseInt(document.getElementById('logoSize')?.value || 10) / 100; // Convert % to decimal
    
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw main video
        if (mainVideo.readyState >= 2) {
            ctx.drawImage(mainVideo, 0, 0, canvas.width, canvas.height);
        } else {
            // Show loading placeholder on main video area
            ctx.fillStyle = '#1f2937';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#9ca3af';
            ctx.font = '20px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Loading main video...', canvas.width / 2, canvas.height / 2);
        }
        
        const currentTime = mainVideo.currentTime;
        
        // Draw CTA with chromakey simulation using UI settings
        const ctaEndTime = ctaEndTimeValue && ctaEndTimeValue.trim() !== '' ? 
            parseFloat(ctaEndTimeValue) : ctaStartTime + ctaDuration;
        
        
        if (currentTime >= ctaStartTime && currentTime <= ctaEndTime) {
            if (ctaVideo.readyState >= 2) {
                const ctaTime = currentTime - ctaStartTime;
                ctaVideo.currentTime = ctaTime;
                
                
                // Calculate CTA size based on UI setting
                const baseCtaWidth = 320;
                const baseCtaHeight = 180;
                const ctaWidth = baseCtaWidth * ctaSize;
                const ctaHeight = baseCtaHeight * ctaSize;
                
                // Calculate CTA position based on UI setting (already accounts for element size)
                const ctaPos = getPositionCoordinates(ctaPosition, canvas.width, canvas.height, false);
                const ctaX = ctaPos.x;
                const ctaY = ctaPos.y;
                
                // Draw CTA with simulated chromakey (remove green background)
                ctx.save();
                
                // Create or reuse temporary canvas for chromakey processing
                if (!window.chromakeyCanvas) {
                    window.chromakeyCanvas = document.createElement('canvas');
                    window.chromakeyCtx = window.chromakeyCanvas.getContext('2d');
                }
                const tempCanvas = window.chromakeyCanvas;
                const tempCtx = window.chromakeyCtx;
                
                // Only resize if needed to avoid flickering
                if (tempCanvas.width !== ctaWidth || tempCanvas.height !== ctaHeight) {
                    tempCanvas.width = ctaWidth;
                    tempCanvas.height = ctaHeight;
                }
                
                // Clear the canvas
                tempCtx.clearRect(0, 0, ctaWidth, ctaHeight);
                
                // Draw CTA to temp canvas
                tempCtx.drawImage(ctaVideo, 0, 0, ctaWidth, ctaHeight);
                
                // Get image data for chromakey processing
                const imageData = tempCtx.getImageData(0, 0, ctaWidth, ctaHeight);
                const data = imageData.data;
                
                let transparentPixels = 0;
                let totalPixels = (ctaWidth * ctaHeight);
                
                // Chromakey for specific green screen colors only
                // TEMP DEBUG: Set to false to disable chromakey completely
                const enableChromakey = true;
                
                if (enableChromakey) {
                    for (let i = 0; i < data.length; i += 4) {
                        const r = data[i];
                        const g = data[i + 1];
                        const b = data[i + 2];
                        
                        // Target typical chromakey colors: green and blue
                        const isChromaGreen = (
                            // Pure bright green (RGB 0,255,0 area)
                            (g > 240 && r < 50 && b < 50) ||
                            // Studio chromakey green (RGB 50,255,50 area) 
                            (g > 230 && r < 80 && b < 80 && Math.abs(r - b) < 30)
                        );
                        
                        const isChromaBlue = (
                            // Pure bright blue (RGB 0,0,255 area)
                            (b > 240 && r < 50 && g < 50) ||
                            // Studio chromakey blue (RGB 50,50,255 area)
                            (b > 230 && r < 80 && g < 80 && Math.abs(r - g) < 30)
                        );
                        
                        if (isChromaGreen || isChromaBlue) {
                            data[i + 3] = 0; // Make transparent
                            transparentPixels++;
                        }
                    }
                }
                
                
                // Put processed data back
                tempCtx.putImageData(imageData, 0, 0);
                
                // Draw processed CTA with chromakey to main canvas
                ctx.drawImage(tempCanvas, ctaX, ctaY);
                
                // Draw subtle border for preview indication
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
                ctx.lineWidth = 1;
                ctx.setLineDash([5, 5]);
                ctx.strokeRect(ctaX, ctaY, ctaWidth, ctaHeight);
                ctx.setLineDash([]);
                
                ctx.restore();
            }
        }
        
        // Draw logo using UI settings
        const logoImg = document.querySelector('#logoPreview .preview-image');
        if (logoImg && logoImg.complete && logoImg.src && logoImg.naturalWidth > 0) {
            // Check logo timing
            const logoEndTime = logoEndTimeValue && logoEndTimeValue.trim() !== '' ? 
                parseFloat(logoEndTimeValue) : 999999; // Show for entire video if no end time
            
            if (currentTime >= logoStartTime && currentTime <= logoEndTime) {
                // Calculate logo size based on UI setting
                const logoWidth = logoImg.naturalWidth * logoSize;
                const logoHeight = logoImg.naturalHeight * logoSize;
                
                // Calculate logo position based on UI setting
                const logoPos = getPositionCoordinates(logoPosition, canvas.width, canvas.height, true);
                let logoX, logoY;
                
                // Adjust position based on logo size
                switch(logoPosition) {
                    case 'top-left':
                        logoX = logoPos.x;
                        logoY = logoPos.y;
                        break;
                    case 'top-right':
                        logoX = logoPos.x - logoWidth;
                        logoY = logoPos.y;
                        break;
                    case 'top-center':
                        logoX = logoPos.x - logoWidth / 2;
                        logoY = logoPos.y;
                        break;
                    case 'center':
                        logoX = logoPos.x - logoWidth / 2;
                        logoY = logoPos.y - logoHeight / 2;
                        break;
                    case 'bottom-left':
                        logoX = logoPos.x;
                        logoY = logoPos.y - logoHeight;
                        break;
                    case 'bottom-right':
                        logoX = logoPos.x - logoWidth;
                        logoY = logoPos.y - logoHeight;
                        break;
                    case 'bottom-center':
                        logoX = logoPos.x - logoWidth / 2;
                        logoY = logoPos.y - logoHeight;
                        break;
                    default:
                        logoX = logoPos.x - logoWidth;
                        logoY = logoPos.y;
                }
                
                ctx.drawImage(logoImg, logoX, logoY, logoWidth, logoHeight);
                
                // Debug indicator for logo
                ctx.strokeStyle = '#ff0000';
                ctx.lineWidth = 1;
                ctx.strokeRect(logoX, logoY, logoWidth, logoHeight);
                
                // Label
                ctx.fillStyle = '#ff0000';
                ctx.font = '12px Arial';
                ctx.fillText('LOGO', logoX, logoY - 5);
            }
        }
        
        if (isPreviewPlaying) {
            requestAnimationFrame(animate);
        }
    }
    
    // Set preview playing flag and start animation
    isPreviewPlaying = true;
    mainVideo.play();
    ctaVideo.play();
    animate();
}

// Export functions for global access
window.toggleSidebar = toggleSidebar;
window.showTab = showTab;
window.updateValue = updateValue;
window.updateSliderValue = updateSliderValue;
window.processVideo = processVideo;
window.stopProcessing = stopProcessing;
window.downloadVideo = downloadVideo;
window.newProject = newProject;
window.showHelp = showHelp;
window.togglePreview = togglePreview;
window.resetPreview = resetPreview;
window.seekPreview = seekPreview;
window.removeFile = removeFile;
window.previewVideo = previewVideo;
window.openPreviewModal = openPreviewModal;
window.closePreviewModal = closePreviewModal;
window.processVideoFromPreview = processVideoFromPreview;
window.showValidationModal = showValidationModal;
window.closeValidationModal = closeValidationModal;
window.goToFeatures = goToFeatures;
window.showProcessingConfirmModal = showProcessingConfirmModal;
window.closeProcessingConfirmModal = closeProcessingConfirmModal;
window.confirmProcessing = confirmProcessing;
window.showMissingFilesModal = showMissingFilesModal;
window.closeMissingFilesModal = closeMissingFilesModal;
window.applyOverlayDirectly = applyOverlayDirectly;

// Processing Confirmation Modal Functions
function showProcessingConfirmModal() {
    const modal = document.getElementById('processingConfirmModal');
    if (!modal) return;
    
    // Get selected features
    const selectedFeatures = [];
    const featureMappings = {
        'logoOverlay': { name: 'Sovrapposizione Logo', icon: 'fas fa-image' },
        'callToAction': { name: 'Sovrapposizione Call to Action', icon: 'fas fa-play-circle' },
        'videoTranscription': { name: 'Trascrizione Video', icon: 'fas fa-closed-captioning' },
        'audioTranslation': { name: 'Traduzione Audio Video', icon: 'fas fa-language' },
        'coverGeneration': { name: 'Generazione Copertina', icon: 'fas fa-file-image' },
        'metadataGeneration': { name: 'Generazione Metadati', icon: 'fas fa-tags' },
        'youtubeUpload': { name: 'Caricamento YouTube', icon: 'fas fa-upload' }
    };
    
    Object.keys(featureMappings).forEach(featureId => {
        const toggle = document.getElementById(featureId);
        if (toggle && toggle.checked) {
            selectedFeatures.push(featureMappings[featureId]);
        }
    });
    
    // Populate features list
    const featuresList = document.getElementById('selectedFeaturesList');
    if (featuresList) {
        featuresList.innerHTML = selectedFeatures.map(feature => 
            `<div class="feature-item">
                <i class="${feature.icon}"></i>
                <span>${feature.name}</span>
            </div>`
        ).join('');
    }
    
    // Update quality info
    const qualitySelect = document.getElementById('qualityPreset');
    const qualityDisplay = document.getElementById('selectedQuality');
    if (qualitySelect && qualityDisplay) {
        const qualityOptions = {
            'draft': 'Bozza (720p)',
            'good': 'Buona (1080p)',
            'high': 'Alta (1080p)',
            'ultra': 'Ultra (1080p)'
        };
        qualityDisplay.textContent = qualityOptions[qualitySelect.value] || 'Ultra (1080p)';
    }
    
    // Estimate time based on features
    const timeEstimate = selectedFeatures.length <= 2 ? '2-4 minuti' : '4-8 minuti';
    const timeDisplay = document.getElementById('estimatedTime');
    if (timeDisplay) {
        timeDisplay.textContent = timeEstimate;
    }
    
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeProcessingConfirmModal() {
    const modal = document.getElementById('processingConfirmModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

function confirmProcessing() {
    closeProcessingConfirmModal();
    actuallyProcessVideo();
}

// Missing Files Modal Functions
function showMissingFilesModal(missingFiles) {
    const modal = document.getElementById('missingFilesModal');
    if (!modal) return;
    
    // Populate missing files list
    const filesList = document.getElementById('missingFilesList');
    if (filesList && missingFiles.length > 0) {
        filesList.innerHTML = missingFiles.map(file => 
            `<div class="missing-file-item">
                <i class="${file.icon}"></i>
                <div>
                    <strong>${file.name}</strong>
                    <div style="font-size: 0.9em; color: #6b7280; font-weight: normal;">${file.description}</div>
                </div>
            </div>`
        ).join('');
    }
    
    // Update message based on number of missing files
    const messageElement = document.getElementById('missingFilesMessage');
    if (messageElement) {
        if (missingFiles.length === 1) {
            messageElement.textContent = 'Per elaborare il video devi caricare il file richiesto:';
        } else {
            messageElement.textContent = 'Per elaborare il video devi caricare tutti i file richiesti:';
        }
    }
    
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeMissingFilesModal() {
    const modal = document.getElementById('missingFilesModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

async function actuallyProcessVideo() {
    console.log('Actually processing video...');
    
    let formData;
    try {
        formData = createProcessingFormData();
        console.log('FormData created:', formData);
    } catch (error) {
        console.error('Error creating FormData:', error);
        showAlert('Errore nella creazione dei dati: ' + error.message, 'error');
        return;
    }
    
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
        console.error('Processing error:', error);
        showAlert('Errore di connessione: ' + error.message, 'error');
    }
}

// Validate inputs specifically for overlay application (Logo & CTA tab)
function validateOverlayInputs() {
    console.log('validateOverlayInputs() called');
    console.log('backgroundFileId:', backgroundFileId);
    console.log('foregroundFileId:', foregroundFileId);
    console.log('logoFileId:', logoFileId);

    const missingFiles = [];

    // Check for video principale (background)
    if (!backgroundFileId || backgroundFileId === null || backgroundFileId === undefined || backgroundFileId.toString().trim() === '') {
        console.log('Missing background file');
        missingFiles.push({
            name: 'Video Principale',
            icon: 'fas fa-film',
            description: 'Il video di base su cui applicare le sovrapposizioni'
        });
    }

    // Check for CTA video (foreground)
    if (!foregroundFileId || foregroundFileId === null || foregroundFileId === undefined || foregroundFileId.toString().trim() === '') {
        console.log('Missing foreground (CTA) file');
        missingFiles.push({
            name: 'Video Call to Action',
            icon: 'fas fa-play-circle',
            description: 'Il video CTA da sovrapporre'
        });
    }

    // Check for logo (optional but show in modal if missing)
    if (!logoFileId || logoFileId === null || logoFileId === undefined || logoFileId.toString().trim() === '') {
        console.log('Missing logo file');
        missingFiles.push({
            name: 'Logo',
            icon: 'fas fa-image',
            description: 'L\'immagine del logo da sovrapporre'
        });
    }

    if (missingFiles.length > 0) {
        console.log('Missing files for overlay:', missingFiles.map(f => f.name));
        showMissingFilesModal(missingFiles);
        return false;
    }

    console.log('All overlay files present');
    return true;
}

// Apply overlay directly without confirmation modal (for Logo & CTA tab)
async function applyOverlayDirectly() {
    console.log('applyOverlayDirectly() called');
    console.log('Current foregroundFileId:', foregroundFileId);
    console.log('Current backgroundFileId:', backgroundFileId);
    console.log('Current logoFileId:', logoFileId);

    // Validate inputs specifically for overlay
    if (!validateOverlayInputs()) {
        console.log('Overlay validation failed - stopping process');
        return;
    }
    console.log('Overlay validation passed - starting processing directly');

    // Show modal IMMEDIATELY
    showProcessingModal('Preparazione elaborazione...', 0, 'Caricamento file...');

    // Start processing directly
    await actuallyProcessVideo();
}

// ===================================
// INTERACTIVE PREVIEW DRAG & DROP
// ===================================

// Preview state
const previewState = {
    canvas: null,
    ctx: null,
    mainVideo: null,
    logoElement: null,
    ctaElement: null,
    dragging: null,
    resizing: null,
    resizeHandle: null,
    startX: 0,
    startY: 0,
    startLeft: 0,
    startTop: 0,
    startWidth: 0,
    startHeight: 0
};

// Initialize preview canvas when files are loaded
function initializePreviewCanvas() {
    console.log('🎨 Initializing interactive preview canvas');

    const previewSection = document.getElementById('interactivePreviewSection');
    const canvas = document.getElementById('previewCanvas');
    const logoElement = document.getElementById('draggableLogo');
    const ctaElement = document.getElementById('draggableCTA');

    if (!previewSection || !canvas) {
        console.error('Preview elements not found');
        return;
    }

    previewState.canvas = canvas;
    previewState.ctx = canvas.getContext('2d');
    previewState.logoElement = logoElement;
    previewState.ctaElement = ctaElement;

    // Set canvas dimensions
    const container = canvas.parentElement;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;

    // Show preview section
    previewSection.style.display = 'block';

    // Draw video frame on canvas
    drawVideoFrameOnCanvas();

    // Initialize draggable elements
    initializeDraggableElements();

    console.log('✅ Preview canvas initialized');
}

// Draw video frame on canvas
function drawVideoFrameOnCanvas() {
    const canvas = previewState.canvas;
    const ctx = previewState.ctx;

    if (!canvas || !ctx) {
        console.warn('⚠️ Canvas or context not available for drawing');
        return;
    }

    // Get main video element - try both locations
    const mainVideoPreview = document.querySelector('#logoTabMainVideoPreviewOverlay video, #mainVideoPreviewOverlay video');

    console.log('🎬 Drawing video frame on canvas. Video element found:', !!mainVideoPreview, 'Has src:', !!mainVideoPreview?.src);

    if (mainVideoPreview && mainVideoPreview.src) {
        // Function to actually draw the frame
        const drawFrame = () => {
            try {
                // Clear canvas with black background
                ctx.fillStyle = '#000';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                // Draw video frame maintaining aspect ratio
                const videoAspect = mainVideoPreview.videoWidth / mainVideoPreview.videoHeight;
                const canvasAspect = canvas.width / canvas.height;

                let drawWidth, drawHeight, offsetX, offsetY;

                if (videoAspect > canvasAspect) {
                    // Video is wider - fit to width
                    drawWidth = canvas.width;
                    drawHeight = canvas.width / videoAspect;
                    offsetX = 0;
                    offsetY = (canvas.height - drawHeight) / 2;
                } else {
                    // Video is taller - fit to height
                    drawHeight = canvas.height;
                    drawWidth = canvas.height * videoAspect;
                    offsetX = (canvas.width - drawWidth) / 2;
                    offsetY = 0;
                }

                ctx.drawImage(mainVideoPreview, offsetX, offsetY, drawWidth, drawHeight);
                console.log('✅ Video frame drawn on canvas');
            } catch (error) {
                console.error('❌ Error drawing video frame:', error);
                drawPlaceholder();
            }
        };

        // If video already loaded, draw immediately
        if (mainVideoPreview.readyState >= 2) {
            drawFrame();
        } else {
            // Wait for video to load
            mainVideoPreview.addEventListener('loadeddata', drawFrame, { once: true });
            console.log('⏳ Waiting for video to load before drawing');
        }

        // Store reference to update canvas on video play/seek
        previewState.mainVideo = mainVideoPreview;
    } else {
        drawPlaceholder();
    }
}

// Draw placeholder when no video
function drawPlaceholder() {
    const canvas = previewState.canvas;
    const ctx = previewState.ctx;

    if (!canvas || !ctx) return;

    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#666';
    ctx.font = '20px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('Carica un video principale per vedere l\'anteprima', canvas.width / 2, canvas.height / 2);
    console.log('📄 Placeholder drawn on canvas');
}

// Update canvas when main video changes
function updateCanvasWithMainVideo() {
    console.log('🔄 Updating canvas with main video');

    // Initialize canvas if not done yet
    if (!previewState.canvas) {
        initializePreviewCanvas();
    } else {
        // Redraw with new video
        drawVideoFrameOnCanvas();
    }
}

// Initialize draggable elements
function initializeDraggableElements() {
    const logoElement = previewState.logoElement;
    const ctaElement = previewState.ctaElement;

    if (logoElement) {
        setupDraggableElement(logoElement, 'logo');
    }

    if (ctaElement) {
        setupDraggableElement(ctaElement, 'cta');
    }
}

// Setup individual draggable element
function setupDraggableElement(element, type) {
    // Mouse down on element (start dragging)
    element.addEventListener('mousedown', (e) => {
        if (e.target.classList.contains('resize-handle')) {
            startResize(e, element, type);
        } else {
            startDrag(e, element, type);
        }
    });

    // Make element active on click
    element.addEventListener('click', (e) => {
        e.stopPropagation();
        setActiveElement(element);
    });
}

// Start dragging
function startDrag(e, element, type) {
    e.preventDefault();
    e.stopPropagation();

    previewState.dragging = { element, type };
    previewState.startX = e.clientX;
    previewState.startY = e.clientY;
    previewState.startLeft = element.offsetLeft;
    previewState.startTop = element.offsetTop;

    setActiveElement(element);

    console.log(`🖱️ Started dragging ${type}`);
}

// Start resizing
function startResize(e, element, type) {
    e.preventDefault();
    e.stopPropagation();

    const handle = e.target;
    const handleClass = handle.classList.contains('nw') ? 'nw' :
                       handle.classList.contains('ne') ? 'ne' :
                       handle.classList.contains('sw') ? 'sw' : 'se';

    previewState.resizing = { element, type };
    previewState.resizeHandle = handleClass;
    previewState.startX = e.clientX;
    previewState.startY = e.clientY;
    previewState.startLeft = element.offsetLeft;
    previewState.startTop = element.offsetTop;
    previewState.startWidth = element.offsetWidth;
    previewState.startHeight = element.offsetHeight;

    setActiveElement(element);

    console.log(`📏 Started resizing ${type} from ${handleClass} corner`);
}

// Mouse move handler
document.addEventListener('mousemove', (e) => {
    if (previewState.dragging) {
        handleDrag(e);
    } else if (previewState.resizing) {
        handleResize(e);
    }
});

// Mouse up handler
document.addEventListener('mouseup', () => {
    if (previewState.dragging) {
        console.log(`✅ Finished dragging ${previewState.dragging.type}`);
        syncPositionToInputs(previewState.dragging.type);
        previewState.dragging = null;
    }

    if (previewState.resizing) {
        console.log(`✅ Finished resizing ${previewState.resizing.type}`);
        syncSizeToInputs(previewState.resizing.type);
        previewState.resizing = null;
        previewState.resizeHandle = null;
    }
});

// Handle dragging
function handleDrag(e) {
    const { element } = previewState.dragging;
    const container = previewState.canvas.parentElement;

    const deltaX = e.clientX - previewState.startX;
    const deltaY = e.clientY - previewState.startY;

    let newLeft = previewState.startLeft + deltaX;
    let newTop = previewState.startTop + deltaY;

    // Constrain within container
    newLeft = Math.max(0, Math.min(newLeft, container.clientWidth - element.offsetWidth));
    newTop = Math.max(0, Math.min(newTop, container.clientHeight - element.offsetHeight));

    element.style.left = newLeft + 'px';
    element.style.top = newTop + 'px';
}

// Handle resizing
function handleResize(e) {
    const { element } = previewState.resizing;
    const handle = previewState.resizeHandle;
    const container = previewState.canvas.parentElement;

    const deltaX = e.clientX - previewState.startX;
    const deltaY = e.clientY - previewState.startY;

    let newWidth = previewState.startWidth;
    let newHeight = previewState.startHeight;
    let newLeft = previewState.startLeft;
    let newTop = previewState.startTop;

    // Calculate new dimensions based on handle
    if (handle === 'se') {
        newWidth = previewState.startWidth + deltaX;
        newHeight = previewState.startHeight + deltaY;
    } else if (handle === 'sw') {
        newWidth = previewState.startWidth - deltaX;
        newHeight = previewState.startHeight + deltaY;
        newLeft = previewState.startLeft + deltaX;
    } else if (handle === 'ne') {
        newWidth = previewState.startWidth + deltaX;
        newHeight = previewState.startHeight - deltaY;
        newTop = previewState.startTop + deltaY;
    } else if (handle === 'nw') {
        newWidth = previewState.startWidth - deltaX;
        newHeight = previewState.startHeight - deltaY;
        newLeft = previewState.startLeft + deltaX;
        newTop = previewState.startTop + deltaY;
    }

    // Maintain aspect ratio
    const aspectRatio = previewState.startWidth / previewState.startHeight;
    newHeight = newWidth / aspectRatio;

    // Apply minimum size
    const minSize = 50;
    if (newWidth < minSize || newHeight < minSize) {
        return;
    }

    // Constrain within container
    if (newLeft < 0 || newTop < 0 ||
        newLeft + newWidth > container.clientWidth ||
        newTop + newHeight > container.clientHeight) {
        return;
    }

    element.style.width = newWidth + 'px';
    element.style.height = newHeight + 'px';
    element.style.left = newLeft + 'px';
    element.style.top = newTop + 'px';
}

// Set active element
function setActiveElement(element) {
    // Remove active class from all elements
    document.querySelectorAll('.draggable-element').forEach(el => {
        el.classList.remove('active');
    });

    // Add active class to clicked element
    element.classList.add('active');
}

// Click on canvas to deselect all
document.addEventListener('click', (e) => {
    if (e.target === previewState.canvas || e.target.classList.contains('preview-canvas-container')) {
        document.querySelectorAll('.draggable-element').forEach(el => {
            el.classList.remove('active');
        });
    }
});

// Sync position to form inputs
function syncPositionToInputs(type) {
    const element = type === 'logo' ? previewState.logoElement : previewState.ctaElement;
    const container = previewState.canvas.parentElement;

    if (!element || !container) return;

    const left = element.offsetLeft;
    const top = element.offsetTop;
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;

    // Calculate percentage position
    const xPercent = (left / containerWidth) * 100;
    const yPercent = (top / containerHeight) * 100;

    console.log(`📍 ${type} position: ${xPercent.toFixed(1)}% x ${yPercent.toFixed(1)}%`);

    // Update position select based on location
    const positionSelect = document.getElementById(type === 'logo' ? 'logoPosition' : 'ctaPosition');
    if (positionSelect) {
        // Determine closest preset position
        let closestPosition = 'center';

        if (xPercent < 33 && yPercent < 33) closestPosition = 'top-left';
        else if (xPercent > 66 && yPercent < 33) closestPosition = 'top-right';
        else if (xPercent >= 33 && xPercent <= 66 && yPercent < 33) closestPosition = 'top-center';
        else if (xPercent < 33 && yPercent > 66) closestPosition = 'bottom-left';
        else if (xPercent > 66 && yPercent > 66) closestPosition = 'bottom-right';
        else if (xPercent >= 33 && xPercent <= 66 && yPercent > 66) closestPosition = 'bottom-center';

        positionSelect.value = closestPosition;
        console.log(`📍 Updated ${type} position select to: ${closestPosition}`);

        // Save settings automatically
        saveSettings();
    }
}

// Sync size to form inputs
function syncSizeToInputs(type) {
    const element = type === 'logo' ? previewState.logoElement : previewState.ctaElement;
    const container = previewState.canvas.parentElement;

    if (!element || !container) return;

    const width = element.offsetWidth;
    const containerWidth = container.clientWidth;

    // Calculate percentage size
    const sizePercent = Math.round((width / containerWidth) * 100);

    console.log(`📐 ${type} size: ${sizePercent}%`);

    // Update size slider
    const sizeSlider = document.getElementById(type === 'logo' ? 'logoSize' : 'ctaSize');
    const sizeValue = document.getElementById(type === 'logo' ? 'logoSizeValue' : 'ctaSizeValue');

    if (sizeSlider && sizeValue) {
        sizeSlider.value = sizePercent;
        sizeValue.textContent = sizePercent + '%';
        console.log(`📐 Updated ${type} size slider to: ${sizePercent}%`);

        // Save settings automatically
        saveSettings();
    }
}

// Update preview when logo is uploaded
function updateLogoPreview(file) {
    console.log('🎨 updateLogoPreview called');

    // Initialize preview canvas FIRST if not done
    if (!previewState.canvas) {
        console.log('📦 Initializing preview canvas from logo upload');
        initializePreviewCanvas();
    }

    const logoElement = document.getElementById('draggableLogo');
    const logoImage = document.getElementById('logoPreviewImage');

    if (!logoElement || !logoImage) {
        console.error('❌ Logo preview elements not found:', { logoElement: !!logoElement, logoImage: !!logoImage });
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        logoImage.src = e.target.result;

        // Show logo element and position it
        logoElement.style.display = 'block';

        // Wait for image to load before positioning
        logoImage.onload = () => {
            positionElementFromInputs('logo');
            console.log('✅ Logo preview updated and positioned');

            // If main video already loaded, update canvas background
            if (backgroundFileId) {
                console.log('🎬 Main video already loaded, updating canvas');
                drawVideoFrameOnCanvas();
            }
        };
    };
    reader.readAsDataURL(file);
}

// Update preview when CTA is uploaded
function updateCTAPreview(file) {
    console.log('🎬 updateCTAPreview called');

    // Initialize preview canvas FIRST if not done
    if (!previewState.canvas) {
        console.log('📦 Initializing preview canvas from CTA upload');
        initializePreviewCanvas();
    }

    const ctaElement = document.getElementById('draggableCTA');
    const ctaVideo = document.getElementById('ctaPreviewVideo');

    if (!ctaElement || !ctaVideo) {
        console.error('❌ CTA preview elements not found:', { ctaElement: !!ctaElement, ctaVideo: !!ctaVideo });
        return;
    }

    const url = URL.createObjectURL(file);
    ctaVideo.src = url;

    // Show CTA element and position it
    ctaElement.style.display = 'block';
    ctaVideo.load();
    ctaVideo.play().catch(() => {}); // Auto-play preview (muted)

    // Wait for video to be ready before positioning
    ctaVideo.addEventListener('loadedmetadata', () => {
        positionElementFromInputs('cta');
        console.log('✅ CTA preview updated and positioned');

        // If main video already loaded, update canvas background
        if (backgroundFileId) {
            console.log('🎬 Main video already loaded, updating canvas');
            drawVideoFrameOnCanvas();
        }
    }, { once: true });
}

// Position element from form inputs
function positionElementFromInputs(type) {
    const element = document.getElementById(type === 'logo' ? 'draggableLogo' : 'draggableCTA');
    const container = document.getElementById('previewCanvas')?.parentElement;

    if (!element || !container) {
        console.warn(`⚠️ Cannot position ${type}: element or container not found`);
        return;
    }

    const positionSelect = document.getElementById(type === 'logo' ? 'logoPosition' : 'ctaPosition');
    const sizeSlider = document.getElementById(type === 'logo' ? 'logoSize' : 'ctaSize');

    if (!positionSelect || !sizeSlider) return;

    const position = positionSelect.value;
    const sizePercent = parseInt(sizeSlider.value);

    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;

    // Calculate element size
    const elementWidth = (containerWidth * sizePercent) / 100;
    const elementHeight = elementWidth; // Keep aspect ratio

    element.style.width = elementWidth + 'px';
    element.style.height = elementHeight + 'px';

    // Calculate position based on preset
    let left = 0, top = 0;

    switch (position) {
        case 'top-left':
            left = 20;
            top = 20;
            break;
        case 'top-right':
            left = containerWidth - elementWidth - 20;
            top = 20;
            break;
        case 'top-center':
            left = (containerWidth - elementWidth) / 2;
            top = 20;
            break;
        case 'center':
            left = (containerWidth - elementWidth) / 2;
            top = (containerHeight - elementHeight) / 2;
            break;
        case 'bottom-left':
            left = 20;
            top = containerHeight - elementHeight - 20;
            break;
        case 'bottom-right':
            left = containerWidth - elementWidth - 20;
            top = containerHeight - elementHeight - 20;
            break;
        case 'bottom-center':
            left = (containerWidth - elementWidth) / 2;
            top = containerHeight - elementHeight - 20;
            break;
    }

    element.style.left = left + 'px';
    element.style.top = top + 'px';

    console.log(`📍 Positioned ${type} at ${position}: ${left}px, ${top}px (${elementWidth}px size)`);
}

// ===================================
// COLLAPSIBLE ADVANCED CONTROLS
// ===================================

function toggleAdvancedControls(type) {
    const contentId = type === 'logo' ? 'logoAdvancedControls' : 'ctaAdvancedControls';
    const toggleId = type === 'logo' ? 'logoAdvancedToggle' : 'ctaAdvancedToggle';

    const content = document.getElementById(contentId);
    const toggleIcon = document.getElementById(toggleId);
    const header = toggleIcon?.closest('.advanced-controls-header');

    if (!content || !toggleIcon) {
        console.error('Advanced controls elements not found for:', type);
        return;
    }

    // Toggle collapsed class
    const isCollapsed = content.classList.contains('collapsed');

    if (isCollapsed) {
        // Expand
        content.classList.remove('collapsed');
        header?.classList.add('expanded');
        console.log(`✅ Expanded ${type} advanced controls`);
    } else {
        // Collapse
        content.classList.add('collapsed');
        header?.classList.remove('expanded');
        console.log(`✅ Collapsed ${type} advanced controls`);
    }
}

// ===================================
// CUSTOM CONFIRM/ALERT MODAL
// ===================================

let confirmModalResolve = null;

/**
 * Show custom confirm modal (replaces browser confirm)
 * @param {string} message - The message to display
 * @param {object} options - Optional configuration
 * @returns {Promise<boolean>} - Resolves to true if confirmed, false if cancelled
 */
function showConfirm(message, options = {}) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmModal');
        const header = modal.querySelector('.confirm-modal-header');
        const icon = document.getElementById('confirmModalIcon');
        const title = document.getElementById('confirmModalTitle');
        const messageEl = document.getElementById('confirmModalMessage');
        const cancelBtn = document.getElementById('confirmModalCancelBtn');
        const confirmBtn = document.getElementById('confirmModalConfirmBtn');

        // Set default options
        const config = {
            title: 'Conferma',
            type: 'warning', // 'warning', 'danger', 'success', 'info'
            confirmText: 'Conferma',
            cancelText: 'Annulla',
            confirmIcon: 'fa-check',
            cancelIcon: 'fa-times',
            ...options
        };

        // Set content
        title.textContent = config.title;
        messageEl.textContent = message;

        // Set icon based on type
        const iconMap = {
            warning: 'fa-exclamation-triangle',
            danger: 'fa-exclamation-circle',
            success: 'fa-check-circle',
            info: 'fa-info-circle'
        };
        icon.innerHTML = `<i class="fas ${iconMap[config.type] || 'fa-question-circle'}"></i>`;

        // Set header style based on type
        header.className = `modal-header confirm-modal-header ${config.type}`;

        // Set button text
        cancelBtn.innerHTML = `<i class="fas ${config.cancelIcon}"></i> ${config.cancelText}`;
        confirmBtn.innerHTML = `<i class="fas ${config.confirmIcon}"></i> ${config.confirmText}`;

        // Store resolve function
        confirmModalResolve = resolve;

        // Show modal
        modal.style.display = 'flex';

        // Add click outside to close
        modal.onclick = (e) => {
            if (e.target === modal) {
                closeConfirmModal(false);
            }
        };
    });
}

/**
 * Show custom alert modal (replaces browser alert)
 * @param {string} message - The message to display
 * @param {object} options - Optional configuration
 * @returns {Promise<void>}
 */
function showCustomAlert(message, options = {}) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmModal');
        const header = modal.querySelector('.confirm-modal-header');
        const icon = document.getElementById('confirmModalIcon');
        const title = document.getElementById('confirmModalTitle');
        const messageEl = document.getElementById('confirmModalMessage');
        const cancelBtn = document.getElementById('confirmModalCancelBtn');
        const confirmBtn = document.getElementById('confirmModalConfirmBtn');

        // Set default options
        const config = {
            title: 'Attenzione',
            type: 'info',
            confirmText: 'OK',
            confirmIcon: 'fa-check',
            ...options
        };

        // Set content
        title.textContent = config.title;
        messageEl.textContent = message;

        // Set icon based on type
        const iconMap = {
            warning: 'fa-exclamation-triangle',
            danger: 'fa-exclamation-circle',
            success: 'fa-check-circle',
            info: 'fa-info-circle'
        };
        icon.innerHTML = `<i class="fas ${iconMap[config.type] || 'fa-info-circle'}"></i>`;

        // Set header style based on type
        header.className = `modal-header confirm-modal-header ${config.type}`;

        // Hide cancel button for alerts
        cancelBtn.style.display = 'none';

        // Set confirm button text
        confirmBtn.innerHTML = `<i class="fas ${config.confirmIcon}"></i> ${config.confirmText}`;

        // Store resolve function
        confirmModalResolve = resolve;

        // Show modal
        modal.style.display = 'flex';

        // Add click outside to close
        modal.onclick = (e) => {
            if (e.target === modal) {
                closeConfirmModal(true);
            }
        };
    });
}

/**
 * Close confirm modal
 * @param {boolean} confirmed - Whether the user confirmed or cancelled
 */
function closeConfirmModal(confirmed) {
    const modal = document.getElementById('confirmModal');
    const cancelBtn = document.getElementById('confirmModalCancelBtn');

    // Reset cancel button visibility
    cancelBtn.style.display = '';

    // Hide modal
    modal.style.display = 'none';

    // Resolve promise
    if (confirmModalResolve) {
        confirmModalResolve(confirmed);
        confirmModalResolve = null;
    }
}

// ========================================
// THUMBNAIL GENERATOR FUNCTIONS
// ========================================

// Variabili globali per il generatore di miniature
let coverVideoFileId = null;
let coverImageFileId = null;
let coverFrameFileId = null;
let currentImageSource = 'ai';
let thumbnailJobId = null;
let thumbnailPollingInterval = null;

// Inizializza event listeners per il tab Copertina
document.addEventListener('DOMContentLoaded', function() {
    initializeCoverTab();
});

function initializeCoverTab() {
    console.log('Inizializzazione tab Copertina...');

    // Upload video
    const coverVideoInput = document.getElementById('coverVideoInput');
    const coverVideoDropZone = document.getElementById('coverVideoDropZone');

    if (coverVideoInput) {
        coverVideoInput.addEventListener('change', handleCoverVideoUpload);
    }

    if (coverVideoDropZone) {
        // Drag and drop per video
        coverVideoDropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            coverVideoDropZone.classList.add('dragover');
        });

        coverVideoDropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            coverVideoDropZone.classList.remove('dragover');
        });

        coverVideoDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            coverVideoDropZone.classList.remove('dragover');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleCoverVideoFile(files[0]);
            }
        });
    }

    // Upload immagine
    const coverImageInput = document.getElementById('coverImageInput');
    const coverImageDropZone = document.getElementById('coverImageDropZone');

    if (coverImageInput) {
        coverImageInput.addEventListener('change', handleCoverImageUpload);
    }

    if (coverImageDropZone) {
        coverImageDropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            coverImageDropZone.style.borderColor = '#667eea';
        });

        coverImageDropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            coverImageDropZone.style.borderColor = '#cbd5e1';
        });

        coverImageDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            coverImageDropZone.style.borderColor = '#cbd5e1';

            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type.startsWith('image/')) {
                handleCoverImageFile(files[0]);
            }
        });
    }

    // Slider opacità testo
    const textBgOpacity = document.getElementById('textBgOpacity');
    if (textBgOpacity) {
        textBgOpacity.addEventListener('input', (e) => {
            document.getElementById('textBgOpacityValue').textContent = e.target.value + '%';
            saveSettings(); // Auto-save
        });
    }

    // Auto-save per tutti i campi del tab Copertina
    const coverAutoSaveFields = [
        'coverStyle',
        'coverDescription',
        'addTextOverlay',
        'coverMainText',
        'textPosition',
        'textColor',
        'textBgColor',
        'textBgOpacity',
        'frameTimestamp'
    ];

    coverAutoSaveFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            if (field.type === 'checkbox') {
                field.addEventListener('change', saveSettings);
            } else {
                field.addEventListener('input', saveSettings);
                field.addEventListener('change', saveSettings);
            }
        }
    });

    console.log('Tab Copertina inizializzato con successo!');
}

// Gestione selezione fonte immagine
function selectImageSource(source) {
    console.log('Selezione fonte immagine:', source);
    currentImageSource = source;
    saveSettings(); // Auto-save quando cambia sorgente

    // Aggiorna UI opzioni
    document.getElementById('aiSourceOption').classList.remove('active');
    document.getElementById('uploadSourceOption').classList.remove('active');
    document.getElementById('frameSourceOption').classList.remove('active');

    document.getElementById('aiGenerationOptions').classList.remove('active');
    document.getElementById('uploadImageOptions').style.display = 'none';
    document.getElementById('frameExtractionOptions').style.display = 'none';

    if (source === 'ai') {
        document.getElementById('aiSourceOption').classList.add('active');
        document.getElementById('aiGenerationOptions').classList.add('active');
    } else if (source === 'upload') {
        document.getElementById('uploadSourceOption').classList.add('active');
        document.getElementById('uploadImageOptions').style.display = 'block';
    } else if (source === 'frame') {
        document.getElementById('frameSourceOption').classList.add('active');
        document.getElementById('frameExtractionOptions').style.display = 'block';
    }
}

// Toggle opzioni testo
function toggleTextOptions() {
    const addText = document.getElementById('addTextOverlay').checked;
    const textOptions = document.getElementById('textOverlayOptions');

    if (addText) {
        textOptions.style.display = 'block';
    } else {
        textOptions.style.display = 'none';
    }
}

// Upload video per miniatura
async function handleCoverVideoUpload(event) {
    const file = event.target.files[0];
    if (file) {
        await handleCoverVideoFile(file);
    }
}

async function handleCoverVideoFile(file) {
    console.log('Upload video per miniatura:', file.name);

    if (!file.type.startsWith('video/')) {
        showAlert('Errore', 'Il file deve essere un video', 'danger');
        return;
    }

    // Crea URL per anteprima PRIMA di fare upload (importante!)
    const videoUrl = URL.createObjectURL(file);
    console.log('Video URL creato:', videoUrl);

    const formData = new FormData();
    formData.append('file', file);

    try {
        showAlert('Upload', 'Caricamento video in corso...', 'info');

        const response = await fetch('/api/thumbnail/upload-video', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        console.log('Upload result:', result);

        if (result.success) {
            coverVideoFileId = result.file_id;

            // Nascondi drop zone
            const dropZone = document.getElementById('coverVideoDropZone');
            const previewDiv = document.getElementById('coverVideoPreview');
            const videoElement = document.getElementById('coverVideoElement');

            console.log('Elements found:', {
                dropZone: !!dropZone,
                previewDiv: !!previewDiv,
                videoElement: !!videoElement
            });

            if (dropZone) dropZone.style.display = 'none';

            // Imposta video PRIMA di mostrare preview
            if (videoElement) {
                videoElement.src = videoUrl;
                videoElement.style.display = 'block';
                videoElement.load();
                console.log('✅ Video src impostato:', videoUrl);

                // Ascolta eventi video per debug
                videoElement.addEventListener('loadeddata', () => {
                    console.log('✅ Video loaded successfully!');
                }, { once: true });

                videoElement.addEventListener('error', (e) => {
                    console.error('❌ Video error:', e);
                }, { once: true });
            } else {
                console.error('❌ Elemento video non trovato!');
            }

            // Mostra preview DIV
            if (previewDiv) {
                previewDiv.style.display = 'block';
                console.log('✅ Preview div mostrato');
            }

            // Imposta nome file
            const nameSpan = document.getElementById('coverVideoName');
            if (nameSpan) {
                nameSpan.textContent = result.filename;
            }

            showAlert('Successo', 'Video caricato con successo!', 'success');
        } else {
            showAlert('Errore', 'Errore durante il caricamento del video', 'danger');
        }
    } catch (error) {
        console.error('Errore upload video:', error);
        showAlert('Errore', 'Errore durante il caricamento: ' + error.message, 'danger');
    }
}

function removeCoverVideo() {
    coverVideoFileId = null;
    document.getElementById('coverVideoDropZone').style.display = 'block';
    document.getElementById('coverVideoPreview').style.display = 'none';
    document.getElementById('coverVideoInput').value = '';

    // Pulisci video element
    const videoElement = document.getElementById('coverVideoElement');
    if (videoElement && videoElement.src) {
        URL.revokeObjectURL(videoElement.src);
        videoElement.src = '';
        videoElement.load();
    }
}

// Upload immagine per miniatura
async function handleCoverImageUpload(event) {
    const file = event.target.files[0];
    if (file) {
        await handleCoverImageFile(file);
    }
}

async function handleCoverImageFile(file) {
    console.log('Upload immagine per miniatura:', file.name);

    if (!file.type.startsWith('image/')) {
        showAlert('Errore', 'Il file deve essere un\'immagine', 'danger');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        showAlert('Upload', 'Caricamento immagine in corso...', 'info');

        const response = await fetch('/api/thumbnail/upload-image', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            coverImageFileId = result.file_id;

            // Mostra preview
            document.getElementById('coverImagePreviewImg').src = result.preview_url;
            document.getElementById('coverImagePreview').style.display = 'block';

            showAlert('Successo', 'Immagine caricata con successo!', 'success');
        } else {
            showAlert('Errore', 'Errore durante il caricamento dell\'immagine', 'danger');
        }
    } catch (error) {
        console.error('Errore upload immagine:', error);
        showAlert('Errore', 'Errore durante il caricamento: ' + error.message, 'danger');
    }
}

function removeCoverImage() {
    coverImageFileId = null;
    document.getElementById('coverImagePreview').style.display = 'none';
    document.getElementById('coverImageInput').value = '';
}

// Estrazione frame dal video
async function extractVideoFrame() {
    if (!coverVideoFileId) {
        showAlert('Errore', 'Carica prima un video!', 'warning');
        return;
    }

    const timestamp = parseFloat(document.getElementById('frameTimestamp').value) || 5.0;

    const formData = new FormData();
    formData.append('file_id', coverVideoFileId);
    formData.append('timestamp', timestamp);

    try {
        showAlert('Estrazione', 'Estrazione frame in corso...', 'info');

        const response = await fetch('/api/thumbnail/extract-frame', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            coverFrameFileId = result.frame_id;

            // Mostra preview frame estratto
            document.getElementById('extractedFrameImg').src = result.preview_url + '?t=' + Date.now();
            document.getElementById('extractedFramePreview').style.display = 'block';

            showAlert('Successo', 'Frame estratto con successo!', 'success');
        } else {
            showAlert('Errore', 'Errore durante l\'estrazione del frame', 'danger');
        }
    } catch (error) {
        console.error('Errore estrazione frame:', error);
        showAlert('Errore', 'Errore durante l\'estrazione: ' + error.message, 'danger');
    }
}

// Generazione miniatura
async function generateThumbnail() {
    console.log('Avvio generazione miniatura...');

    // Validazione input
    if (currentImageSource === 'upload' && !coverImageFileId) {
        showAlert('Errore', 'Carica prima un\'immagine!', 'warning');
        return;
    }

    if (currentImageSource === 'frame' && !coverFrameFileId) {
        showAlert('Errore', 'Estrai prima un frame dal video!', 'warning');
        return;
    }

    // Raccogli parametri
    const formData = new FormData();
    formData.append('source_type', currentImageSource);

    if (currentImageSource === 'upload') {
        formData.append('file_id', coverImageFileId);
    } else if (currentImageSource === 'frame') {
        formData.append('file_id', coverFrameFileId);
    }

    formData.append('style', document.getElementById('coverStyle').value);
    formData.append('description', document.getElementById('coverDescription').value || '');

    const addText = document.getElementById('addTextOverlay').checked;
    formData.append('add_text', addText);

    if (addText) {
        formData.append('text_content', document.getElementById('coverMainText').value || '');
        formData.append('text_position', document.getElementById('textPosition').value);
        formData.append('text_color', document.getElementById('textColor').value);
        formData.append('text_bg_color', document.getElementById('textBgColor').value);
        formData.append('text_bg_opacity', document.getElementById('textBgOpacity').value);
    }

    try {
        // Disabilita pulsante
        const btn = document.getElementById('generateThumbnailBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generazione in corso...';

        // Mostra progress
        document.getElementById('coverGenerationProgress').style.display = 'block';
        document.getElementById('coverThumbnailResult').style.display = 'none';

        const response = await fetch('/api/thumbnail/generate', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            thumbnailJobId = result.job_id;

            // Avvia polling per monitorare progresso
            startThumbnailProgressPolling();
        } else {
            throw new Error(result.message || 'Errore generazione miniatura');
        }
    } catch (error) {
        console.error('Errore generazione miniatura:', error);
        showAlert('Errore', 'Errore durante la generazione: ' + error.message, 'danger');

        // Re-abilita pulsante
        const btn = document.getElementById('generateThumbnailBtn');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-magic"></i> Genera Miniatura AI';

        document.getElementById('coverGenerationProgress').style.display = 'none';
    }
}

// Polling progresso generazione
function startThumbnailProgressPolling() {
    if (thumbnailPollingInterval) {
        clearInterval(thumbnailPollingInterval);
    }

    thumbnailPollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/jobs/${thumbnailJobId}`);
            const job = await response.json();

            // Aggiorna progress bar
            const progressFill = document.getElementById('coverProgressFill');
            const progressText = document.getElementById('coverProgressText');

            progressFill.style.width = job.progress + '%';
            progressText.textContent = job.message;

            if (job.status === 'completed') {
                clearInterval(thumbnailPollingInterval);
                thumbnailPollingInterval = null;

                // Mostra risultato
                displayThumbnailResult(job.output_file);

                // Re-abilita pulsante
                const btn = document.getElementById('generateThumbnailBtn');
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-magic"></i> Genera Miniatura AI';

                showAlert('Successo', 'Miniatura generata con successo!', 'success');
            } else if (job.status === 'error') {
                clearInterval(thumbnailPollingInterval);
                thumbnailPollingInterval = null;

                showAlert('Errore', job.message || 'Errore durante la generazione', 'danger');

                // Re-abilita pulsante
                const btn = document.getElementById('generateThumbnailBtn');
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-magic"></i> Genera Miniatura AI';

                document.getElementById('coverGenerationProgress').style.display = 'none';
            }
        } catch (error) {
            console.error('Errore polling progresso:', error);
        }
    }, 1000);
}

// Mostra risultato miniatura
function displayThumbnailResult(outputFile) {
    document.getElementById('coverGenerationProgress').style.display = 'none';
    document.getElementById('coverThumbnailResult').style.display = 'block';

    const thumbnailImg = document.getElementById('generatedThumbnail');
    thumbnailImg.src = '/outputs/' + outputFile + '?t=' + Date.now();

    // Scroll verso il risultato
    document.getElementById('coverThumbnailResult').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Download miniatura
function downloadThumbnail() {
    if (!thumbnailJobId) return;

    const thumbnailImg = document.getElementById('generatedThumbnail');
    const link = document.createElement('a');
    link.href = thumbnailImg.src;
    link.download = `youtube_thumbnail_${thumbnailJobId}.jpg`;
    link.click();

    showAlert('Download', 'Miniatura scaricata con successo!', 'success');
}

// Rigenera miniatura
async function regenerateThumbnail() {
    const confirmed = await showConfirmDialog(
        'Rigenerare Miniatura',
        'Vuoi rigenerare la miniatura con le stesse impostazioni?',
        'info'
    );

    if (confirmed) {
        await generateThumbnail();
    }
}

// Salva miniatura nel progetto
async function saveThumbnailToProject() {
    showAlert('Salvataggio', 'Miniatura salvata nel progetto!', 'success');
    // Qui puoi implementare logica aggiuntiva per salvare nel database/progetto
}

// ========================================
// WORKFLOW AUTOMATICO
// ========================================

async function processVideoWorkflow() {
    console.log('processVideoWorkflow() chiamato');

    // Validazione: verifica che sia stato caricato almeno il video principale
    if (!backgroundFileId) {
        showAlert('Errore', 'Carica prima il video principale', 'error');
        return;
    }

    // Leggi lo stato degli switch
    const logoOverlay = document.getElementById('logoOverlay')?.checked || false;
    const callToAction = document.getElementById('callToAction')?.checked || false;
    const videoTranscription = document.getElementById('videoTranscription')?.checked || false;
    const audioTranslation = document.getElementById('audioTranslation')?.checked || false;
    const coverGeneration = document.getElementById('coverGeneration')?.checked || false;
    const metadataGeneration = document.getElementById('metadataGeneration')?.checked || false;
    const youtubeUpload = document.getElementById('youtubeUpload')?.checked || false;

    // Verifica che almeno una funzionalità sia selezionata
    if (!logoOverlay && !callToAction && !videoTranscription && !audioTranslation &&
        !coverGeneration && !metadataGeneration && !youtubeUpload) {
        showAlert('Attenzione', 'Seleziona almeno una funzionalità da eseguire', 'warning');
        return;
    }

    // Validazioni specifiche
    if (logoOverlay && !logoFileId) {
        showAlert('Errore', 'Funzionalità Logo attiva ma nessun logo caricato', 'error');
        return;
    }

    if (callToAction && !foregroundFileId) {
        showAlert('Errore', 'Funzionalità CTA attiva ma nessun video CTA caricato', 'error');
        return;
    }

    // Prepara FormData
    const formData = new FormData();
    formData.append('video_file_id', backgroundFileId);
    formData.append('logo_overlay', logoOverlay);
    formData.append('call_to_action', callToAction);
    formData.append('video_transcription', videoTranscription);
    formData.append('audio_translation', audioTranslation);
    formData.append('cover_generation', coverGeneration);
    formData.append('metadata_generation', metadataGeneration);
    formData.append('youtube_upload', youtubeUpload);

    // Aggiungi file opzionali
    if (callToAction && foregroundFileId) {
        formData.append('cta_file_id', foregroundFileId);

        // Posizione e scala CTA
        const ctaPosition = document.getElementById('ctaPosition')?.value || 'center';
        const ctaSize = parseInt(document.getElementById('ctaSize')?.value || 20) / 100;
        const ctaCoords = getPositionCoordinates(ctaPosition, 1920, 1080, false);

        formData.append('cta_x_pos', ctaCoords.x);
        formData.append('cta_y_pos', ctaCoords.y);
        formData.append('cta_scale', ctaSize);
    }

    if (logoOverlay && logoFileId) {
        formData.append('logo_file_id', logoFileId);

        // Posizione e scala Logo
        const logoPosition = document.getElementById('logoPosition')?.value || 'top-left';
        const logoSize = parseInt(document.getElementById('logoSize')?.value || 10) / 100;
        const logoCoords = getPositionCoordinates(logoPosition, 1920, 1080, true);

        formData.append('logo_x_pos', logoCoords.x);
        formData.append('logo_y_pos', logoCoords.y);
        formData.append('logo_scale', logoSize);
    }

    if (audioTranslation) {
        const targetLang = document.getElementById('targetLanguage')?.value || 'en';
        formData.append('target_language', targetLang);
    }

    try {
        // Mostra modal di processing
        showProcessingModal();
        updateProcessingStatus('Avvio workflow automatico...', 0);

        // Chiamata API
        const response = await fetch('/api/workflow-auto', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Errore durante l\'avvio del workflow');
        }

        const result = await response.json();
        const jobId = result.job_id;

        console.log('Workflow avviato, job_id:', jobId);

        // Polling dello stato
        pollJobStatus(jobId);

    } catch (error) {
        console.error('Errore workflow:', error);
        hideProcessingModal();
        showAlert('Errore', error.message, 'error');
    }
}

// Modifica il pulsante "Elabora Video" per usare il workflow automatico
// quando si è nella tab "Workflow Automatico"
const originalProcessVideo = processVideo;
processVideo = function() {
    // Controlla se siamo nella tab upload (workflow automatico)
    const uploadTab = document.getElementById('uploadTab');
    if (uploadTab && uploadTab.classList.contains('active')) {
        // Usa il workflow automatico
        processVideoWorkflow();
    } else {
        // Usa la funzione originale
        originalProcessVideo();
    }
};

// ========================================
// SALVATAGGIO AUTOMATICO SWITCH
// ========================================

// Lista degli ID degli switch da salvare
const workflowSwitches = [
    'logoOverlay',
    'callToAction',
    'videoTranscription',
    'audioTranslation',
    'coverGeneration',
    'metadataGeneration',
    'youtubeUpload'
];

// Funzione per salvare lo stato degli switch
function saveWorkflowSwitches() {
    const settings = {};
    workflowSwitches.forEach(switchId => {
        const element = document.getElementById(switchId);
        if (element) {
            settings[switchId] = element.checked;
        }
    });
    localStorage.setItem('workflowSwitches', JSON.stringify(settings));
    console.log('Switch workflow salvati:', settings);
}

// Funzione per caricare lo stato degli switch
function loadWorkflowSwitches() {
    const saved = localStorage.getItem('workflowSwitches');
    if (saved) {
        try {
            const settings = JSON.parse(saved);
            workflowSwitches.forEach(switchId => {
                const element = document.getElementById(switchId);
                if (element && settings.hasOwnProperty(switchId)) {
                    element.checked = settings[switchId];
                }
            });
            console.log('Switch workflow caricati:', settings);
        } catch (e) {
            console.error('Errore caricamento switch:', e);
        }
    }
}

// Funzione per ripristinare i default (tutti disattivati)
function resetWorkflowSwitches() {
    workflowSwitches.forEach(switchId => {
        const element = document.getElementById(switchId);
        if (element) {
            element.checked = false;
        }
    });
    saveWorkflowSwitches();
    showAlert('Reset', 'Impostazioni workflow ripristinate ai valori predefiniti', 'success');
}

// Aggiungi event listener a tutti gli switch per il salvataggio automatico
function initWorkflowSwitches() {
    // Carica lo stato salvato
    loadWorkflowSwitches();

    // Aggiungi listener per salvataggio automatico
    workflowSwitches.forEach(switchId => {
        const element = document.getElementById(switchId);
        if (element) {
            element.addEventListener('change', function() {
                saveWorkflowSwitches();
                console.log(`Switch ${switchId} cambiato: ${this.checked}`);
            });
        }
    });

    console.log('Switch workflow inizializzati');
}

// Inizializza quando il DOM è pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWorkflowSwitches);
} else {
    initWorkflowSwitches();
}


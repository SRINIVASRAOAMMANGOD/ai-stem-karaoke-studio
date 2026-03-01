/**
 * AI STEM Karaoke Studio - Main JavaScript
 */

// ============================================
// Navigation & Smooth Scrolling
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    initNavigation();
    initSmoothScroll();
    initSectionVisibility();
    initUploadFeatures();
    initTabSwitching();
    initMobileMenu();
});

/**
 * Initialize navigation active states
 */
function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('section[id]');
    
    // Smooth scroll and active state on click
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            // Only handle hash links
            if (href && href.startsWith('#')) {
                e.preventDefault();
                const targetId = href.substring(1);
                const targetSection = document.getElementById(targetId);
                
                if (targetSection) {
                    // Smooth scroll to section
                    targetSection.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'start' 
                    });
                    
                    // Update active state
                    navLinks.forEach(l => l.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Close mobile menu if open
                    const navMenu = document.getElementById('nav-menu');
                    if (navMenu) {
                        navMenu.classList.remove('active');
                    }
                }
            }
        });
    });
    
    // Update active state on scroll
    window.addEventListener('scroll', () => {
        let current = '';
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            
            if (pageYOffset >= sectionTop - 200) {
                current = section.getAttribute('id');
            }
        });
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            const href = link.getAttribute('href');
            if (href && href === `#${current}`) {
                link.classList.add('active');
            }
        });
    });
}

/**
 * Initialize smooth scrolling for all anchor links
 */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            
            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'start' 
                });
            }
        });
    });
}

/**
 * Initialize section visibility based on content
 */
function initSectionVisibility() {
    // Initially hide sections that require processing
    const sectionsToHide = [
        'waveform-section',
        'stem-controls-section',
        'master-controls-section',
        'karaoke-controls-section',
        'recording-controls-section',
        'comparison-section',
        'ai-score-section'
    ];
    
    sectionsToHide.forEach(sectionId => {
        const section = document.getElementById(sectionId);
        if (section && !section.style.display) {
            section.style.display = 'none';
        }
    });
}

/**
 * Initialize mobile menu toggle
 */
function initMobileMenu() {
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
            navToggle.classList.toggle('active');
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!navToggle.contains(e.target) && !navMenu.contains(e.target)) {
                navMenu.classList.remove('active');
                navToggle.classList.remove('active');
            }
        });
    }
}

// ============================================
// Upload Features
// ============================================

function initUploadFeatures() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const uploadForm = document.getElementById('upload-form');
    const selectedFileDiv = document.getElementById('selected-file');
    
    if (!uploadArea || !fileInput) return;
    
    // Click to upload — skip if the click originated from the label or file input
    // (the <label for="file-input"> already natively opens the file picker)
    uploadArea.addEventListener('click', (e) => {
        if (e.target.closest('label') || e.target === fileInput) return;
        fileInput.click();
    });
    
    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            displaySelectedFile(files[0]);
        }
    });
    
    // File selection
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            displaySelectedFile(e.target.files[0]);
        }
    });
    
    // Remove file
    const removeBtn = document.querySelector('.btn-remove');
    if (removeBtn) {
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.value = '';
            if (selectedFileDiv) {
                selectedFileDiv.style.display = 'none';
            }
            uploadArea.style.display = 'block';
        });
    }
    
    // Form submission
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFileUpload);
    }
    
    // URL form
    const urlForm = document.getElementById('url-form');
    if (urlForm) {
        urlForm.addEventListener('submit', handleUrlUpload);
    }
}

function displaySelectedFile(file) {
    const uploadArea = document.getElementById('upload-area');
    const selectedFileDiv = document.getElementById('selected-file');
    const fileName = selectedFileDiv?.querySelector('.file-name');
    
    if (fileName) {
        fileName.textContent = file.name;
    }
    
    if (uploadArea) {
        uploadArea.style.display = 'none';
    }
    
    if (selectedFileDiv) {
        selectedFileDiv.style.display = 'flex';
    }
}

async function handleFileUpload(e) {
    e.preventDefault();

    const fileInput = document.getElementById('file-input');
    if (!fileInput || !fileInput.files.length) {
        alert('Please select a file');
        return;
    }

    const file = fileInput.files[0];
    console.log('File selected:', file.name, 'Size:', file.size);

    const formData = new FormData();
    formData.append('file', file);

    try {
        showProgressSection();
        updateProgress(10, 'Uploading file...');

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 min timeout

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData,
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Server error: ${response.status} - ${errorText}`);
        }

        updateProgress(50, 'Processing stems with Demucs AI... This may take 1-3 minutes.');

        const data = await response.json();
        console.log('Response data:', data);

        if (data.success) {
            updateProgress(100, 'Complete! Redirecting to mixer...');
            setTimeout(() => {
                window.location.href = data.redirect_url;
            }, 1500);
        } else {
            throw new Error(data.error || 'Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error.name, error.message);
        if (error.name === 'AbortError') {
            alert('Upload timed out after 5 minutes. Try a smaller file.');
        } else {
            alert('Upload failed: ' + error.message);
        }
        hideProgressSection();
    }
}

async function handleUrlUpload(e) {
    e.preventDefault();
    
    const urlInput = document.getElementById('url-input');
    const url = urlInput?.value.trim();
    
    if (!url) {
        showAlert('Please enter a URL', 'error');
        return;
    }
    
    try {
        showProgressSection();
        updateProgress(0, 'Downloading from URL...');
        
        const response = await fetch('/upload-url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url })
        });
        
        const data = await response.json();
        
        if (data.success) {
            updateProgress(100, 'Complete!');
            showAlert('Download and separation completed!', 'success');
            showResultSections(data);
        } else {
            throw new Error(data.error || 'URL processing failed');
        }
    } catch (error) {
        console.error('URL upload error:', error);
        showAlert(error.message, 'error');
        hideProgressSection();
    }
}

// ============================================
// Progress Management
// ============================================

function showProgressSection() {
    const progressSection = document.getElementById('progress-section');
    if (progressSection) {
        progressSection.style.display = 'block';
        progressSection.scrollIntoView({ behavior: 'smooth' });
    }
}

function hideProgressSection() {
    const progressSection = document.getElementById('progress-section');
    if (progressSection) {
        progressSection.style.display = 'none';
    }
}

function updateProgress(percentage, message) {
    const progressFill = document.getElementById('progress-fill');
    const progressPercentage = document.getElementById('progress-percentage');
    const progressMessage = document.getElementById('progress-message');
    
    if (progressFill) {
        progressFill.style.width = percentage + '%';
    }
    
    if (progressPercentage) {
        progressPercentage.textContent = percentage + '%';
    }
    
    if (progressMessage) {
        progressMessage.textContent = message;
    }
    
    // Update steps
    const steps = document.querySelectorAll('.step');
    steps.forEach((step, index) => {
        const stepPercentage = (index + 1) * 25;
        if (percentage >= stepPercentage) {
            step.classList.add('complete');
        }
        if (percentage >= stepPercentage - 25 && percentage < stepPercentage) {
            step.classList.add('active');
        }
    });
}

// ============================================
// Show Result Sections
// ============================================

function showResultSections(data) {
    const sections = [
        'waveform-section',
        'stem-controls-section',
        'master-controls-section',
        'karaoke-controls-section',
        'recording-controls-section'
    ];
    
    sections.forEach(sectionId => {
        const section = document.getElementById(sectionId);
        if (section) {
            section.style.display = 'block';
        }
    });
    
    // Scroll to waveform
    const waveformSection = document.getElementById('waveform-section');
    if (waveformSection) {
        setTimeout(() => {
            waveformSection.scrollIntoView({ behavior: 'smooth' });
        }, 500);
    }
    
    hideProgressSection();
}

// ============================================
// Tab Switching
// ============================================

function initTabSwitching() {
    // Upload tabs
    const uploadTabs = document.querySelectorAll('.upload-section .tab-btn');
    uploadTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.getAttribute('data-tab');
            switchTab(tab.closest('.upload-section'), tabName);
        });
    });
    
    // Settings tabs
    const settingsTabs = document.querySelectorAll('.settings-tab');
    settingsTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.getAttribute('data-tab');
            
            // Update active tab
            settingsTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // Show corresponding panel
            const panels = document.querySelectorAll('.settings-panel');
            panels.forEach(panel => {
                panel.classList.remove('active');
                if (panel.id === `${tabName}-settings`) {
                    panel.classList.add('active');
                }
            });
        });
    });
}

function switchTab(container, tabName) {
    // Update tab buttons
    const tabs = container.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.classList.remove('active');
        if (tab.getAttribute('data-tab') === tabName) {
            tab.classList.add('active');
        }
    });
    
    // Update tab content
    const contents = container.querySelectorAll('.tab-content');
    contents.forEach(content => {
        content.classList.remove('active');
        if (content.id === `${tabName}-tab`) {
            content.classList.add('active');
        }
    });
}

// ============================================
// Alert Messages
// ============================================

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="close-btn">&times;</button>
    `;
    
    let flashContainer = document.querySelector('.flash-messages');
    if (!flashContainer) {
        flashContainer = document.createElement('div');
        flashContainer.className = 'flash-messages';
        document.body.appendChild(flashContainer);
    }
    
    flashContainer.appendChild(alertDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
    
    // Remove on click
    const closeBtn = alertDiv.querySelector('.close-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            alertDiv.remove();
        });
    }
}

// ============================================
// Karaoke Studio Initialization
// ============================================

function initializeKaraokeStudio() {
    console.log('AI STEM Karaoke Studio initialized');
    
    // Initialize all features
    initStemControls();
    initMasterControls();
    initKaraokeMode();
    initRecordingControls();
    initProjectsList();
    initSettings();
}

// ============================================
// Stem Controls
// ============================================

function initStemControls() {
    // Volume sliders
    document.querySelectorAll('.volume-slider').forEach(slider => {
        slider.addEventListener('input', (e) => {
            const value = e.target.value;
            const valueDisplay = e.target.closest('.control-group')?.querySelector('.control-value');
            if (valueDisplay) {
                valueDisplay.textContent = value + '%';
            }
        });
    });
    
    // Pan sliders
    document.querySelectorAll('.pan-slider').forEach(slider => {
        slider.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            const valueDisplay = e.target.closest('.control-group')?.querySelector('.control-value');
            if (valueDisplay) {
                if (value === 0) {
                    valueDisplay.textContent = 'Center';
                } else if (value < 0) {
                    valueDisplay.textContent = 'L ' + Math.abs(value);
                } else {
                    valueDisplay.textContent = 'R ' + value;
                }
            }
        });
    });
    
    // Solo/Mute buttons
    document.querySelectorAll('.solo-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            this.classList.toggle('active');
        });
    });
    
    document.querySelectorAll('.mute-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            this.classList.toggle('active');
        });
    });
}

// ============================================
// Master Controls
// ============================================

function initMasterControls() {
    // Master volume
    const masterVolume = document.getElementById('master-volume');
    if (masterVolume) {
        masterVolume.addEventListener('input', (e) => {
            const value = e.target.value;
            const valueDisplay = document.querySelector('.volume-value');
            if (valueDisplay) {
                valueDisplay.textContent = value + '%';
            }
        });
    }
    
    // Tempo controls
    const tempoSlider = document.getElementById('tempo-slider');
    const tempoValue = document.getElementById('tempo-value');
    if (tempoSlider && tempoValue) {
        tempoSlider.addEventListener('input', (e) => {
            tempoValue.textContent = e.target.value;
        });
    }
    
    // Pitch controls
    const pitchSlider = document.getElementById('pitch-slider');
    const pitchValue = document.getElementById('pitch-value');
    if (pitchSlider && pitchValue) {
        pitchSlider.addEventListener('input', (e) => {
            pitchValue.textContent = e.target.value;
        });
    }
}

// ============================================
// Karaoke Mode
// ============================================

function initKaraokeMode() {
    const karaokeToggle = document.getElementById('karaoke-mode-toggle');
    const karaokeContent = document.getElementById('karaoke-content');
    
    if (karaokeToggle && karaokeContent) {
        karaokeToggle.addEventListener('change', (e) => {
            karaokeContent.style.display = e.target.checked ? 'block' : 'none';
        });
    }
}

// ============================================
// Recording Controls
// ============================================

function initRecordingControls() {
    const recordBtn = document.getElementById('record-btn');
    const stopRecBtn = document.getElementById('stop-rec-btn');
    
    if (recordBtn) {
        recordBtn.addEventListener('click', startRecording);
    }
    
    if (stopRecBtn) {
        stopRecBtn.addEventListener('click', stopRecording);
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log('Recording started');
        showAlert('Recording started', 'success');
        
        // Update UI
        document.getElementById('record-btn').style.display = 'none';
        document.getElementById('stop-rec-btn').style.display = 'inline-flex';
        
        const statusIndicator = document.getElementById('recording-indicator');
        if (statusIndicator) {
            statusIndicator.classList.add('recording');
            statusIndicator.querySelector('.status-text').textContent = 'Recording...';
        }
    } catch (error) {
        console.error('Microphone access error:', error);
        showAlert('Could not access microphone', 'error');
    }
}

function stopRecording() {
    console.log('Recording stopped');
    showAlert('Recording stopped', 'info');
    
    // Update UI
    document.getElementById('record-btn').style.display = 'inline-flex';
    document.getElementById('stop-rec-btn').style.display = 'none';
    document.getElementById('play-rec-btn').style.display = 'inline-flex';
    document.getElementById('save-rec-btn').style.display = 'inline-flex';
    document.getElementById('discard-rec-btn').style.display = 'inline-flex';
    
    const statusIndicator = document.getElementById('recording-indicator');
    if (statusIndicator) {
        statusIndicator.classList.remove('recording');
        statusIndicator.querySelector('.status-text').textContent = 'Recording Complete';
    }
}

// ============================================
// Projects List
// ============================================

function initProjectsList() {
    // Load projects
    loadProjects();
    
    // Search functionality
    const searchInput = document.getElementById('project-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            filterProjects(e.target.value);
        });
    }
    
    // Favorite buttons
    document.querySelectorAll('.favorite-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            this.classList.toggle('active');
        });
    });
}

async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        const data = await response.json();
        
        if (data.success && data.projects) {
            displayProjects(data.projects);
        }
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

function displayProjects(projects) {
    const projectsGrid = document.getElementById('projects-grid');
    const projectsEmpty = document.getElementById('projects-empty');
    
    if (!projectsGrid) return;
    
    if (projects.length === 0) {
        if (projectsEmpty) {
            projectsEmpty.style.display = 'block';
        }
        return;
    }
    
    if (projectsEmpty) {
        projectsEmpty.style.display = 'none';
    }
    
    // Display projects (implementation would go here)
}

function filterProjects(query) {
    const projectCards = document.querySelectorAll('.project-card');
    const lowerQuery = query.toLowerCase();
    
    projectCards.forEach(card => {
        const title = card.querySelector('.project-title')?.textContent.toLowerCase() || '';
        const artist = card.querySelector('.project-artist')?.textContent.toLowerCase() || '';
        
        if (title.includes(lowerQuery) || artist.includes(lowerQuery)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

// ============================================
// Settings
// ============================================

function initSettings() {
    // Load settings
    loadSettings();
    
    // Save settings button
    const saveBtn = document.getElementById('save-settings-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveSettings);
    }
}

async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const data = await response.json();
        
        if (data.success && data.settings) {
            applySettings(data.settings);
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

async function saveSettings() {
    const settings = {
        audio_output: document.getElementById('audio-output')?.value,
        audio_input: document.getElementById('audio-input')?.value,
        sample_rate: document.getElementById('sample-rate')?.value,
        buffer_size: document.getElementById('buffer-size')?.value,
        theme: document.getElementById('theme')?.value,
        default_model: document.getElementById('default-model')?.value
    };
    
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Settings saved successfully', 'success');
        } else {
            throw new Error('Failed to save settings');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showAlert('Failed to save settings', 'error');
    }
}

function applySettings(settings) {
    // Apply settings to form fields
    Object.keys(settings).forEach(key => {
        const element = document.getElementById(key.replace(/_/g, '-'));
        if (element) {
            element.value = settings[key];
        }
    });
}

// ============================================
// Utility Functions
// ============================================

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

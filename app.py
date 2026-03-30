"""
================================================================================
KARAOKE STUDIO - FLASK BACKEND SERVER
================================================================================
Main application entry point. Handles all routes:
- Page routes: / /mixer /karaoke /projects /settings
- Upload routes: /upload /upload-url
- API routes: /api/settings /api/stems /api/projects /api/save-recording etc.

Key Features:
1. FILE UPLOAD: Accept MP3/WAV → Store in projects/
2. DEMUCS SEPARATION: Run AI model to split audio into stems (vocals/drums/bass/other)
3. PROJECT MANAGEMENT: Track projects with metadata.json
4. KARAOKE RECORDING: Accept user vocal recording → Mix with stems
5. SETTINGS PERSISTENCE: Save user preferences to settings.json
6. FILE SERVING: Serve audio files to browser via /files/ endpoint

Architecture:
- Routes are organized: PAGE ROUTES (HTML) → API ROUTES (JSON)
- Each route loads project or settings from disk
- Helper functions at bottom: load_project, save_project_metadata, etc.
================================================================================
"""

from flask import Flask, render_template, request, send_from_directory, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
import json
import re
import shutil
import subprocess
import threading
from datetime import datetime
from services.demucs_service import separate_audio, _load_model
from config import get_config

# ── Initialize Flask App ──────────────────────────────────────────────────
app = Flask(__name__)

# Load configuration (environment-specific: development/production/testing)
config_name = os.environ.get('FLASK_ENV', 'development')
config = get_config(config_name)
app.config.from_object(config)

# ── CORS Headers ──────────────────────────────────────────────────────────
# Allow browser requests from any origin (important for local testing)
@app.after_request
def add_cors_headers(response):
    """Add CORS headers to enable browser requests"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# ── Folder Configuration ──────────────────────────────────────────────────
# These constants define where files are stored on disk
UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']  # uploads/ for temporary files
PROJECTS_FOLDER = 'projects'                  # projects/ for all karaoke projects
ALLOWED_EXTENSIONS = app.config['ALLOWED_EXTENSIONS']  # mp3, wav, flac, m4a, aac, ogg
SETTINGS_FILE = 'settings.json'               # User settings file (singleton)

# ── Default Settings ─────────────────────────────────────────────────────
# These are the default user settings. Merged with saved settings from disk.
# Users can modify these in /settings page → changes persist to settings.json
DEFAULT_SETTINGS = {
    # Audio I/O Settings
    'audio_output':    'default',       # Output device (speakers)
    'audio_input':     'default',       # Input device (microphone)
    'sample_rate':     '48000',         # Audio sample rate (Hz)
    'buffer_size':     '512',           # Audio buffer size (samples)
    'normalize_audio': True,            # Normalize after processing
    
    # Processing Settings
    'default_model':   'htdemucs',      # Which Demucs model to use
    'processing_quality': 'balanced',   # balanced/fast/high_quality
    'cpu_threads':     4,               # CPU threads for processing
    'use_gpu':         True,            # Use GPU acceleration if available
    'auto_cleanup':    True,            # Auto-delete old projects
    
    # UI Settings
    'theme':           'dark',          # dark or light theme
    'accent_color':    '#0f766e',       # App accent color (FIXED - don't change)
    'waveform_colors': 'default',       # Waveform visualization colors
    'show_animations': True,            # Enable visual animations
    'compact_mode':    False,           # Compact UI layout
    
    # Storage Settings
    'max_storage':     '1000',          # Max storage in MB
    'auto_delete_old': False,           # Auto-delete oldest projects when full
    'export_format':   'wav',           # Export audio format
    
    # Advanced Settings
    'enable_debug':    False,           # Debug mode (verbose logging)
    'api_endpoint':    'http://localhost:5000',  # API server address
}


# ── Settings Management ───────────────────────────────────────────────────
def load_settings():
    """Load user settings from disk, merging with defaults."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                saved = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(saved)
            return merged
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings_to_disk(data):
    """Save user settings to settings.json file."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


# ── Startup Initialization ────────────────────────────────────────────────
# Ensure required folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROJECTS_FOLDER, exist_ok=True)


def _prewarm_model():
    """
    Pre-load the default Demucs model in background so it's ready for first upload.
    This prevents the first upload from stalling while the model loads from disk.
    """
    try:
        default_model = load_settings().get('default_model', 'htdemucs')
        print(f"[Startup] Pre-warming Demucs model '{default_model}' in background…")
        _load_model(default_model)
        print(f"[Startup] Model '{default_model}' ready — first upload will be instant.")
    except Exception as e:
        print(f"[Startup] Model pre-warm skipped: {e}")


# Run model pre-warming in background thread so it doesn't block server startup
threading.Thread(target=_prewarm_model, daemon=True).start()


def allowed_file(filename):
    """Check if file extension is in ALLOWED_EXTENSIONS."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================
# PAGE ROUTES - Serve HTML Templates
# ============================================

@app.route('/')
def index():
    """Home page - allows user to upload audio file"""
    return render_template('home.html')


@app.route('/mixer/<project_id>')
def mixer(project_id):
    """Stem mixer page - adjust individual stem volumes and effects"""
    project = load_project(project_id)
    if not project:
        return redirect(url_for('index'))
    return render_template('mixer.html', project=project)


@app.route('/karaoke/<project_id>')
def karaoke(project_id):
    """Karaoke recording page - record vocal and play backing tracks"""
    project = load_project(project_id)
    if not project:
        return redirect(url_for('index'))
    return render_template('karaoke.html', project=project)


@app.route('/compare/<project_id>')
def compare(project_id):
    """Comparison page - compare original vocals with user recording"""
    project = load_project(project_id)
    if not project:
        return redirect(url_for('index'))
    vocal_stem = find_vocal_stem(project)
    has_vocals = vocal_stem is not None
    recording_path = os.path.join(PROJECTS_FOLDER, project_id, 'recording.wav')
    has_recording = project.get('has_recording', False) and os.path.exists(recording_path)
    return render_template('compare.html', project=project,
                           has_vocals=has_vocals, has_recording=has_recording)


@app.route('/projects')
def projects():
    """Projects list page - browse all karaoke projects"""
    all_projects = get_all_projects()
    return render_template('projects.html', projects=all_projects)


@app.route('/settings')
def settings():
    """Settings page - configure user preferences and audio settings"""
    return render_template('settings.html')


@app.route('/debug-stems')
def debug_stems():
    """Debug page - test stem loading (development only)"""
    return render_template('debug_stems.html')


# ============================================
# UPLOAD ROUTES - Handle Audio File Upload
# ============================================

@app.route('/upload', methods=['POST'])
def upload():
    """
    Handle audio file upload and run AI stem separation.
    
    PROCESS:
    1. Validate file format (mp3, wav, flac, m4a, etc)
    2. Create project folder with unique ID (timestamp)
    3. Save uploaded file
    4. Run Demucs model to separate into stems (vocals/drums/bass/other)
    5. Save project metadata (JSON)
    6. Return project_id to frontend
    
    TIME: Takes 1-3 minutes depending on audio length
    """
    try:
        # STEP 1: Validate file in request
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        audio = request.files['file']
        
        if audio.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(audio.filename):
            return jsonify({'success': False, 'error': 'Invalid file format'}), 400

        # STEP 2: Create project folder
        project_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        project_folder = os.path.join(PROJECTS_FOLDER, project_id)
        os.makedirs(project_folder, exist_ok=True)
        
        # STEP 3: Save uploaded file
        filename = secure_filename(audio.filename)
        original_name = os.path.splitext(filename)[0]
        upload_path = os.path.join(project_folder, 'original_' + filename)
        audio.save(upload_path)

        # STEP 4: Run Demucs separation (AI model)
        saved_model = request.form.get('model') or load_settings().get('default_model', 'htdemucs')
        output_folder = os.path.join(project_folder, 'stems')
        print(f"[Upload] Starting Demucs separation for project {project_id}")
        
        stems_path = separate_audio(upload_path, model=saved_model, output_folder=output_folder)

        if not stems_path:
            return jsonify({'success': False, 'error': 'Stem separation failed'}), 500

        # STEP 5: Save project metadata
        project_data = {
            'id': project_id,
            'name': original_name,
            'original_file': upload_path,
            'stems_folder': stems_path,
            'model': saved_model,
            'created_at': datetime.now().isoformat(),
            'has_recording': False,
            'score': None
        }
        save_project_metadata(project_id, project_data)

        # STEP 6: Return success with redirect to mixer
        return jsonify({
            'success': True,
            'project_id': project_id,
            'redirect_url': url_for('mixer', project_id=project_id)
        })

    except Exception as e:
        print(f"[Upload] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/upload-url', methods=['POST'])
def upload_url():
    """
    Download audio from URL (YouTube / direct link) then separate stems.
    Same process as /upload but downloads first instead of accepting file.
    """
    from services.url_service import download_from_url

    try:
        body = request.get_json(silent=True) or {}
        url  = (body.get('url') or '').strip()
        model = body.get('model') or load_settings().get('default_model', 'htdemucs')

        if not url:
            return jsonify({'success': False, 'error': 'No URL provided'}), 400

        # Create project folder
        project_id     = datetime.now().strftime('%Y%m%d_%H%M%S')
        project_folder = os.path.join(PROJECTS_FOLDER, project_id)
        os.makedirs(project_folder, exist_ok=True)

        # Download audio from URL
        download_folder = os.path.join(project_folder, 'downloads')
        os.makedirs(download_folder, exist_ok=True)
        audio_path, video_title = download_from_url(url, download_folder)

        if not audio_path or not os.path.exists(audio_path):
            return jsonify({'success': False, 'error': 'Failed to download audio from URL'}), 400

        # Extract name from title or filename
        if video_title:
            original_name = video_title
        else:
            original_name = os.path.splitext(os.path.basename(audio_path))[0]
            original_name = re.sub(r'^\d{8}_\d{6}_', '', original_name)

        # Run Demucs separation
        output_folder = os.path.join(project_folder, 'stems')
        stems_path = separate_audio(audio_path, model=model, output_folder=output_folder)

        if not stems_path:
            return jsonify({'success': False, 'error': 'Audio separation failed'}), 500

        # Save metadata
        project_data = {
            'id':            project_id,
            'name':          original_name,
            'original_file': audio_path,
            'stems_folder':  stems_path,
            'model':         model,
            'created_at':    datetime.now().isoformat(),
            'has_recording': False,
            'score':         None,
            'source_url':    url,
        }
        save_project_metadata(project_id, project_data)

        return jsonify({
            'success':      True,
            'project_id':   project_id,
            'redirect_url': url_for('mixer', project_id=project_id)
        })

    except Exception as e:
        print(f"[Upload URL] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# API ROUTES - Return JSON Data
# ============================================
# These routes return JSON responses for frontend JavaScript to consume.
# Frontend loads HTML, then uses JavaScript to call these API endpoints.

@app.route('/api/projects', methods=['GET'])
def api_get_projects():
    """Get list of all karaoke projects"""
    try:
        projects = get_all_projects()
        return jsonify({'success': True, 'projects': projects})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<project_id>', methods=['GET'])
def api_get_project(project_id):
    """Get specific project details by ID"""
    try:
        project = load_project(project_id)
        if project:
            return jsonify({'success': True, 'project': project})
        else:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<project_id>', methods=['DELETE'])
def api_delete_project(project_id):
    """Delete a project and all its files"""
    try:
        project_folder = os.path.join(PROJECTS_FOLDER, project_id)
        if os.path.exists(project_folder):
            shutil.rmtree(project_folder)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/save-recording/<project_id>', methods=['POST'])
def save_recording(project_id):
    """
    Save user's vocal recording from karaoke page.
    
    PROCESS:
    1. Accept audio blob from browser (webm/wav format)
    2. Convert to WAV format using ffmpeg (mono, 44.1kHz, 16-bit)
    3. Save to projects/{project_id}/recording.wav
    4. Fallback to raw upload if conversion fails (doesn't lose data)
    5. Update project metadata with has_recording=true
    """
    try:
        if 'recording' not in request.files:
            return jsonify({'success': False, 'error': 'No recording uploaded'}), 400
        
        recording = request.files['recording']
        
        if recording.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        project_folder = os.path.join(PROJECTS_FOLDER, project_id)
        if not os.path.exists(project_folder):
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Save upload, convert to WAV, clean up temp file
        original_name = secure_filename(recording.filename) or 'recording.webm'
        _, ext = os.path.splitext(original_name)
        ext = ext.lower() if ext else '.webm'
        uploaded_path = os.path.join(project_folder, f'recording_upload{ext}')
        recording_path = os.path.join(project_folder, 'recording.wav')

        recording.save(uploaded_path)

        # Convert to standard WAV using ffmpeg
        cmd = [
            'ffmpeg', '-y',
            '-i', uploaded_path,
            '-ac', '1',                # mono
            '-ar', '44100',            # 44.1kHz sample rate
            '-c:a', 'pcm_s16le',       # 16-bit PCM
            recording_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            # Fallback: if ffmpeg fails, keep raw upload
            shutil.copy2(uploaded_path, recording_path)

        try:
            if os.path.exists(uploaded_path):
                os.remove(uploaded_path)
        except OSError:
            pass
        
        # Update project metadata
        project = load_project(project_id)
        if project:
            project['has_recording'] = True
            project['recording_file'] = recording_path
            save_project_metadata(project_id, project)
        
        return jsonify({
            'success': True,
            'recording_path': recording_path
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """Get all user settings"""
    return jsonify({'success': True, 'settings': load_settings()})


@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    """Save user settings. Only accent_color is locked (for brand consistency)."""
    try:
        data = request.get_json(silent=True) or {}
        current = load_settings()
        # Only update settings that are in DEFAULT_SETTINGS (ignore unknown keys)
        current.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
        # Lock accent color to prevent user changes
        current['accent_color'] = DEFAULT_SETTINGS['accent_color']
        save_settings_to_disk(current)
        return jsonify({'success': True, 'settings': current})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/storage-info', methods=['GET'])
def api_storage_info():
    """Get disk usage stats: total bytes used, MB used, project count, free space"""
    try:
        import shutil
        total_bytes = 0
        project_count = 0
        
        # Calculate total size of all projects
        for root, dirs, files in os.walk(PROJECTS_FOLDER):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total_bytes += os.path.getsize(fp)
                except OSError:
                    pass
        
        # Count projects
        for pid in os.listdir(PROJECTS_FOLDER):
            if os.path.isdir(os.path.join(PROJECTS_FOLDER, pid)):
                project_count += 1
        
        # Get disk free space
        disk = shutil.disk_usage('.')
        
        return jsonify({
            'success': True,
            'used_bytes': total_bytes,
            'used_mb': round(total_bytes / 1024 / 1024, 1),
            'project_count': project_count,
            'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 1),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/clear-cache', methods=['POST'])
def api_clear_cache():
    """Clear uploads/ folder to free disk space"""
    try:
        removed = 0
        # Clear uploads/ folder
        for item in os.listdir(UPLOAD_FOLDER):
            p = os.path.join(UPLOAD_FOLDER, item)
            try:
                os.remove(p)
                removed += 1
            except Exception:
                pass
        return jsonify({'success': True, 'removed': removed})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/project-requirements/<project_id>', methods=['GET'])
def project_requirements(project_id):
    """Check which stems/recordings are available for a project"""
    try:
        project = load_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        vocal_stem = find_vocal_stem(project)
        recording_path = os.path.join(PROJECTS_FOLDER, project_id, 'recording.wav')
        has_recording = os.path.exists(recording_path)

        vocal_url = None
        if vocal_stem:
            vocal_url = '/files/' + vocal_stem.replace('\\', '/')

        recording_url = None
        if has_recording:
            recording_url = f'/files/projects/{project_id}/recording.wav'

        return jsonify({
            'success': True,
            'has_vocals': vocal_stem is not None,
            'has_recording': has_recording,
            'vocal_url': vocal_url,
            'recording_url': recording_url,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stems/<project_id>', methods=['GET'])
def api_get_stems(project_id):
    """
    Return playable URLs for all stems (audio tracks) of a project.
    
    RESPONSE:
    {
        "stems": {
            "vocals": "/files/projects/..../vocals.wav",
            "drums": "/files/projects/..../drums.wav",
            "bass": "/files/projects/..../bass.wav",
            "other": "/files/projects/..../other.wav"
        },
        "project": {...}
    }
    """
    try:
        project = load_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        stems_folder = project.get('stems_folder', '')
        if not stems_folder or not os.path.exists(stems_folder):
            return jsonify({'success': False, 'error': 'Stems not found'}), 404

        # Build URLs for each stem file
        stems = {}
        for stem_file in os.listdir(stems_folder):
            if stem_file.endswith('.wav'):
                name = os.path.splitext(stem_file)[0]   # vocals, drums, bass, other
                url_path = stems_folder.replace('\\', '/') + '/' + stem_file
                stems[name] = '/files/' + url_path

        return jsonify({'success': True, 'stems': stems, 'project': project})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export-karaoke/<project_id>', methods=['GET'])
@app.route('/api/download-karaoke/<project_id>', methods=['GET'])
def export_karaoke(project_id):
    """
    Create a downloadable karaoke mix.
    Combines: backing stems (drums, bass, other) + user vocal recording
    Result: karaoke_with_user_vocals.wav (ready to share or perform with)
    """
    try:
        project = load_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        recording_path = os.path.join(PROJECTS_FOLDER, project_id, 'recording.wav')
        if not os.path.exists(recording_path):
            return jsonify({'success': False, 'error': 'Recording not found. Save your recording first.'}), 400

        stems_folder = project.get('stems_folder', '')
        if not stems_folder or not os.path.exists(stems_folder):
            return jsonify({'success': False, 'error': 'Stems not found for this project.'}), 400

        # Find all non-vocal stems (backing track)
        backing_stems = []
        for f in os.listdir(stems_folder):
            if f.endswith('.wav') and not f.lower().startswith('vocals'):
                backing_stems.append(os.path.join(stems_folder, f))

        if not backing_stems:
            return jsonify({'success': False, 'error': 'No non-vocal stems available for karaoke backing.'}), 400

        exports_dir = os.path.join(PROJECTS_FOLDER, project_id, 'exports')
        os.makedirs(exports_dir, exist_ok=True)

        backing_mix_path = os.path.join(exports_dir, 'karaoke_backing.wav')
        final_mix_path   = os.path.join(exports_dir, 'karaoke_with_user_vocals.wav')

        # Mix backing stems (drums+bass+other) into one track
        if len(backing_stems) == 1:
            shutil.copy2(backing_stems[0], backing_mix_path)
        else:
            cmd = ['ffmpeg', '-y']
            for stem in backing_stems:
                cmd += ['-i', stem]
            cmd += [
                '-filter_complex', f'amix=inputs={len(backing_stems)}:normalize=0:duration=longest',
                '-c:a', 'pcm_s16le',
                backing_mix_path,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                return jsonify({'success': False, 'error': f'Failed to create backing mix'}), 500

        # Mix backing + user vocal into final karaoke file
        cmd2 = [
            'ffmpeg', '-y',
            '-i', backing_mix_path,
            '-i', recording_path,
            '-filter_complex', 'amix=inputs=2:normalize=0:duration=longest',
            '-c:a', 'pcm_s16le',
            final_mix_path,
        ]
        proc2 = subprocess.run(cmd2, capture_output=True, text=True)
        if proc2.returncode != 0:
            return jsonify({'success': False, 'error': f'Failed to create final karaoke mix'}), 500

        file_url = f'/files/projects/{project_id}/exports/karaoke_with_user_vocals.wav'
        return jsonify({'success': True, 'file_url': file_url, 'filename': 'karaoke_with_user_vocals.wav'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analyze-performance/<project_id>', methods=['POST'])
def analyze_performance(project_id):
    """
    Analyze vocal performance using AI.
    Compares: original vocals vs user recording
    Returns: accuracy score, pitch accuracy, timing accuracy, etc
    """
    try:
        project = load_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        # Require isolated vocal stem
        vocal_stem = find_vocal_stem(project)
        if not vocal_stem:
            return jsonify({
                'success': False,
                'error': 'Isolated vocal track not found'
            }), 400

        # Require user recording
        recording_path = os.path.join(PROJECTS_FOLDER, project_id, 'recording.wav')
        if not os.path.exists(recording_path):
            return jsonify({
                'success': False,
                'error': 'No vocal recording found'
            }), 400

        # Run AI analysis
        from services.scoring_service import analyze_vocal_accuracy
        analysis = analyze_vocal_accuracy(vocal_stem, recording_path)

        # Update project with score
        if project:
            project['score'] = analysis['overall_score']
            save_project_metadata(project_id, project)
        
        return jsonify({'success': True, 'analysis': analysis})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<project_id>/save-mix', methods=['POST'])
def save_mix(project_id):
    """Save mix settings (volumes, mutes, tempo, pitch) to project metadata"""
    try:
        project = load_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        data = request.get_json(silent=True) or {}
        project['mix_settings'] = {
            'volumes':      data.get('volumes', {}),
            'muted':        data.get('muted', {}),
            'soloed':       data.get('soloed', {}),
            'master_volume':data.get('master_volume', 0.8),
            'tempo':        data.get('tempo', 100),
            'pitch':        data.get('pitch', 0),
        }
        save_project_metadata(project_id, project)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/files/<path:filename>')
def serve_file(filename):
    """Serve audio/project files to browser. Files are: stems, recordings, exports"""
    # Secure path traversal: ensure requested file stays within project root
    safe = filename.replace('/', os.sep)
    base_dir = os.path.abspath(os.getcwd())
    abs_path = os.path.abspath(os.path.join(base_dir, safe))
    
    # Security check: path must be inside project directory
    if not abs_path.startswith(base_dir):
        return jsonify({'error': 'Forbidden'}), 403
    
    directory = os.path.dirname(abs_path)
    file_name  = os.path.basename(abs_path)
    return send_from_directory(directory, file_name)


# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error (>50MB)"""
    return jsonify({'success': False, 'error': 'File too large. Maximum size is 50MB'}), 413


@app.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors"""
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Endpoint not found'}), 404
    return render_template('home.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors"""
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    return render_template('home.html'), 500


# ============================================
# HELPER FUNCTIONS - Project & File Management
# ============================================

def find_vocal_stem(project):
    """Find the isolated vocals stem file for a project. Returns path or None."""
    stems_folder = project.get('stems_folder', '')
    if not stems_folder or not os.path.exists(stems_folder):
        return None
    for f in os.listdir(stems_folder):
        if f.startswith('vocals') and f.endswith('.wav'):
            return os.path.join(stems_folder, f)
    return None


def save_project_metadata(project_id, data):
    """Save project data to JSON file: projects/{project_id}/metadata.json"""
    project_folder = os.path.join(PROJECTS_FOLDER, project_id)
    metadata_file = os.path.join(project_folder, 'metadata.json')
    
    with open(metadata_file, 'w') as f:
        json.dump(data, f, indent=2)


def load_project(project_id):
    """Load project data from JSON file, return dict or None if not found"""
    project_folder = os.path.join(PROJECTS_FOLDER, project_id)
    metadata_file = os.path.join(project_folder, 'metadata.json')
    
    if not os.path.exists(metadata_file):
        return None
    
    try:
        with open(metadata_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[Error] Loading project {project_id}: {e}")
        return None


def get_all_projects():
    """Get all projects sorted by creation date (newest first)"""
    projects = []
    
    if not os.path.exists(PROJECTS_FOLDER):
        return projects
    
    # List all project directories
    for project_id in os.listdir(PROJECTS_FOLDER):
        project_folder = os.path.join(PROJECTS_FOLDER, project_id)
        if os.path.isdir(project_folder):
            project = load_project(project_id)
            if project:
                # Add stem list to project for UI display
                stems_folder = project.get('stems_folder', '')
                if stems_folder and os.path.exists(stems_folder):
                    project['stems'] = {
                        os.path.splitext(f)[0]: True
                        for f in os.listdir(stems_folder)
                        if f.endswith('.wav')
                    }
                else:
                    project.setdefault('stems', {})
                projects.append(project)
    
    # Sort by newest first
    projects.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return projects


# ============================================
# APP ENTRY POINT
# ============================================

if __name__ == '__main__':
    # Run the Flask development server
    # debug=True: reload on code changes, show errors
    # use_reloader=False: prevent double model loading
    # threaded=True: handle multiple requests simultaneously
    app.run(debug=True, use_reloader=False, threaded=True)

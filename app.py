from flask import Flask, render_template, request, send_from_directory, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
from services.demucs_service import separate_audio
from config import get_config

# Create Flask app
app = Flask(__name__)

# Load configuration (default to development)
config_name = os.environ.get('FLASK_ENV', 'development')
config = get_config(config_name)
app.config.from_object(config)

# Folders configuration
UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
PROJECTS_FOLDER = 'projects'
ALLOWED_EXTENSIONS = app.config['ALLOWED_EXTENSIONS']
SETTINGS_FILE = 'settings.json'

DEFAULT_SETTINGS = {
    'audio_output':    'default',
    'audio_input':     'default',
    'sample_rate':     '48000',
    'buffer_size':     '512',
    'normalize_audio': True,
    'default_model':   'htdemucs',
    'processing_quality': 'balanced',
    'cpu_threads':     4,
    'use_gpu':         True,
    'auto_cleanup':    True,
    'theme':           'dark',
    'accent_color':    '#6366f1',
    'waveform_colors': 'default',
    'show_animations': True,
    'compact_mode':    False,
    'max_storage':     '1000',
    'auto_delete_old': False,
    'export_format':   'wav',
    'enable_debug':    False,
    'api_endpoint':    'http://localhost:5000',
}

def load_settings():
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
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROJECTS_FOLDER, exist_ok=True)

# Pre-warm the default Demucs model in a background thread so the first
# upload doesn't stall waiting for disk-to-RAM model loading.
def _prewarm_model():
    try:
        default_model = load_settings().get('default_model', 'htdemucs')
        print(f"[Startup] Pre-warming Demucs model '{default_model}' in background…")
        from services.demucs_service import _load_model
        _load_model(default_model)
        print(f"[Startup] Model '{default_model}' ready — first upload will be instant.")
    except Exception as e:
        print(f"[Startup] Model pre-warm skipped: {e}")

import threading
threading.Thread(target=_prewarm_model, daemon=True).start()


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================
# PAGE ROUTES
# ============================================

@app.route('/')
def index():
    """Home page - Upload only"""
    return render_template('home.html')


@app.route('/mixer/<project_id>')
def mixer(project_id):
    """Stem mixer page"""
    project = load_project(project_id)
    if not project:
        return redirect(url_for('index'))
    return render_template('mixer.html', project=project)


@app.route('/karaoke/<project_id>')
def karaoke(project_id):
    """Karaoke recording page"""
    project = load_project(project_id)
    if not project:
        return redirect(url_for('index'))
    return render_template('karaoke.html', project=project)


@app.route('/compare/<project_id>')
def compare(project_id):
    """Comparison page"""
    project = load_project(project_id)
    if not project:
        return redirect(url_for('index'))
    return render_template('compare.html', project=project)


@app.route('/projects')
def projects():
    """Projects list page"""
    all_projects = get_all_projects()
    return render_template('projects.html', projects=all_projects)


@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')


# ============================================
# API ROUTES
# ============================================

@app.route('/upload', methods=['POST'])
def upload():
    """Handle file upload and stem separation"""
    print("\n" + "="*50)
    print("UPLOAD REQUEST RECEIVED")
    print("="*50)
    
    try:
        # Check if file is in request
        if 'file' not in request.files:
            print("ERROR: No file in request")
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        audio = request.files['file']
        print(f"File received: {audio.filename}")
        
        if audio.filename == '':
            print("ERROR: Empty filename")
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(audio.filename):
            print(f"ERROR: Invalid file format: {audio.filename}")
            return jsonify({'success': False, 'error': 'Invalid file format'}), 400

        # Create project
        project_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        project_folder = os.path.join(PROJECTS_FOLDER, project_id)
        os.makedirs(project_folder, exist_ok=True)
        print(f"Created project folder: {project_folder}")
        
        # Secure filename
        filename = secure_filename(audio.filename)
        original_name = os.path.splitext(filename)[0]
        
        # Save uploaded file
        upload_path = os.path.join(project_folder, 'original_' + filename)
        audio.save(upload_path)
        print(f"Saved file to: {upload_path}")
        print(f"File size: {os.path.getsize(upload_path)} bytes")

        # Run separation — use model from settings (falls back to htdemucs)
        saved_model = load_settings().get('default_model', 'htdemucs')
        output_folder = os.path.join(project_folder, 'stems')
        print(f"\nStarting Demucs separation...")
        print(f"Project ID: {project_id}")
        print(f"Input: {upload_path}")
        print(f"Output: {output_folder}")
        print("This may take 1-3 minutes depending on file length...")
        
        stems_path = separate_audio(upload_path, model=saved_model, output_folder=output_folder)

        if not stems_path:
            print(f"\nERROR: Separation failed for project {project_id}")
            return jsonify({'success': False, 'error': 'Error during audio separation. Check terminal for details.'}), 500

        print(f"\nSUCCESS: Separation complete!")
        print(f"Stems location: {stems_path}")
        
        # Save project metadata
        project_data = {
            'id': project_id,
            'name': original_name,
            'original_file': upload_path,
            'stems_folder': stems_path,
            'model': 'htdemucs',
            'created_at': datetime.now().isoformat(),
            'has_recording': False,
            'score': None
        }
        save_project_metadata(project_id, project_data)
        print(f"Project metadata saved")
        print("="*50 + "\n")

        return jsonify({
            'success': True,
            'project_id': project_id,
            'redirect_url': url_for('mixer', project_id=project_id)
        })

    except Exception as e:
        print(f"\nEXCEPTION in upload handler: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*50 + "\n")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects', methods=['GET'])
def api_get_projects():
    """Get all projects"""
    try:
        projects = get_all_projects()
        return jsonify({'success': True, 'projects': projects})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<project_id>', methods=['GET'])
def api_get_project(project_id):
    """Get specific project"""
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
    """Delete a project"""
    try:
        project_folder = os.path.join(PROJECTS_FOLDER, project_id)
        if os.path.exists(project_folder):
            import shutil
            shutil.rmtree(project_folder)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/save-recording/<project_id>', methods=['POST'])
def save_recording(project_id):
    """Save user recording"""
    try:
        if 'recording' not in request.files:
            return jsonify({'success': False, 'error': 'No recording uploaded'}), 400
        
        recording = request.files['recording']
        
        if recording.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        project_folder = os.path.join(PROJECTS_FOLDER, project_id)
        if not os.path.exists(project_folder):
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Save recording
        recording_path = os.path.join(project_folder, 'recording.wav')
        recording.save(recording_path)
        
        # Update metadata
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
    return jsonify({'success': True, 'settings': load_settings()})


@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    try:
        data = request.get_json(silent=True) or {}
        current = load_settings()
        current.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
        save_settings_to_disk(current)
        return jsonify({'success': True, 'settings': current})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/storage-info', methods=['GET'])
def api_storage_info():
    try:
        import shutil
        total_bytes = 0
        project_count = 0
        for root, dirs, files in os.walk(PROJECTS_FOLDER):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total_bytes += os.path.getsize(fp)
                except OSError:
                    pass
        for pid in os.listdir(PROJECTS_FOLDER):
            if os.path.isdir(os.path.join(PROJECTS_FOLDER, pid)):
                project_count += 1
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
    try:
        import shutil
        removed = 0
        # Clear uploads/ folder
        for item in os.listdir(UPLOAD_FOLDER):
            p = os.path.join(UPLOAD_FOLDER, item)
            try:
                os.remove(p); removed += 1
            except Exception:
                pass
        return jsonify({'success': True, 'removed': removed})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analyze-performance/<project_id>', methods=['POST'])
def analyze_performance(project_id):
    """Analyze vocal performance using AI"""
    try:
        # TODO: Implement actual AI analysis
        # Mock response for now
        analysis = {
            'overall_score': 85,
            'pitch_accuracy': 88,
            'timing_accuracy': 82,
            'volume_stability': 87,
            'similarity': 84,
            'feedback': 'Great performance! Your pitch control is excellent. Work on timing in faster sections.'
        }
        
        # Update project with score
        project = load_project(project_id)
        if project:
            project['score'] = analysis['overall_score']
            save_project_metadata(project_id, project)
        
        return jsonify({'success': True, 'analysis': analysis})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/projects/<project_id>/save-mix', methods=['POST'])
def save_mix(project_id):
    """Persist mix settings (volumes, mutes, solos, tempo, pitch) to project metadata"""
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


@app.route('/api/stems/<project_id>', methods=['GET'])
def api_get_stems(project_id):
    """Return playable URLs for all stems of a project"""
    try:
        project = load_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        stems_folder = project.get('stems_folder', '')
        if not stems_folder or not os.path.exists(stems_folder):
            return jsonify({'success': False, 'error': 'Stems not found'}), 404

        stems = {}
        for stem_file in os.listdir(stems_folder):
            if stem_file.endswith('.wav'):
                name = os.path.splitext(stem_file)[0]   # vocals, drums, bass, other
                # Build a forward-slash URL for the browser
                url_path = stems_folder.replace('\\', '/') + '/' + stem_file
                stems[name] = '/files/' + url_path

        return jsonify({'success': True, 'stems': stems, 'project': project})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/files/<path:filename>')
def serve_file(filename):
    """Serve project files (stems, recordings, originals)"""
    # filename arrives with forward slashes from the browser
    safe = filename.replace('/', os.sep)
    base_dir = os.path.abspath(os.getcwd())
    abs_path = os.path.abspath(os.path.join(base_dir, safe))
    # Security: ensure the path stays inside the project root
    if not abs_path.startswith(base_dir):
        return jsonify({'error': 'Forbidden'}), 403
    directory = os.path.dirname(abs_path)
    file_name  = os.path.basename(abs_path)
    return send_from_directory(directory, file_name)


# ============================================
# HELPER FUNCTIONS
# ============================================

def save_project_metadata(project_id, data):
    """Save project metadata to JSON file"""
    project_folder = os.path.join(PROJECTS_FOLDER, project_id)
    metadata_file = os.path.join(project_folder, 'metadata.json')
    
    with open(metadata_file, 'w') as f:
        json.dump(data, f, indent=2)


def load_project(project_id):
    """Load project metadata from JSON file"""
    project_folder = os.path.join(PROJECTS_FOLDER, project_id)
    metadata_file = os.path.join(project_folder, 'metadata.json')
    
    if not os.path.exists(metadata_file):
        return None
    
    try:
        with open(metadata_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading project: {e}")
        return None


def get_all_projects():
    """Get all projects from projects folder"""
    projects = []
    
    if not os.path.exists(PROJECTS_FOLDER):
        return projects
    
    for project_id in os.listdir(PROJECTS_FOLDER):
        project_folder = os.path.join(PROJECTS_FOLDER, project_id)
        if os.path.isdir(project_folder):
            project = load_project(project_id)
            if project:
                projects.append(project)
    
    # Sort by creation date (newest first)
    projects.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return projects


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({'success': False, 'error': 'File too large. Maximum size is 50MB'}), 413


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Endpoint not found'}), 404
    return render_template('home.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    return render_template('home.html'), 500


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, threaded=True)

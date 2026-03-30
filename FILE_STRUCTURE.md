================================================================================
KARAOKE STUDIO - FILE & FOLDER STRUCTURE DOCUMENTATION
================================================================================
Complete guide to every file in the project and what it does.

Last Updated: March 29, 2026
App: AI STEM Karaoke Studio
Version: 1.0


================================================================================
ROOT DIRECTORY FILES
================================================================================

### app.py (1000+ lines)
**Purpose**: Main Flask backend server. Heart of the application.
**Contains**:
- CORS header setup
- Settings management (load/save from disk)
- Model pre-warming (background thread)
- All HTTP routes (page routes + API routes)
- Error handlers

**Key Routes**:
- Page routes: / (home), /mixer, /karaoke, /compare, /projects, /settings
- Upload routes: /upload, /upload-url
- API routes: /api/settings, /api/stems, /api/save-recording, /api/export-karaoke, etc.
- File serving: /files/<path> (streams audio files to browser)

**Dependencies**: Flask, demucs, werkzeug, requests, subprocess
**Run**: `python app.py` → starts server on http://localhost:5000

---

### config.py (100+ lines)
**Purpose**: Environment-specific configuration settings.
**Contains**:
- Base Config class (shared by all environments)
- DevelopmentConfig (debug mode, verbose logging)
- ProductionConfig (security hardened, requires env vars)
- TestingConfig (separate test database)
- get_config() function to retrieve correct config

**Settings Managed**:
- File upload: UPLOAD_FOLDER, MAX_CONTENT_LENGTH (50MB)
- Allowed formats: mp3, wav, flac, ogg, m4a, aac
- Demucs models: htdemucs, htdemucs_ft, htdemucs_6s, mdx_extra, mdx_extra_q
- Audio processing: sample rates, buffer sizes
- Session management: cookie settings, CSRF protection
- Feature flags: YouTube download, AI analysis, cloud storage

**Run**: Never run directly. Imported by app.py

---

### requirements.txt
**Purpose**: Python package dependencies for the project.
**Contains**:
- Flask: Web framework
- Demucs: Audio stem separation AI
- torchaudio: Audio loading/saving with PyTorch
- torch: Deep learning framework (GPU support)
- librosa: Audio feature extraction
- mir_eval: Music Information Retrieval evaluation metrics
- yt-dlp: YouTube audio download
- requests: HTTP requests library
- werkzeug: Secure file handling

**Usage**: `pip install -r requirements.txt` (installs all packages)

---

### settings.json
**Purpose**: User settings file (persistent storage).
**Contains**: User preferences saved from /settings page
**Format**: JSON key-value pairs
**Example**:
```json
{
  "theme": "dark",
  "sample_rate": "48000",
  "default_model": "htdemucs",
  "show_animations": true,
  "max_storage": "1000"
}
```
**Creation**: Auto-created on first run with DEFAULT_SETTINGS from app.py
**Modification**: Updated when user clicks "Save Settings" on /settings page

---

### karaoke_studio.db
**Purpose**: SQLite database for project data (future use, currently uses JSON).
**Status**: Partially implemented, mostly using JSON metadata files instead
**Schema**: projects, recordings, settings tables
**Usage**: Not actively used in current version

---

### README.md
**Purpose**: Project overview and quick start guide.
**Contains**:
- Project description
- Feature list
- Installation steps
- How to run
- Technology stack

---

### API_DOCUMENTATION.md
**Purpose**: Complete API reference for all 10 endpoints.
**Contains**:
- Endpoint paths, methods, request/response examples
- Status codes and error handling
- cURL examples for each endpoint
- Use cases and examples

---

### important.txt
**Purpose**: Notes about the project (temporary/maintenance notes).
**Contents**: Varies, typically deployment notes or known issues


================================================================================
CORE FOLDERS
================================================================================

## /database/ (Database Layer)

### database/__init__.py
**Purpose**: Package initialization file (empty or minimal imports).
**Status**: Exists for Python package structure.

### database/db.py
**Purpose**: Database utilities and initialization (currently minimal use).
**Contains**:
- Database connection setup
- Table initialization (projects, recordings, settings)
- Project CRUD operations (not actively used)
- Settings storage functions

**Status**: Partially implemented. App uses JSON files for project metadata instead.
**Future Use**: Intended for scaling to SQLite instead of JSON


================================================================================
SERVICES FOLDER (/services)
================================================================================
Business logic and external service integrations.

### services/__init__.py
**Purpose**: Package initialization file.
**Status**: Empty (just marks folder as Python package).

### services/demucs_service.py (250+ lines)
**Purpose**: AI audio stem separation using Demucs model.
**Key Functions**:
- `_get_device()`: Detects GPU/CPU (CUDA > MPS > CPU)
- `_load_model(name)`: Loads Demucs model, caches in memory (huge speedup)
- `separate_audio(file_path, model, output_folder)`: Main function
  - Loads audio file
  - Converts to model format
  - Runs AI inference (1-3 minutes)
  - Saves 4 stems: vocals, drums, bass, other

**How It Works**:
1. First call: ~30-60 seconds (model loads from disk to GPU/CPU memory)
2. Subsequent calls: Use cached model (instant model load, still 1-3 min for processing)
3. Outputs: projects/{project_id}/stems/htdemucs/{track_name}/{vocals,drums,bass,other}.wav

**Dependencies**: torch, torchaudio, demucs library

---

### services/scoring_service.py (150+ lines)
**Purpose**: AI vocal performance analysis (compare user recording vs original).
**Key Function**:
- `analyze_vocal_accuracy(vocal_path, recording_path)`: Analyze singing quality

**Metrics Returned** (0-100 scale):
- Pitch accuracy: Stay on key
- Timing accuracy: Hit beats correctly
- Tone quality: Match timbre/voice quality
- Expression: Dynamic changes
- Consistency: Stable pitch/tone
- Breath control: Pause patterns

**Technologies**: librosa (feature extraction), mir_eval (MIR metrics)
**Status**: Fully implemented, ready to use

---

### services/url_service.py (150+ lines)
**Purpose**: Download audio from URLs (YouTube & direct links).
**Key Functions**:
- `is_youtube_url(url)`: Detect YouTube links
- `download_from_youtube(url, folder)`: Extract video audio as MP3
- `download_direct_audio(url, folder)`: Download direct audio file links

**How It Works**:
1. Detect URL type (YouTube or direct)
2. Download (yt-dlp for YouTube, requests for direct)
3. Convert to MP3 (YouTube only, via ffmpeg)
4. Save to folder with timestamp

**Dependencies**: yt-dlp, requests, ffmpeg (system binary)

---

### services/__pycache/
**Purpose**: Python bytecode cache (auto-generated).
**Status**: No need to modify; auto-generated for performance


================================================================================
STATIC ASSETS FOLDER (/static)
================================================================================
Frontend CSS and JavaScript.

### static/css/style.css (1000+ lines)
**Purpose**: All styling for the web interface.
**Contains**:
- Layout styles (grid, flexbox)
- Component styles (buttons, inputs, modals)
- Theme variables (colors, fonts, spacing)
- Responsive design (mobile, tablet, desktop)
- Dark/light theme support

**How It's Used**: Imported in templates/base.html via `<link rel="stylesheet">`
**Modification**: Change app appearance by editing this file

---

### static/js/script.js (1500+ lines)
**Purpose**: Client-side JavaScript for all interactivity.
**Key Features**:
- Page routing (handle navigation without page reloads)
- Fetch API calls to backend (GET /api/settings, POST /upload, etc.)
- Audio playback (WebAudio API)
- Recording (MediaRecorder API)
- Form handling and validation
- UI state management

**Main Workflows**:
1. User uploads file → POST /upload → Demucs processes → GET /mixer
2. User records vocal → POST /api/save-recording → saved to disk
3. User changes settings → POST /api/settings → saved to settings.json
4. User exports karaoke → GET /api/export-karaoke → download WAV

**Dependencies**: Vanilla JS (no frameworks)


================================================================================
TEMPLATES FOLDER (/templates)
================================================================================
HTML templates rendered by Flask.

### templates/base.html
**Purpose**: Base template extended by all pages.
**Contains**:
- HTML structure (<head>, <body>)
- Links to CSS/JS files
- Navigation navbar
- Block placeholders for child templates

**How It Works**: Other templates use `{% extends "base.html" %}` to inherit structure

---

### templates/home.html
**Purpose**: Home page - file upload interface.
**Features**:
- Upload file input
- Drag-and-drop support
- Upload button
- Progress indicator

**Route**: GET / → render home.html
**JavaScript**: Handles form submission → POST /upload

---

### templates/mixer.html
**Purpose**: Stem mixer page - adjust individual stem volumes.
**Features**:
- 4 sliders (vocals, drums, bass, other volumes)
- Master volume control
- Effects controls (reverb, echo)
- Tempo/pitch adjustment
- Export karaoke button

**Route**: GET /mixer/<project_id> → render mixer.html
**JavaScript**: 
- GET /api/stems/{project_id} → get stem URLs
- WebAudio API → play stems with effects
- POST /api/projects/{id}/save-mix → save mix settings

---

### templates/karaoke.html (2000+ lines)
**Purpose**: Karaoke recording page - main feature.
**Features**:
- Load and play backing tracks (stems without vocals)
- Record user vocal via microphone
- Playback recording
- Save recording
- Audio visualizer (waveform)
- Playback controls (play, pause, stop)

**Route**: GET /karaoke/<project_id> → render karaoke.html
**Key JavaScript Functions**:
- `loadStems()`: GET /api/stems → load 4 audio files
- `playBacking()`: Play drums+bass+other (no vocals for user to sing over)
- `startRecording()`: Access microphone, record audio
- `stopRecording()` / `saveRecording()`: Save vocal → POST /api/save-recording

**Critical Code**: 
- Audio cleanup handlers (prevents stale audio on page re-entry)
- Audio context management (suspend/resume handling)
- Browser autoplay policy unlock

---

### templates/compare.html
**Purpose**: Comparison page - compare original vocals vs user recording.
**Features**:
- Waveform display of both tracks
- Side-by-side playback
- AI analysis button

**Route**: GET /compare/<project_id> → render compare.html
**Requires**: Project must have recording + vocal stem

---

### templates/projects.html
**Purpose**: Projects list page - browse all karaoke projects.
**Features**:
- List of all projects
- Project metadata (name, date, stems, recording status)
- Links to mixer, karaoke, compare pages
- Delete project buttons

**Route**: GET /projects → render projects.html
**JavaScript**: GET /api/projects → fetch all projects

---

### templates/settings.html (600+ lines)
**Purpose**: Settings page - user preferences.
**Tabs**:
- Audio Settings (sample rate, buffer size, input/output devices)
- Processing (Demucs model selection, quality)
- Appearance (theme, animations, compact mode)
- Storage (max size, cleanup options)
- Advanced (debug mode, export format)

**Route**: GET /settings → render settings.html
**JavaScript**:
- GET /api/settings → load current settings
- POST /api/settings → save changes to settings.json
- GET /api/storage-info → show disk usage
- POST /api/clear-cache → delete temporary files

**Special Feature**: API endpoint field is auto-detected (hidden from users)

---

### templates/components/ (Reusable HTML Components)

#### components/navbar.html
**Purpose**: Navigation bar shown on all pages.
**Contains**: Logo, nav links (home, projects, settings), current page indicator

#### components/progress_bar.html
**Purpose**: Upload progress indicator.
**Shows**: File size, upload percentage, time remaining

#### components/stem_controls.html
**Purpose**: Stem playback controls (reused in multiple pages).
**Shows**: Individual stem sliders, mute/solo buttons

#### components/master_controls.html
**Purpose**: Main playback controls (common to mixer and karaoke).
**Shows**: Master volume, play/pause/stop buttons, timeline

#### components/recording_controls.html
**Purpose**: Microphone recording controls (karaoke page).
**Shows**: Record button, stop button, save button, recording timer

#### components/waveform_section.html
**Purpose**: Audio waveform visualization (for visual feedback).
**Uses**: Canvas API to draw waveform

#### components/karaoke_controls.html
**Purpose**: Karaoke-specific controls.
**Shows**: Backing track volume, recording monitor, vocal effects

#### components/ai_score_dashboard.html
**Purpose**: AI performance analysis results display.
**Shows**: Pitch, timing, tone, expression, consistency, breath scores and feedback

#### components/comparison_layout.html
**Purpose**: Side-by-side layout for compare page.
**Shows**: Original vocals vs user recording

#### components/upload_section.html
**Purpose**: File upload widget (home page).
**Shows**: Upload input, drag-drop area, format requirements

#### components/projects_list.html
**Purpose**: Projects list rendering (projects page).
**Shows**: Project cards with metadata and action buttons

#### components/settings_panel.html
**Purpose**: Settings form container (settings page).
**Shows**: Tabs and form fields organized by category


================================================================================
DATA FOLDERS
================================================================================

## /projects/ (User Projects)
**Purpose**: Store all karaoke projects and data.
**Structure**:
```
projects/
├── 20260329_212407/          (project ID: timestamp format YYYYMMDD_HHMMSS)
│   ├── metadata.json         (project info: name, stems path, recording status)
│   ├── original_song.mp3     (uploaded audio file)
│   ├── recording.wav         (user vocal recording)
│   ├── stems/                (separated audio stems folder)
│   │   └── htdemucs/
│   │       └── song_name/
│   │           ├── vocals.wav
│   │           ├── drums.wav
│   │           ├── bass.wav
│   │           └── other.wav
│   └── exports/              (generated files)
│       └── karaoke_with_user_vocals.wav
│
└── 20260330_152000/
    ├── metadata.json
    ├── original_...
    └── ...
```

**metadata.json Contents**:
```json
{
  "id": "20260329_212407",
  "name": "song_title",
  "original_file": "projects/20260329_212407/original_song.mp3",
  "stems_folder": "projects/20260329_212407/stems/htdemucs/song_name",
  "model": "htdemucs",
  "created_at": "2026-03-29T21:24:55.034654",
  "has_recording": true,
  "score": 85,
  "mix_settings": {...}
}
```

**How Used**:
- Each project is a directory named by timestamp
- metadata.json tracks project state
- Stems are loaded in mixer/karaoke pages
- User recording saved when recording submitted

---

## /uploads/ (Temporary Files)
**Purpose**: Temporary storage during file processing.
**Status**: Cleared by "Clear Cache" button
**Cleanup**: POST /api/clear-cache removes all files here

---

## /__pycache__/ (Python Cache)
**Purpose**: Auto-generated Python bytecode cache.
**Status**: Auto-generated, safe to delete (will be regenerated)
**Note**: No need to modify


================================================================================
DEVELOPMENT & TESTING FILES
================================================================================

### .gitignore
**Purpose**: Git ignore rules (which files not to commit).
**Contents**: __pycache__, venv/, *.pyc, settings.json, karaoke_studio.db, etc.

### .git/ (Git Repository)
**Purpose**: Version control history.
**Status**: Project is a Git repo, can commit/rollback changes

### .vscode/ (VS Code Settings)
**Purpose**: Editor configuration for VS Code.
**Contents**: Workspace settings, extensions recommendations

### venv/ (Virtual Environment)
**Purpose**: Isolated Python environment for this project.
**Location**: c:\Users\HP\Desktop\ai-stem-karaoke-studio\venv\
**Contains**: Python executable, all installed packages (from requirements.txt)
**Activation**: `& venv\Scripts\Activate.ps1` (PowerShell)


================================================================================
KEY FILES TO KNOW FOR MENTOR PRESENTATION
================================================================================

**Show These To Mentor:**

1. **Architecture Overview**: Read top of app.py (module docstring)
   - Shows Flask structure, route organization, workflow

2. **Upload & Stem Separation**: app.py - `/upload` route + demucs_service.py
   - Shows how file processing works end-to-end
   - How AI model gets cached for speed

3. **Karaoke Recording**: templates/karaoke.html + app.py `/api/save-recording`
   - Shows how user records vocals
   - How audio gets converted to standard format

4. **API Design**: app.py - "API ROUTES" section
   - Shows all 10 endpoints and responses
   - How frontend communicates with backend

5. **Settings Management**: config.py + app.py load_settings/save_settings
   - Shows how user preferences persist
   - Environment-specific configuration

6. **File Storage**: /projects folder structure
   - Shows how data is organized
   - Project metadata system

7. **Frontend Flow**: static/js/script.js + templates/
   - Shows client-side workflow
   - API call patterns


================================================================================
FILE MODIFICATION GUIDELINES
================================================================================

**Safe to Edit:**
- static/js/script.js: Add features, fix bugs
- static/css/style.css: Change appearance
- templates/*.html: Modify UI, add new pages
- app.py: Add new routes, modify logic

**Be Careful:**
- config.py: Changing settings affects all environments
- demucs_service.py: Model loading/caching is critical
- requirements.txt: Version changes may break compatibility

**Never Delete (Core Functionality):**
- app.py: Main server
- demucs_service.py: Stem separation
- templates/karaoke.html: Recording feature
- config.py: Configuration


================================================================================
END OF DOCUMENTATION
================================================================================

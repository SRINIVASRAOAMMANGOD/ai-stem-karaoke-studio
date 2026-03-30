"""
================================================================================
KARAOKE STUDIO - CONFIGURATION
================================================================================
Environment-specific settings for Flask app.

Three configurations:
1. DEVELOPMENT - Debug mode, verbose logging, easy testing
2. PRODUCTION - Security hardened, optimized, requires env variables
3. TESTING - Test-specific settings with SQLite

Key Settings:
- File upload: 50MB max allowed
- Audio support: MP3, WAV, FLAC, M4A, OGG, AAC
- Demucs models: htdemucs (default), htdemucs_ft, htdemucs_6s, etc
- Audio processing: 48kHz sample rate, 512 sample buffer
================================================================================
"""

import os
from datetime import timedelta


class Config:
    """
    Base configuration - shared by all environments.
    Override in subclasses for environment-specific settings.
    """
    
    # ── Flask Core Settings ───────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = False
    TESTING = False
    
    # ── File Upload Settings ──────────────────────────────────────────────
    UPLOAD_FOLDER = 'uploads'                              # Temporary upload folder
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024                 # 50MB max file size
    ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'ogg', 'm4a', 'aac'}  # Supported formats
    
    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_FILE = 'karaoke_studio.db'                    # SQLite database path
    
    # ── Audio Stem Separation (Demucs AI) ─────────────────────────────────
    DEFAULT_MODEL = 'htdemucs'                             # Default Demucs model for separation
    AVAILABLE_MODELS = [
        'htdemucs',        # Recommended: 4-stem separation (vocals, drums, bass, other)
        'htdemucs_ft',     # Fine-tuned version
        'htdemucs_6s',     # 6-stem version (more granular)
        'mdx_extra',       # Alternative model
        'mdx_extra_q'      # Quantized version (smaller, faster)
    ]
    
    # ── Audio Processing Settings ─────────────────────────────────────────
    DEFAULT_SAMPLE_RATE = 48000                            # Audio sample rate (Hz)
    DEFAULT_BUFFER_SIZE = 512                              # WebAudio buffer size (samples)
    
    # ── Session Management ────────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)       # Session duration
    SESSION_COOKIE_SECURE = False                          # HTTPS only (set True in production)
    SESSION_COOKIE_HTTPONLY = True                         # Prevent JS access to cookies
    SESSION_COOKIE_SAMESITE = 'Lax'                        # CSRF protection
    
    # ── API Rate Limiting ─────────────────────────────────────────────────
    API_MAX_REQUESTS_PER_MINUTE = 60                       # Prevent abuse
    
    # ── Feature Flags ─────────────────────────────────────────────────────
    ENABLE_YOUTUBE_DOWNLOAD = True                         # Allow downloading from YouTube
    ENABLE_AI_ANALYSIS = True                              # Enable vocal performance analysis
    ENABLE_CLOUD_STORAGE = False                           # Cloud storage integration (future)


class DevelopmentConfig(Config):
    """
    Development configuration - for local testing and debugging.
    Features: Debug mode on, stack traces shown, auto-reload on code changes
    """
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """
    Production configuration - security hardened, optimized.
    IMPORTANT: Requires SECRET_KEY environment variable to be set!
    """
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # HTTPS only
    
    def __init__(self):
        super().__init__()
        # Force SECRET_KEY to be set from environment in production
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            raise ValueError("❌ ERROR: SECRET_KEY environment variable must be set in production")
        self.SECRET_KEY = secret_key


class TestingConfig(Config):
    """
    Testing configuration - for unit tests and automated testing.
    Features: Uses separate test database, CSRF disabled for testing
    """
    DEBUG = True
    TESTING = True
    DATABASE_FILE = 'test_karaoke_studio.db'  # Separate from production
    WTF_CSRF_ENABLED = False                   # Allow forms in tests


# ── Configuration Registry ────────────────────────────────────────────────
# Maps environment names to Config classes
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig  # Default if env not specified
}


def get_config(config_name=None):
    """
    Get configuration class by name.
    Falls back to FLASK_ENV environment variable, then 'development'.
    
    Usage in app.py:
        config = get_config(os.environ.get('FLASK_ENV', 'development'))
        app.config.from_object(config)
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    return config.get(config_name, config['default'])


import os
from datetime import timedelta

class Config:
    """Base configuration"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = False
    TESTING = False
    
    # File upload settings
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'ogg', 'm4a', 'aac'}
    
    # Database settings
    DATABASE_FILE = 'karaoke_studio.db'
    
    # Demucs settings
    DEFAULT_MODEL = 'htdemucs'
    AVAILABLE_MODELS = [
        'htdemucs',
        'htdemucs_ft',
        'htdemucs_6s',
        'mdx_extra',
        'mdx_extra_q'
    ]
    
    # Audio processing settings
    DEFAULT_SAMPLE_RATE = 48000
    DEFAULT_BUFFER_SIZE = 512
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # API settings
    API_MAX_REQUESTS_PER_MINUTE = 60
    
    # Feature flags
    ENABLE_YOUTUBE_DOWNLOAD = True
    ENABLE_AI_ANALYSIS = True
    ENABLE_CLOUD_STORAGE = False


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # Override with environment variables in production
    def __init__(self):
        super().__init__()
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            raise ValueError("SECRET_KEY environment variable must be set in production")
        self.SECRET_KEY = secret_key


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    
    # Use separate test database
    DATABASE_FILE = 'test_karaoke_studio.db'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """Get configuration by name"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    return config.get(config_name, config['default'])

"""
Configuration settings for Hajri.ai
Centralizes all paths and configuration in one place
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration with centralized path management"""
    
    # Application Info
    APP_NAME = "Hajri.ai"
    VERSION = "1.0.0"
    
    # Base Paths (using pathlib for cross-platform compatibility)
    BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Project root
    SRC_DIR = BASE_DIR / "src"
    ASSETS_DIR = BASE_DIR / "assets"
    SCRIPTS_DIR = BASE_DIR / "scripts"
    DOCS_DIR = BASE_DIR / "docs"
    TESTS_DIR = BASE_DIR / "tests"
    
    # Data Paths
    TRAINING_IMAGES_DIR = ASSETS_DIR / "training_images"
    DB_FILE = ASSETS_DIR / "hajri.db"
    LOGO_PATH = ASSETS_DIR / "logo.png"
    
    # Source Code Paths
    MODELS_DIR = SRC_DIR / "models"
    LEGACY_DIR = SRC_DIR / "legacy"
    CONFIG_DIR = SRC_DIR / "config"
    DATABASE_DIR = SRC_DIR / "database"
    SERVICES_DIR = SRC_DIR / "services"
    UI_DIR = SRC_DIR / "ui"
    UTILS_DIR = SRC_DIR / "utils"
    
    # Database
    DB_FOREIGN_KEYS = True
    
    # Authentication
    COOKIE_NAME = "hajri_cookie_name"
    COOKIE_EXPIRY_DAYS = 30
    SECRET_KEY = os.getenv("SECRET_KEY", "hajri_secret_key_123")
    
    # Default Admin
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
    ADMIN_EMAIL = "admin@example.com"
    
    # Email Configuration
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    
    # Face Recognition
    FACE_MODEL = "SFace"
    DETECTOR_BACKEND = "opencv"
    ENFORCE_DETECTION = False
    
    # Image Processing
    NUM_TRAINING_IMAGES = 10
    NUM_AUGMENTED_IMAGES = 50
    IMAGE_SIZE = (224, 224)
    
    # Attendance
    DEFAULT_ATTENDANCE_THRESHOLD = 75  # Percentage
    
    # Cache Settings
    CACHE_TTL = 3600  # 1 hour in seconds
    
    # Streamlit Page Config
    PAGE_TITLE = "Hajri.ai"
    PAGE_ICON = "🎓"
    LAYOUT = "wide"
    SIDEBAR_STATE = "collapsed"
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        directories = [
            cls.ASSETS_DIR,
            cls.TRAINING_IMAGES_DIR,
            cls.MODELS_DIR,
            cls.SCRIPTS_DIR,
            cls.DOCS_DIR,
            cls.TESTS_DIR,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate_config(cls):
        """Validate critical configuration"""
        issues = []
        
        if cls.ADMIN_PASSWORD == "changeme" and not os.getenv("ADMIN_PASSWORD"):
            issues.append("⚠️  ADMIN_PASSWORD not set in .env. Using insecure default.")
        
        if not cls.SENDER_EMAIL or not cls.SENDER_PASSWORD:
            issues.append("⚠️  Email credentials not set. Email notifications will not work.")
        
        if not cls.LOGO_PATH.exists():
            issues.append(f"⚠️  Logo not found at {cls.LOGO_PATH}. Using fallback.")
        
        return issues
    
    @classmethod
    def get_path(cls, *parts):
        """
        Get a path relative to BASE_DIR
        
        Args:
            *parts: Path components
            
        Returns:
            Path object
        """
        return cls.BASE_DIR.joinpath(*parts)
    
    @classmethod
    def get_asset_path(cls, *parts):
        """Get a path relative to ASSETS_DIR"""
        return cls.ASSETS_DIR.joinpath(*parts)
    
    @classmethod
    def get_src_path(cls, *parts):
        """Get a path relative to SRC_DIR"""
        return cls.SRC_DIR.joinpath(*parts)


# Create directories on import
Config.ensure_directories()

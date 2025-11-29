"""
Configuration settings for MultiAgent Platform
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///financial_coach.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # CORS
    CORS_HEADERS = 'Content-Type'
    
    # Google Gemini
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = 'gemini-2.5-flash'
    
    # Application
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    JSON_SORT_KEYS = False
    
    # Agent Configuration
    AGENT_TIMEOUT = 30  # seconds
    MAX_CONCURRENT_TASKS = 10
    
    # Financial Analysis
    DEFAULT_CURRENCY = 'USD'
    EMERGENCY_FUND_MONTHS = 6
    SAVINGS_RATE_TARGET = 0.20  # 20%
    
    # Pagination
    ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 100

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # In production, these should be set via environment variables
    # and should be strong, unique values
    @property
    def SECRET_KEY(self):
        secret_key = os.getenv('SECRET_KEY')
        if not secret_key:
            raise ValueError("SECRET_KEY must be set in production")
        return secret_key
    
    @property
    def GEMINI_API_KEY(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be set in production")
        return api_key

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(env=None):
    """Get configuration based on environment"""
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])

"""
Backend Configuration

Environment-based configuration for the AI Personal Tutor backend.
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration."""

    # Flask settings
    DEBUG: bool = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    PORT: int = int(os.getenv('PORT', '8000'))
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-prod')

    # CORS settings
    CORS_ORIGINS: str = os.getenv('CORS_ORIGINS', '*')

    # Ollama settings
    OLLAMA_HOST: str = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    OLLAMA_MODEL: str = os.getenv('OLLAMA_MODEL', 'llama3.2')

    # AWS settings
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-west-2')
    S3_BUCKET: str = os.getenv('S3_BUCKET', 'ai-tutor-audio')

    # Lesson settings
    LESSONS_PER_URL: int = int(os.getenv('LESSONS_PER_URL', '3'))
    MAX_CONTENT_LENGTH: int = int(os.getenv('MAX_CONTENT_LENGTH', '100000'))

    # Voice configuration
    ALEX_VOICE: str = os.getenv('ALEX_VOICE', 'Matthew')
    SAM_VOICE: str = os.getenv('SAM_VOICE', 'Joanna')

    # Database configuration
    DATABASE_URL: str = os.getenv('DATABASE_URL', '')
    USE_DATABASE: bool = bool(os.getenv('DATABASE_URL', ''))

    # Session storage (future Redis support)
    REDIS_URL: str = os.getenv('REDIS_URL', '')
    USE_REDIS: bool = bool(os.getenv('USE_REDIS', ''))


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG: bool = True


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG: bool = False


class TestingConfig(Config):
    """Testing environment configuration."""
    DEBUG: bool = True
    TESTING: bool = True


def get_config() -> Config:
    """Get configuration based on environment."""
    env = os.getenv('FLASK_ENV', 'development')

    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }

    return configs.get(env, DevelopmentConfig)()

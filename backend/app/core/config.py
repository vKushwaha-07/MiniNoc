"""
Core Configuration Module for Mini NOC.
Centralizes all application settings and environment variables.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Mini NOC - Network Monitoring System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./mini_noc.db"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # On Vercel, use /tmp for SQLite if no DATABASE_URL is set
        if os.getenv("VERCEL") and "sqlite:///./" in self.DATABASE_URL:
            self.DATABASE_URL = "sqlite:////tmp/mini_noc.db"
    
    # Monitoring Configuration
    SCAN_INTERVAL_SECONDS: int = 60
    PING_COUNT: int = 4
    PING_TIMEOUT_SECONDS: float = 2.0
    
    # Thresholds
    PACKET_LOSS_WARNING_PERCENT: float = 10.0
    PACKET_LOSS_CRITICAL_PERCENT: float = 50.0
    LATENCY_WARNING_MS: float = 100.0
    LATENCY_CRITICAL_MS: float = 500.0
    CPU_WARNING_PERCENT: float = 80.0
    CPU_CRITICAL_PERCENT: float = 95.0
    
    # SNMP Defaults
    SNMP_COMMUNITY: str = "public"
    SNMP_PORT: int = 161
    SNMP_TIMEOUT: float = 2.0
    
    # Consecutive failures before marking DOWN
    DOWN_THRESHOLD_COUNT: int = 3
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

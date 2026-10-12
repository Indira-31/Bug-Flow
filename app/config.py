import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    PROJECT_NAME: str = "BugFlow - Software Issue Tracking & Resolution Platform"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # JWT Auth Configuration
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", 
        "bugflow-super-secure-jwt-secret-key-enterprise-2026-production-token-v1"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/bugflow.db")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_PRE_PING: bool = True
    
    # File Storage
    UPLOAD_DIR: Path = BASE_DIR / "app" / "uploads"

settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
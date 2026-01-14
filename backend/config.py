from pydantic_settings import BaseSettings
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

class Settings(BaseSettings):
    # MongoDB
    mongo_url: str = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name: str = os.environ.get('DB_NAME', 'portal_database')
    
    # JWT
    jwt_secret_key: str = os.environ.get('JWT_SECRET_KEY', 'default-secret-key-change-in-production')
    jwt_algorithm: str = os.environ.get('JWT_ALGORITHM', 'HS256')
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 hours
    jwt_refresh_token_expire_days: int = 30
    
    # CORS
    cors_origins: str = os.environ.get('CORS_ORIGINS', '*')
    
    # Encryption
    encryption_key: str = os.environ.get('ENCRYPTION_KEY', 'YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=')
    
    # Portal Magic Link
    portal_base_url: str = os.environ.get('PORTAL_BASE_URL', 'http://localhost:3000')
    portal_token_expire_hours: int = int(os.environ.get('PORTAL_TOKEN_EXPIRE_HOURS', '24'))
    
    # Internal API
    internal_api_secret: str = os.environ.get('INTERNAL_API_SECRET', 'internal-api-secret-key')
    
    # Withdrawal
    min_withdrawal_amount: float = float(os.environ.get('MIN_WITHDRAWAL_AMOUNT', '20.0'))
    
    # AI / LLM Integration
    emergent_llm_key: str = os.environ.get('EMERGENT_LLM_KEY', '')
    
    class Config:
        env_file = '.env'

settings = Settings()

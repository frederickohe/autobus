from pydantic import BaseSettings
from sqlalchemy.engine.url import URL
import os


class Settings(BaseSettings):
    SERVICE_NAME: str = "Autobus Backend"
    DEBUG: bool = os.environ.get('DEBUG', 'false').lower() == 'true'

    # Database Configuration - supports both traditional and Docker Postgres env vars
    DB_DRIVER: str = os.environ.get('DB_DRIVER', 'postgresql+asyncpg')
    DB_HOST: str = os.environ.get('PGHOST') or os.environ.get('DB_HOST')
    DB_PORT: int = int(os.environ.get('PGPORT', os.environ.get('DB_PORT', 5432)))
    DB_USER: str = os.environ.get('PGUSER') or os.environ.get('DB_USER')
    DB_PASSWORD: str = os.environ.get('PGPASSWORD') or os.environ.get('DB_PASSWORD')
    DB_DATABASE: str = os.environ.get('PGDATABASE') or os.environ.get('DB_DATABASE')
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 0
    DB_ECHO: bool = os.environ.get('DB_ECHO', 'false').lower() == 'true'

    # JWT Configuration
    SECRET_KEY: str = os.environ.get('SECRET_KEY', os.environ.get('JWT_SECRET_KEY', 'green-secret-keeps-gamma'))
    ALGORITHM: str = os.environ.get('ALGORITHM', os.environ.get('JWT_ALGORITHM', 'HS256'))
    KID: str = os.environ.get('KID', 'autobus-kid')
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 360
    
    # Redis Configuration
    REDIS_HOST: str = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT: str = os.environ.get('REDIS_PORT', '6379')
    REDIS_PASSWORD: str = os.environ.get('REDIS_PASSWORD', '')
    
    # Message Queue Configuration
    RABBIT_MQ_URL: str = os.environ.get('RABBIT_MQ_URL', '')
    RABBIT_MQ_ROUTING_KEY: str = os.environ.get('RABBIT_MQ_ROUTING_KEY', '')
    RABBIT_MQ_AUDIT_QUEUE: str = os.environ.get('RABBIT_MQ_AUDIT_QUEUE', '')
    SMS_MQ_QUEUE: str = os.environ.get('SMS_MQ_QUEUE', '')
    EMAIL_MQ_QUEUE: str = os.environ.get('EMAIL_MQ_QUEUE', '')
    BASE_FRONTEND_URL: str = os.environ.get('BASE_FRONTEND_URL', 'http://localhost:3000')
    BATCH_CUSTOMER_UPLOAD_QUEUE: str = os.environ.get('BATCH_CUSTOMER_UPLOAD_QUEUE', '')
    COMPANY_QUEUE: str = os.environ.get('COMPANY_QUEUE', '')

    # Wirepick SMS Configuration
    WIREPICK_API_URL = "https://api.wirepick.com/httpsms"
    WIREPICK_CLIENT_ID = "your_client_id"  # Replace with actual client ID
    WIREPICK_PASSWORD = "your_password"    # Replace with actual password
    WIREPICK_PUBLIC_KEY = "your_public_key" # Replace with actual public key (wpkKey)
    WIREPICK_SENDER_ID = "YourSenderID"     # Your approved sender ID
    USE_WIREPICK_API_KEY = False  # Set to True to use API key authentication, False to use client/password
    
    # OTP Configuration
    OTP_EXPIRE_MINUTES: int = int(os.environ.get('OTP_EXPIRE_MINUTES', 5))

    # MongoDB Logging
    MONGO_URI: str = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
    MONGO_DB_NAME: str = os.environ.get('MONGO_DB_NAME', 'api_logs_db')
    
    # Logging levels
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')

    @property
    def DB_DSN(self) -> URL:
        return URL.create(
            self.DB_DRIVER,
            self.DB_USER,
            self.DB_PASSWORD,
            self.DB_HOST,
            self.DB_PORT,
            self.DB_DATABASE,
        )

    @property
    def DB_URL_STRING(self) -> str:
        return f'{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}?async_fallback=true'

    def MULTI_TENANT_DB_STRING(self, migration_id: str) -> str:
        return (f'jdbc:postgresql://{self.DB_HOST}:'
                f'{self.DB_PORT}/{migration_id}?ApplicationName=MultiTenant')
        
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
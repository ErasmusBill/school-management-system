from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    DATABASE_URL: str
    
    JWT_ALGORITHM: str = "HS256" 
    JWT_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES : int
    REFRESH_TOKEN_EXPIRE_DAYS : int
    
    MAIL_USERNAME :str
    MAIL_PASSWORD :str
    MAIL_FROM :str
    MAIL_PORT : int
    MAIL_SERVER :str
    MAIL_FROM_NAME : str
    MAIL_STARTTLS :bool = True
    MAIL_SSL_TLS :bool = False
    USE_CREDENTIALS :bool = True
    VALIDATE_CERTS :bool = True
    
    
    REDIS_HOST :str
    REDIS_PORT : int
    REDIS_DB : int
    REDIS_PASSWORD : str = ""
    
    
    
    
    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore',
    )
    
    
Config = Settings()
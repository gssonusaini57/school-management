from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "mysql+pymysql://school:school@localhost:3306/school_management"
    JWT_SECRET: str = "change-me-in-prod"
    JWT_EXPIRY_HOURS: int = 8
    ADMIN_DEFAULT_PASSWORD: str = "admin123"
    SUPER_ADMIN_DEFAULT_PASSWORD: str = "super123"
    CORS_ORIGINS: str = "*"
    LOG_DIR: str = "./logs"
    STATIC_DIR: str = "../"
    BACKUP_DIR: str = "./backups"


settings = Settings()

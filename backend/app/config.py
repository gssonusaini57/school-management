from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "mysql+pymysql://school:school@localhost:3306/school_management"
    JWT_SECRET: str = "change-me-in-prod"
    JWT_EXPIRY_HOURS: int = 1
    ADMIN_DEFAULT_PASSWORD: str = "admin123"
    SUPER_ADMIN_DEFAULT_PASSWORD: str = "super123"
    CORS_ORIGINS: str = "*"
    LOG_DIR: str = "./logs"
    STATIC_DIR: str = "../"
    BACKUP_DIR: str = "./backups"

    # --- Outbound email (Zoho Mail) ---
    # SMTP credentials for the transactional mailbox (password-reset etc.).
    # Zoho India datacenter: smtp.zoho.in ; global: smtp.zoho.com. Port 465 = SSL.
    # SMTP_USER is the full mailbox address; SMTP_PASSWORD is a Zoho *app password*
    # (generate one under Zoho → My Account → Security → App Passwords when 2FA is on).
    SMTP_HOST: str = "smtp.zoho.in"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""           # e.g. info@kisschool.in
    SMTP_PASSWORD: str = ""       # Zoho app password
    SMTP_USE_SSL: bool = True     # True → SSL on 465; False → STARTTLS (use port 587)
    SMTP_FROM: str = ""           # defaults to SMTP_USER if blank
    SMTP_FROM_NAME: str = "Khalsa International School"

    # Base URL of the admin SPA, used to build password-reset links in emails.
    # No trailing slash. Reset page lives at <APP_BASE_URL>/reset-password?token=...
    APP_BASE_URL: str = "https://expressonly.in/school/admin"
    RESET_TOKEN_TTL_MINUTES: int = 30

    # Publicly-reachable logo URL embedded in transactional emails. Email clients
    # can't load bundled/relative images, so this must be an absolute URL. Left
    # blank, it derives from APP_BASE_URL → the crest shipped in the SPA's
    # public/ dir (served at <APP_BASE_URL>/brand/crest-mark.png).
    EMAIL_LOGO_URL: str = ""

    # Mailbox that receives "needs approval" workflow notifications (student/marks
    # edit requests, marks batch submissions). Blank → falls back to the sending
    # mailbox (smtp_from_address, i.e. info@kisschool.in).
    APPROVER_NOTIFY_EMAIL: str = ""

    @property
    def smtp_from_address(self) -> str:
        return self.SMTP_FROM or self.SMTP_USER

    @property
    def approver_notify_email(self) -> str:
        return self.APPROVER_NOTIFY_EMAIL or self.smtp_from_address

    @property
    def email_logo_url(self) -> str:
        if self.EMAIL_LOGO_URL:
            return self.EMAIL_LOGO_URL
        return f"{self.APP_BASE_URL.rstrip('/')}/brand/crest-mark.png"

    @property
    def email_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_USER and self.SMTP_PASSWORD)


settings = Settings()

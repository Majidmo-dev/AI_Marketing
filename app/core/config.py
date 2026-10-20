from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_JWT_SECRETS = {"unsafe-local-only-change-me", "replace-with-a-long-random-secret"}

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "AI Marketing SaaS"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/marketing_saas"
    jwt_secret_key: str = "unsafe-local-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    invitation_ttl_hours: int = 72
    auto_create_tables: bool = True
    agency_admin_emails: str = ""
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    app_base_url: str = "http://localhost:3000"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_default_price_id: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"

    @model_validator(mode="after")
    def require_real_secret_outside_local(self):
        if self.environment != "local" and (self.jwt_secret_key in PLACEHOLDER_JWT_SECRETS or len(self.jwt_secret_key) < 32):
            raise ValueError("JWT_SECRET_KEY must be a unique random value of at least 32 characters outside the local environment")
        return self

    @property
    def agency_admin_email_set(self) -> set[str]:
        return {x.strip().lower() for x in self.agency_admin_emails.split(",") if x.strip()}

settings = Settings()

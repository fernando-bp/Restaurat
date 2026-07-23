from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    redis_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    bcrypt_rounds: int = 12
    environment: str = "development"
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
    ]
    max_connections_db: int = 20
    food_cost_alert_threshold: float = 35.0
    media_root: Path = PROJECT_ROOT / "data" / "images"
    media_url: str = "/media"
    bold_api_base_url: str = "https://api.online.payments.bold.co"
    bold_api_key: str = ""
    bold_checkout_api_key: str = ""
    bold_checkout_secret_key: str = ""
    bold_webhook_secret: str = ""
    bold_webhook_verify_signature: bool = True
    bold_qr_expiration_minutes: int = 15
    bold_terminal_api_base_url: str = "https://integrations.api.bold.co"
    bold_api_key_sandbox: str = ""
    bold_secret_key_sandbox: str = ""
    bold_api_key_prod: str = ""
    bold_secret_key_prod: str = ""
    bold_terminal_sandbox: bool = True
    bold_terminal_webhook_url: str = ""
    @property
    def bold_terminal_api_key(self) -> str:
        return self.bold_api_key_sandbox if self.bold_terminal_sandbox else self.bold_api_key_prod

    @property
    def bold_terminal_webhook_secret(self) -> str:
        # Bold specifies an empty secret for sandbox webhook signatures.
        return "" if self.bold_terminal_sandbox else self.bold_secret_key_prod
    factus_enabled: bool = True
    factus_api_base_url: str = "https://api-sandbox.factus.com.co"
    factus_timeout_seconds: int = 20
    factus_grant_type: str = "password"
    factus_client_id: str = ""
    factus_client_secret: str = ""
    factus_username: str = ""
    factus_password: str = ""
    factus_numbering_range_id: int = 4
    factus_operation_type: str = "10"
    factus_document_type: str = "01"
    factus_send_email: bool = False
    factus_payment_form: int = 1
    factus_payment_method_code: str = "42"
    factus_customer_legal_organization_code: str = "1"
    factus_customer_municipality_code: str = "68679"

settings = Settings()

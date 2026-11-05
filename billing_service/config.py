import json
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///.local/billing.db"
    payment_provider: Literal["fake", "mercadopago_test"] = "fake"
    catalog_path: Path = Path("config/catalog.demo.json")
    auth_jwt_public_key_b64: str = ""
    quote_valid_minutes: int = 30
    queue_billing_comandos_url: str = ""
    queue_os_saga_respostas_url: str = ""
    aws_region: str = "us-east-1"
    aws_endpoint_url: str | None = None
    mercado_pago_access_token: SecretStr = SecretStr("")
    mercado_pago_webhook_secret: SecretStr = SecretStr("")
    mercado_pago_notification_url: str = ""
    mercado_pago_return_url: str = ""

    @model_validator(mode="after")
    def safety(self):
        if self.quote_valid_minutes <= 0:
            raise ValueError("quote_valid_minutes must be positive")
        if self.app_env == "production" and (
            self.payment_provider == "fake"
            or self.database_url.startswith("sqlite")
            or self.catalog_path.name == "catalog.demo.json"
        ):
            raise ValueError("Production cannot use fake payments, SQLite or the demo catalog")
        if self.payment_provider == "mercadopago_test" and (
            not self.mercado_pago_access_token.get_secret_value()
            or not self.mercado_pago_webhook_secret.get_secret_value()
            or not self.mercado_pago_notification_url.startswith("https://")
            or not self.mercado_pago_return_url.startswith("https://")
        ):
            raise ValueError(
                "Mercado Pago test provider requires credentials and HTTPS callback URLs"
            )
        return self

    def prices(self) -> dict[str, int]:
        data = json.loads(self.catalog_path.read_text())
        if not isinstance(data, dict) or any(
            not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in data.values()
        ):
            raise ValueError("Catalog must map item keys to integer cents")
        return data

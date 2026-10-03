from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Global Treasury AI"
    environment: str = "development"
    database_url: str = "sqlite:///./treasury.db"
    group_reporting_currency: str = "USD"
    auth_mode: str = "demo_header"
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_username_claim: str = "preferred_username"
    production_write_idempotency_required: bool = True
    production_release_id: int | None = None
    max_request_bytes: int = 2097152
    security_headers_enabled: bool = True
    metrics_enabled: bool = True
    cors_origins: str = "http://localhost:3000"
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    secret_provider: str = "UNCONFIGURED"
    execution_signing_key_id: str | None = None
    siem_endpoint: str | None = None
    workload_identity_audience: str | None = None
    integration_mode: str = "sandbox"  # sandbox / uat / production
    integration_timeout_seconds: float = 30.0
    sap_s4_base_url: str | None = None
    sap_s4_token_secret_name: str | None = None
    oracle_fusion_base_url: str | None = None
    oracle_fusion_token_secret_name: str | None = None
    bank_api_base_url: str | None = None
    bank_api_token_secret_name: str | None = None
    market_data_base_url: str | None = None
    market_data_token_secret_name: str | None = None
    live_event_lag_warning_seconds: int = 300
    execution_signing_secret: str | None = None

    # GPT-6 Astra is the requested production reasoning model.
    ai_model_label: str = "GPT-6 Astra"
    ai_model: str = "gpt-6-astra"
    ai_enabled: bool = False
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    ai_timeout_seconds: float = 30.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

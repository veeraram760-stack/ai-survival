from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_file_encoding="utf-8")

    database_url: str = "sqlite+aiosqlite:///./ai_survival.db"
    database_sync_url: str = "sqlite:///./ai_survival.db"
    secret_key: str = "test-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    modal_token_id: str | None = None
    modal_token_secret: str | None = None
    modal_api_key: str | None = None
    modal_api_key_secret: str | None = None
    modal_gpu_types: str = "A10G,A100,H100"
    real_money_only: bool = False
    google_api_key: str | None = None
    google_cloud_api_key: str | None = None
    webhook_publish_url: str | None = None
    amazon_associate_tag: str | None = None
    shareasale_id: str | None = None
    shareasale_token: str | None = None
    cj_affiliate_id: str | None = None
    cj_api_key: str | None = None
    impact_partner_id: str | None = None
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    printful_api_key: str | None = None
    printify_api_key: str | None = None
    printify_shop_id: str | None = None
    gumroad_access_token: str | None = None
    lemonsqueezy_api_key: str | None = None
    lemonsqueezy_store_id: str | None = None
    meta_access_token: str | None = None
    instagram_user_id: str | None = None
    facebook_page_id: str | None = None
    tiktok_access_token: str | None = None
    shopify_access_token: str | None = None
    shopify_store_domain: str | None = None
    gumroad_webhook_secret: str | None = None
    lemonsqueezy_webhook_secret: str | None = None
    meta_webhook_secret: str | None = None
    tiktok_webhook_secret: str | None = None
    shopify_webhook_secret: str | None = None
    paypal_client_id: str | None = None
    paypal_secret: str | None = None
    paypal_mode: str = "sandbox"
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    discord_webhook_url: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    default_notification_email: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_pass: str | None = None
    smtp_from: str | None = None
    smtp_to: str | None = None
    smtp_subject: str = "Partnership Opportunity"
    smtp_tls: bool = True

    openai_api_key: str | None = None
    openai_base_url: str | None = None
    anthropic_api_key: str | None = None
    llm_provider: str = "auto"
    ollama_base_url: str = "http://localhost:11434"
    hf_api_key: str | None = None
    groq_api_key: str | None = None
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    starting_capital: float = 50.0
    survival_reserve_ratio: float = 0.25
    min_operating_capital_ratio: float = 0.10
    max_agent_creation_cost: float = 0.50
    max_clone_cost: float = 0.25
    max_daily_compute_cost: float = 5.0
    max_single_spend: float = 2.0
    reproduction_min_profit: float = 10.0
    reproduction_min_roi: float = 1.5
    reproduction_min_success_rate: float = 0.6
    population_soft_cap: int = 100
    population_hard_cap: int = 1000
    withdrawal_threshold: float = 500.0
    auto_promotion_enabled: bool = False
    auto_promotion_interval_minutes: int = 60
    revenue_cycle_interval_minutes: int = 15

    app_env: str = "development"
    log_level: str = "INFO"

    gcp_project_id: str | None = None
    gcp_region: str = "us-central1"
    gcp_ai_location: str = "us-central1"
    google_application_credentials: str | None = None
    google_cloud_api_key: str | None = None

    twitter_bearer_token: str | None = None
    twitter_api_key: str | None = None
    twitter_api_secret: str | None = None
    linkedin_access_token: str | None = None
    linkedin_person_id: str | None = None


settings = Settings()

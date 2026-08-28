"""
Core application settings loaded from environment variables.
All sensitive values come from .env — never hardcoded.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Smart Portfolio"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "production"
    SECRET_KEY: str = "change_this"
    DEBUG: bool = False
    # وسم النسخة: A للأساسية، B للنسخة الثانية… يظهر في الرقم التسلسلي بتبويب «حول».
    SP_COPY: str = "A"

    # Database
    DATABASE_URL: str = "postgresql://sp_user:password@db:5432/smart_portfolio"

    # AI
    AI_PROVIDER: str = "gemini"
    # "gemini-flash-latest" (the rolling alias, chosen previously to survive
    # model retirements) silently started pointing at "gemini-3.5-flash" —
    # a newer preview model whose free tier is only 20 requests/DAY, not the
    # ~1,500/day a stable Flash release gets. Every AI feature quietly fell
    # back to its rule-based text almost all day, every day, with no visible
    # error (confirmed live: the key itself is valid — a real call returns
    # RESOURCE_EXHAUSTED quota 20/day for that specific model, not an auth
    # error). "gemini-2.5-flash" then also 404'd live ("no longer available
    # to new users" — this account is new). "gemini-3.1-flash-lite" is the
    # current stable (non-preview, non-"-latest") Lite release, confirmed
    # present in this project's real /v1beta/models listing — Lite tiers
    # get a materially higher free-tier RPD than the full-size model of the
    # same generation. Re-verify against aistudio.google.com's rate-limits
    # page occasionally, since even a stable name can eventually retire —
    # just not get silently swapped for a stingier one overnight like the
    # rolling "-latest" alias does.
    AI_MODEL: str = "gemini-3.1-flash-lite"
    AI_API_KEY: Optional[str] = None
    AI_TEMPERATURE: float = 0.3
    AI_MAX_TOKENS: int = 4096
    AI_MEMORY_ENABLED: bool = True
    AI_ANALYSIS_SCHEDULE: str = "daily"

    # Market Data
    PRIMARY_MARKET_PROVIDER: str = "yahoo_finance"
    SECONDARY_MARKET_PROVIDER: str = "sahmak"
    YAHOO_FINANCE_ENABLED: bool = True
    SAHMAK_API_KEY: Optional[str] = None
    SAHMAK_BASE_URL: str = "https://app.sahmk.sa/api/v1"

    # Per-provider daily request caps (free-tier safe; override in .env)
    # Sahmak/Gemini caps mirror a real vendor-enforced free-tier quota — Yahoo
    # doesn't have one (it's an unofficial, undocumented endpoint with no
    # published daily limit), so this is a self-imposed safety valve, not a
    # real vendor cap. Yahoo's actual risk is unofficial-endpoint request-rate
    # blocking, which this count does nothing to prevent by itself; that's
    # instead managed by keeping the market-wide movers scan at an hourly
    # cadence during trading hours (see scheduler.py) rather than a tight
    # 15-min interval, which would risk that block for the whole site.
    YAHOO_DAILY_LIMIT: int = 100_000
    SAHMAK_DAILY_LIMIT: int = 90     # free plan is 100/day — 10 kept as safety buffer
    GEMINI_DAILY_LIMIT: int = 1450  # free tier is 1500/day — 50 kept as safety buffer
    MARKET_UPDATE_INTERVAL_MINUTES: int = 15
    DAILY_API_LIMIT: int = 500

    # Telegram
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    TELEGRAM_BOT_USERNAME: Optional[str] = None

    # Portfolio
    DEFAULT_CURRENCY: str = "SAR"
    DEFAULT_INSTALLMENTS: int = 5
    PORTFOLIO_MODE: str = "BUILD"

    # Backup
    BACKUP_ENABLED: bool = True
    BACKUP_FREQUENCY: str = "daily"
    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_LOCATION: str = "/app/backups"

    # Security
    JWT_SECRET: str = "change_this_jwt_secret"
    # صلاحية الجلسة. الافتراضي ٣٠ يوماً لا يوماً واحداً: إجبار المالك على إدخال
    # كلمته كل صباح لا يمنع مهاجماً (التوكن المسروق يُستعمل خلال دقائق لا أيام)،
    # وإنما يُعوّده على كتابتها مراراً — فتُكتب بسرعةٍ وفي أماكن غير آمنة. وما
    # يُسقط الجلسة حقاً متاحٌ وفوري: تغيير كلمة المرور أو «إنهاء كل الجلسات».
    # قابلة للضبط من .env عبر JWT_EXPIRE_MINUTES.
    JWT_EXPIRE_MINUTES: int = 43200
    APP_PASSWORD: str = "change_this_password"

    # Scheduler
    SCHEDULER_ENABLED: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_ids: tuple[int, ...] = tuple(
        int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
    )
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")
    download_dir: str = os.getenv("DOWNLOAD_DIR", "downloads")
    cookies_file: str = os.getenv("COOKIES_FILE", "")
    max_file_mb: int = _get_int("MAX_FILE_MB", 50)
    dashboard_user: str = os.getenv("DASHBOARD_USER", "admin")
    dashboard_pass: str = os.getenv("DASHBOARD_PASS", "admin123")
    dashboard_port: int = _get_int("DASHBOARD_PORT", 8000)
    default_lang: str = os.getenv("DEFAULT_LANG", "en")


settings = Settings()

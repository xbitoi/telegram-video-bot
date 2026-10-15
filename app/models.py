from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(64), default="")
    lang: Mapped[str] = mapped_column(String(8), default="en")
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    cookies_path: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Download(Base):
    __tablename__ = "downloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    url: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(32), default="unknown")
    file_type: Mapped[str] = mapped_column(String(16), default="video")
    status: Mapped[str] = mapped_column(String(16), default="done")
    file_path: Mapped[str] = mapped_column(Text, default="")
    error_simple: Mapped[str] = mapped_column(String(32), default="")
    error_detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def _migrate_downloads(conn) -> None:
    from sqlalchemy import inspect, text

    tables = set(inspect(conn).get_table_names())
    if "downloads" in tables:
        cols = {c["name"] for c in inspect(conn).get_columns("downloads")}
        if "error_simple" not in cols:
            conn.execute(text("ALTER TABLE downloads ADD COLUMN error_simple VARCHAR(32) DEFAULT ''"))
        if "error_detail" not in cols:
            conn.execute(text("ALTER TABLE downloads ADD COLUMN error_detail TEXT DEFAULT ''"))
    if "users" in tables:
        cols = {c["name"] for c in inspect(conn).get_columns("users")}
        if "cookies_path" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN cookies_path VARCHAR(256) DEFAULT ''"))


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_downloads)
    async with SessionLocal() as s:
        defaults = {"max_file_mb": "50", "welcome_en": "Send me a video link.", "welcome_ar": "ارسل رابط فيديو."}
        for k, v in defaults.items():
            existing = await s.get(Setting, k)
            if existing is None:
                s.add(Setting(key=k, value=v))
        await s.commit()

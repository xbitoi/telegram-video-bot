import asyncio
import os
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urlparse

from app.config import settings


@dataclass
class DownloadResult:
    file_path: str
    title: str
    platform: str


class DownloadError(Exception):
    def __init__(self, kind: str, detail: str):
        super().__init__(detail)
        self.kind = kind
        self.detail = detail


def classify_error(text: str) -> str:
    low = text.lower()
    if "sign in to confirm" in low or "login required" in low or "log in to confirm" in low or "cookies" in low and "sign in" in low:
        return "need_login"
    if "429" in low or "too many requests" in low:
        return "rate_limited"
    if "unsupported url" in low or "no video formats found" in low and "private" not in low:
        return "unsupported"
    if "private video" in low or "login required" in low:
        return "need_login"
    if "file too large" in low or "larger than max" in low:
        return "too_large"
    if "timed out" in low or "network" in low or "connection" in low:
        return "network"
    return "unknown"


def detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    for name in ("youtube", "youtu.be", "instagram", "tiktok", "facebook", "twitter", "x.com"):
        if name in host:
            return name.replace("youtu.be", "youtube").replace("x.com", "twitter")
    return "unknown"


async def resolve_cookies_file() -> str:
    if settings.cookies_file and os.path.exists(settings.cookies_file):
        return settings.cookies_file
    try:
        from app.models import SessionLocal, Setting

        async with SessionLocal() as s:
            row = await s.get(Setting, "cookies_file")
            if row and row.value and os.path.exists(row.value):
                return row.value
    except Exception:
        pass
    return ""


ProgressCb = Callable[[float], Awaitable[None]]
PROGRESS_RE = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%")


async def download_media(
    url: str, kind: str = "video", progress_cb: ProgressCb | None = None, user_cookies: str = ""
) -> DownloadResult:
    os.makedirs(settings.download_dir, exist_ok=True)
    uid = uuid.uuid4().hex[:8]
    out_tpl = os.path.join(settings.download_dir, f"{uid}.%(ext)s")
    if kind == "audio":
        cmd = ["yt-dlp", "--newline", "--no-colors", "--write-info-json", "--no-write-playlist-metafiles",
               "-x", "--audio-format", "mp3", "-o", out_tpl]
    else:
        cmd = ["yt-dlp", "--newline", "--no-colors", "--write-info-json", "--no-write-playlist-metafiles",
               "-f", "mp4/best[ext=mp4]/best", "-o", out_tpl]
    cookies = user_cookies if user_cookies and os.path.exists(user_cookies) else await resolve_cookies_file()
    if cookies:
        cmd += ["--cookies", cookies]
    cmd.append(url)
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    tail: list[str] = []
    last_pct = -1.0
    try:
        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode("utf-8", "ignore").strip()
            if not line:
                continue
            tail.append(line)
            if len(tail) > 30:
                tail.pop(0)
            m = PROGRESS_RE.search(line)
            if m and progress_cb is not None:
                try:
                    pct = float(m.group(1))
                except ValueError:
                    continue
                if pct - last_pct >= 1.0:
                    last_pct = pct
                    await progress_cb(pct)
        await proc.wait()
    except asyncio.CancelledError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        raise
    if proc.returncode != 0:
        text = "\n".join(tail[-12:])
        raise DownloadError(classify_error(text), text or "download failed")
    for f in os.listdir(settings.download_dir):
        if f.startswith(uid) and not f.endswith(".info.json"):
            path = os.path.join(settings.download_dir, f)
            return DownloadResult(file_path=path, title=read_info_title(uid) or f, platform=detect_platform(url))
    raise DownloadError("unknown", "yt-dlp finished but no file found")


def read_info_title(uid: str) -> str:
    import json

    info_path = os.path.join(settings.download_dir, f"{uid}.info.json")
    try:
        with open(info_path, encoding="utf-8") as fh:
            info = json.load(fh)
        title = str(info.get("title") or "").strip()
        return title[:200]
    except (OSError, ValueError):
        return ""
    finally:
        try:
            os.remove(info_path)
        except OSError:
            pass

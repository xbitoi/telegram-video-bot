"""Single-window runner: live console log + file log for the Telegram bot."""
import asyncio
import logging
import sys
from pathlib import Path

Path("logs").mkdir(exist_ok=True)

root = logging.getLogger()
root.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(message)s")
fh = logging.FileHandler("logs/bot-live.log", encoding="utf-8")
fh.setFormatter(fmt)
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(fmt)
root.addHandler(fh)
root.addHandler(sh)

from app.bot import main  # noqa: E402

asyncio.run(main())

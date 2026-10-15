import asyncio
import logging
import os
import time

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import BotCommand, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup
from sqlalchemy import func, select

from app.config import settings
from app.downloader import DownloadError, detect_platform, download_media
from app.models import Download, SessionLocal, User, init_db

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

TEXTS = {
    "en": {
        "welcome": "🎬 Send me a video link (YouTube/Instagram/TikTok). Use the quick buttons below ⬇️ or the inline buttons to choose 🎬 video or 🎵 audio.",
        "help": "🎬 Send any video link and I will download it for you.\n\nCommands:\n/start - start\n/lang - switch language (EN/AR/RU/FR/ES/ZH)\n/audio - download as 🎵 MP3\n/video - download as 🎬 MP4\n/mystats - 📊 my downloads\n/cancel - ✖ stop current download\n/mycookies - 🔑 check your saved login\n/forgetcookies - 🗑 delete your saved login",
        "downloading": "⏳ Downloading, please wait...",
        "failed": "❌ Download failed: ",
        "need_link": "🔗 Please send a video link starting with http:// or https://",
        "blocked": "⛔ You are blocked. Contact support.",
        "mode_set": "✅ Mode set: ",
        "video": "🎬 Video",
        "audio": "🎵 Audio",
        "quick_video": "🎬 Video",
        "quick_audio": "🎵 Audio",
        "quick_lang": "🌍 EN/AR",
        "quick_stats": "📊 My stats",
        "quick_help": "❓ Help",
        "choose": "Choose an action:",
    },
    "ar": {
        "welcome": "🎬 ارسل رابط فيديو (يوتيوب/انستغرام/تيك توك). استخدم الازرار السريعة بالاسفل ⬇️ او الازرار المرفقة لاختيار 🎬 فيديو او 🎵 صوت.",
        "help": "🎬 ارسل اي رابط فيديو وساحمله لك.\n\nالاوامر:\n/start - بدء\n/lang - تبديل اللغة (EN/AR/RU/FR/ES/ZH)\n/audio - تحميل 🎵 MP3\n/video - تحميل 🎬 MP4\n/mystats - 📊 تحميلاتي\n/cancel - ✖ ايقاف التحميل الجاري\n/mycookies - 🔑 فحص تسجيل الدخول المحفوظ\n/forgetcookies - 🗑 حذف تسجيل الدخول المحفوظ",
        "downloading": "⏳ جاري التحميل، انتظر...",
        "failed": "❌ فشل التحميل: ",
        "need_link": "🔗 ارسل رابط فيديو يبدا بـ http:// او https://",
        "blocked": "⛔ تم حظرك. تواصل مع الدعم.",
        "mode_set": "✅ تم ضبط الوضع: ",
        "video": "🎬 فيديو",
        "audio": "🎵 صوت",
        "quick_video": "🎬 فيديو",
        "quick_audio": "🎵 صوت",
        "quick_lang": "🌍 عربي/EN",
        "quick_stats": "📊 احصائياتي",
        "quick_help": "❓ مساعدة",
        "choose": "اختر اجراء:",
    },
    "ru": {
        "welcome": "🎬 Пришлите ссылку на видео (YouTube/Instagram/TikTok). Используйте быстрые кнопки ниже ⬇️ или встроенные кнопки, чтобы выбрать 🎬 видео или 🎵 аудио.",
        "help": "🎬 Пришлите любую ссылку на видео, и я скачаю его для вас.\n\nКоманды:\n/start - старт\n/lang - сменить язык\n/audio - скачать как 🎵 MP3\n/video - скачать как 🎬 MP4\n/mystats - 📊 моя статистика\n/cancel - ✖ остановить загрузку\n/mycookies - 🔑 проверить сохранённый вход\n/forgetcookies - 🗑 удалить сохранённый вход",
        "downloading": "⏳ Скачиваю, подождите...",
        "failed": "❌ Ошибка скачивания: ",
        "need_link": "🔗 Пришлите ссылку на видео, начинающуюся с http:// или https://",
        "blocked": "⛔ Вы заблокированы. Обратитесь в поддержку.",
        "mode_set": "✅ Режим установлен: ",
        "video": "🎬 Видео",
        "audio": "🎵 Аудио",
        "quick_video": "🎬 Видео",
        "quick_audio": "🎵 Аудио",
        "quick_lang": "🌍 Язык",
        "quick_stats": "📊 Статистика",
        "quick_help": "❓ Помощь",
        "choose": "Выберите действие:",
    },
    "fr": {
        "welcome": "🎬 Envoyez-moi un lien vidéo (YouTube/Instagram/TikTok). Utilisez les boutons rapides ci-dessous ⬇️ ou les boutons intégrés pour choisir 🎬 vidéo ou 🎵 audio.",
        "help": "🎬 Envoyez n'importe quel lien vidéo et je le téléchargerai pour vous.\n\nCommandes :\n/start - démarrer\n/lang - changer de langue\n/audio - télécharger en 🎵 MP3\n/video - télécharger en 🎬 MP4\n/mystats - 📊 mes statistiques\n/cancel - ✖ arrêter le téléchargement\n/mycookies - 🔑 vérifier la connexion enregistrée\n/forgetcookies - 🗑 supprimer la connexion enregistrée",
        "downloading": "⏳ Téléchargement en cours, patientez...",
        "failed": "❌ Échec du téléchargement : ",
        "need_link": "🔗 Veuillez envoyer un lien vidéo commençant par http:// ou https://",
        "blocked": "⛔ Vous êtes bloqué. Contactez le support.",
        "mode_set": "✅ Mode défini : ",
        "video": "🎬 Vidéo",
        "audio": "🎵 Audio",
        "quick_video": "🎬 Vidéo",
        "quick_audio": "🎵 Audio",
        "quick_lang": "🌍 Langue",
        "quick_stats": "📊 Mes stats",
        "quick_help": "❓ Aide",
        "choose": "Choisissez une action :",
    },
    "es": {
        "welcome": "🎬 Envíame un enlace de video (YouTube/Instagram/TikTok). Usa los botones rápidos de abajo ⬇️ o los botones integrados para elegir 🎬 video o 🎵 audio.",
        "help": "🎬 Envía cualquier enlace de video y lo descargaré por ti.\n\nComandos:\n/start - iniciar\n/lang - cambiar idioma\n/audio - descargar como 🎵 MP3\n/video - descargar como 🎬 MP4\n/mystats - 📊 mis estadísticas\n/cancel - ✖ detener la descarga\n/mycookies - 🔑 ver el inicio de sesión guardado\n/forgetcookies - 🗑 eliminar el inicio de sesión guardado",
        "downloading": "⏳ Descargando, espera...",
        "failed": "❌ Error al descargar: ",
        "need_link": "🔗 Envía un enlace de video que comience con http:// o https://",
        "blocked": "⛔ Estás bloqueado. Contacta con soporte.",
        "mode_set": "✅ Modo establecido: ",
        "video": "🎬 Video",
        "audio": "🎵 Audio",
        "quick_video": "🎬 Video",
        "quick_audio": "🎵 Audio",
        "quick_lang": "🌍 Idioma",
        "quick_stats": "📊 Mis stats",
        "quick_help": "❓ Ayuda",
        "choose": "Elige una acción:",
    },
    "zh": {
        "welcome": "🎬 请发送视频链接（YouTube/Instagram/TikTok）。使用下方的快捷按钮 ⬇️ 或内联按钮选择 🎬 视频或 🎵 音频。",
        "help": "🎬 发送任何视频链接，我会帮你下载。\n\n命令：\n/start - 开始\n/lang - 切换语言\n/audio - 下载为 🎵 MP3\n/video - 下载为 🎬 MP4\n/mystats - 📊 我的统计\n/cancel - ✖ 停止下载\n/mycookies - 🔑 查看已保存的登录\n/forgetcookies - 🗑 删除已保存的登录",
        "downloading": "⏳ 正在下载，请稍候...",
        "failed": "❌ 下载失败：",
        "need_link": "🔗 请发送以 http:// 或 https:// 开头的视频链接",
        "blocked": "⛔ 你已被屏蔽，请联系支持。",
        "mode_set": "✅ 已设置模式：",
        "video": "🎬 视频",
        "audio": "🎵 音频",
        "quick_video": "🎬 视频",
        "quick_audio": "🎵 音频",
        "quick_lang": "🌍 语言",
        "quick_stats": "📊 我的统计",
        "quick_help": "❓ 帮助",
        "choose": "请选择操作：",
    },
}

LANGS = ["en", "ar", "ru", "fr", "es", "zh"]

LANG_NAMES = {"en": "🇬🇧 English", "ar": "🇸🇦 عربي", "ru": "🇷🇺 Русский",
              "fr": "🇫🇷 Français", "es": "🇪🇸 Español", "zh": "🇨🇳 中文"}

LANG_PICK = {"en": "🌍 Choose your language:", "ar": "🌍 اختر لغتك:",
             "ru": "🌍 Выберите язык:", "fr": "🌍 Choisissez votre langue:",
             "es": "🌍 Elige tu idioma:", "zh": "🌍 请选择语言："}


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=LANG_NAMES[c], callback_data=f"lang:{c}")] for c in LANGS]
    )

dp = Dispatcher()
user_mode: dict[int, str] = {}
active_tasks: dict[int, "asyncio.Task"] = {}


def progress_bar(pct: float, label: str) -> str:
    filled = max(0, min(10, int(pct // 10)))
    return f"{label}\n{'▓' * filled}{'░' * (10 - filled)} {pct:.0f}%"


def cancel_kb(lang: str) -> InlineKeyboardMarkup:
    txt = {"en": "✖ Cancel", "ar": "✖ الغاء", "ru": "✖ Отмена", "fr": "✖ Annuler", "es": "✖ Cancelar", "zh": "✖ 取消"}.get(lang, "✖ Cancel")
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=txt, callback_data="op:cancel")]])


async def notify_admins(bot, text: str) -> None:
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text[:1000])
        except Exception:
            pass

SIMPLE_ERRORS = {
    "en": {
        "need_login": "❌ This {platform} link needs a logged-in account to watch. Good news: you can use YOUR OWN YouTube account — just send me your cookies file 🔑 (export it with the free 'Get cookies.txt LOCALLY' browser extension while logged in on youtube.com, then send the .txt file here) and send the link again. Or try a public link.",
        "rate_limited": "❌ {platform} is busy right now (too many requests). ⏳ Please wait about 10 minutes and try again.",
        "unsupported": "❌ This link has no downloadable video. 🔗 Check that the link opens and plays in your browser, then try again.",
        "too_large": "❌ This file is bigger than the {limit}MB limit. 🎵 Try audio mode instead (/audio).",
        "network": "❌ Network problem reaching {platform}. 📡 Try again in a few minutes.",
        "unknown": "❌ Something went wrong with this {platform} link. 🔁 Try another link or try again later.",
    },
    "ar": {
        "need_login": "❌ رابط {platform} يحتاج حسابا مسجلا للمشاهدة. والخبر الطيب: يمكنك استعمال حساب يوتيوب الخاص بك 🔑 — ارسل لي ملف الكوكيز (صدّره باضافة 'Get cookies.txt LOCALLY' المجانية وانت مسجل في youtube.com، ثم ارسل ملف .txt هنا) واعد ارسال الرابط. او جرب رابطا عاما.",
        "rate_limited": "❌ موقع {platform} مشغول الان (طلبات كثيرة). ⏳ انتظر حوالي 10 دقائق وحاول مجددا.",
        "unsupported": "❌ هذا الرابط لا يحوي فيديو قابلا للتحميل. 🔗 تاكد ان الرابط يعمل في متصفحك ثم حاول مجددا.",
        "too_large": "❌ الملف اكبر من حد {limit}MB. 🎵 جرب وضع الصوت (/audio).",
        "network": "❌ مشكلة شبكة في الوصول الى {platform}. 📡 حاول بعد دقائق.",
        "unknown": "❌ حدث خطا مع رابط {platform}. 🔁 جرب رابطا اخر او حاول لاحقا.",
    },
    "ru": {
        "need_login": "❌ Для этой ссылки {platform} нужен вход в аккаунт. Хорошая новость: можно использовать СВОЙ аккаунт YouTube 🔑 — пришлите мне файл cookies (расширение 'Get cookies.txt LOCALLY', будучи залогиненным на youtube.com, затем отправьте .txt сюда) и пришлите ссылку снова. Или попробуйте публичную ссылку.",
        "rate_limited": "❌ {platform} сейчас перегружен (слишком много запросов). ⏳ Подождите около 10 минут и попробуйте снова.",
        "unsupported": "❌ В этой ссылке нет скачиваемого видео. 🔗 Проверьте, что ссылка открывается в браузере, и попробуйте снова.",
        "too_large": "❌ Файл больше лимита {limit}MB. 🎵 Попробуйте аудио-режим (/audio).",
        "network": "❌ Проблема сети с {platform}. 📡 Попробуйте через несколько минут.",
        "unknown": "❌ Что-то пошло не так с этой ссылкой {platform}. 🔁 Попробуйте другую ссылку или позже.",
    },
    "fr": {
        "need_login": "❌ Ce lien {platform} nécessite un compte connecté. Bonne nouvelle : vous pouvez utiliser VOTRE propre compte YouTube 🔑 — envoyez-moi votre fichier cookies (extension 'Get cookies.txt LOCALLY' en étant connecté sur youtube.com, puis envoyez le .txt ici) et renvoyez le lien. Ou essayez un lien public.",
        "rate_limited": "❌ {platform} est surchargé (trop de requêtes). ⏳ Attendez environ 10 minutes et réessayez.",
        "unsupported": "❌ Ce lien ne contient pas de vidéo téléchargeable. 🔗 Vérifiez qu'il s'ouvre dans votre navigateur, puis réessayez.",
        "too_large": "❌ Fichier plus grand que la limite de {limit}MB. 🎵 Essayez le mode audio (/audio).",
        "network": "❌ Problème réseau avec {platform}. 📡 Réessayez dans quelques minutes.",
        "unknown": "❌ Un problème est survenu avec ce lien {platform}. 🔁 Essayez un autre lien ou réessayez plus tard.",
    },
    "es": {
        "need_login": "❌ Este enlace de {platform} necesita una cuenta iniciada. Buenas noticias: puedes usar TU propia cuenta de YouTube 🔑 — envíame tu archivo de cookies (extensión 'Get cookies.txt LOCALLY' con sesión iniciada en youtube.com, luego envía el .txt aquí) y vuelve a enviar el enlace. O prueba con un enlace público.",
        "rate_limited": "❌ {platform} está saturado (demasiadas solicitudes). ⏳ Espera unos 10 minutos e inténtalo de nuevo.",
        "unsupported": "❌ Este enlace no contiene un video descargable. 🔗 Comprueba que se abra en tu navegador e inténtalo de nuevo.",
        "too_large": "❌ El archivo supera el límite de {limit}MB. 🎵 Prueba el modo de audio (/audio).",
        "network": "❌ Problema de red con {platform}. 📡 Inténtalo en unos minutos.",
        "unknown": "❌ Algo salió mal con este enlace de {platform}. 🔁 Prueba con otro enlace o más tarde.",
    },
    "zh": {
        "need_login": "❌ 此 {platform} 链接需要登录帐户。好消息：你可以使用自己的 YouTube 帐户 🔑——把 cookies 文件发给我（在已登录 youtube.com 时用 'Get cookies.txt LOCALLY' 扩展导出，再把 .txt 发到这里），然后重新发送链接。或尝试公开链接。",
        "rate_limited": "❌ {platform} 目前繁忙（请求过多）。⏳ 请等待约 10 分钟后重试。",
        "unsupported": "❌ 此链接没有可下载的视频。🔗 请确认链接能在浏览器中打开，然后重试。",
        "too_large": "❌ 文件超过 {limit}MB 限制。🎵 请尝试音频模式（/audio）。",
        "network": "❌ 连接 {platform} 时出现网络问题。📡 请几分钟后再试。",
        "unknown": "❌ 此 {platform} 链接出现问题。🔁 请尝试其他链接或稍后再试。",
    },
}


def get_lang(message: Message) -> str:
    code = (message.from_user and message.from_user.language_code or "").lower()
    for lang in ("ar", "ru", "fr", "es", "zh"):
        if code.startswith(lang):
            return lang
    return "en"


def main_kb(lang: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t["video"], callback_data="mode:video"),
             InlineKeyboardButton(text=t["audio"], callback_data="mode:audio")]
        ]
    )


async def get_or_create_user(tg_id: int, username: str, lang: str) -> User:
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.telegram_id == tg_id))
        u = res.scalar_one_or_none()
        if u is None:
            u = User(telegram_id=tg_id, username=username or "", lang=lang)
            s.add(u)
            await s.commit()
            await s.refresh(u)
        return u


async def resolve_lang(tg_id: int, fallback: str) -> str:
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.telegram_id == tg_id))
        u = res.scalar_one_or_none()
        if u and u.lang in LANGS:
            return u.lang
    return fallback


def quick_kb(lang: str) -> ReplyKeyboardMarkup:
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t["quick_video"]), KeyboardButton(text=t["quick_audio"])],
            [KeyboardButton(text=t["quick_stats"]), KeyboardButton(text=t["quick_help"])],
            [KeyboardButton(text=t["quick_lang"])],
        ],
        resize_keyboard=True,
        persistent=True,
    )


QUICK_VIDEO = {"🎬 Video", "🎬 فيديو", "🎬 Видео", "🎬 Vidéo", "🎬 视频"}
QUICK_AUDIO = {"🎵 Audio", "🎵 صوت", "🎵 Аудио", "🎵 音频"}
QUICK_STATS = {"📊 My stats", "📊 احصائياتي", "📊 Статистика", "📊 Mes stats", "📊 Mis stats", "📊 我的统计"}
QUICK_HELP = {"❓ Help", "❓ مساعدة", "❓ Помощь", "❓ Aide", "❓ Ayuda", "❓ 帮助"}
QUICK_LANG = {"🌍 EN/AR", "🌍 عربي/EN", "🌍 Язык", "🌍 Langue", "🌍 Idioma", "🌍 语言"}


@dp.message(Command("start", "help"))
async def cmd_start(message: Message):
    lang = get_lang(message)
    user = await get_or_create_user(message.from_user.id, message.from_user.username or "", lang)
    lang = user.lang
    t = TEXTS[lang]
    await message.answer(t["welcome"], reply_markup=main_kb(lang))
    await message.answer(t["choose"], reply_markup=quick_kb(lang))


@dp.message(Command("lang"))
async def cmd_lang(message: Message):
    lang = await resolve_lang(message.from_user.id, get_lang(message))
    await message.answer(LANG_PICK.get(lang, LANG_PICK["en"]), reply_markup=lang_kb())


@dp.callback_query(F.data.startswith("lang:"))
async def cb_lang(callback):
    code = (callback.data.split(":")[1] if ":" in callback.data else "")
    if code not in LANGS:
        await callback.answer()
        return
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.telegram_id == callback.from_user.id))
        u = res.scalar_one_or_none()
        if u is None:
            u = User(telegram_id=callback.from_user.id, username=callback.from_user.username or "", lang=code)
            s.add(u)
        else:
            u.lang = code
        await s.commit()
    try:
        await callback.message.edit_text("✅ " + LANG_NAMES[code])
    except Exception:
        pass
    await callback.message.answer(TEXTS[code]["choose"], reply_markup=quick_kb(code))
    await callback.answer("✅ " + LANG_NAMES[code])


@dp.message(Command("audio", "video"))
async def cmd_mode(message: Message):
    mode = message.text.lstrip("/").split()[0]
    user_mode[message.from_user.id] = mode
    lang = await resolve_lang(message.from_user.id, get_lang(message))
    icon = "🎬" if mode == "video" else "🎵"
    await message.answer(f"{icon} " + TEXTS[lang]["mode_set"] + mode, reply_markup=quick_kb(lang))


@dp.message(F.text.in_(QUICK_VIDEO | QUICK_AUDIO))
async def quick_mode(message: Message):
    mode = "video" if message.text in QUICK_VIDEO else "audio"
    user_mode[message.from_user.id] = mode
    lang = await resolve_lang(message.from_user.id, get_lang(message))
    icon = "🎬" if mode == "video" else "🎵"
    await message.answer(f"{icon} " + TEXTS[lang]["mode_set"] + mode, reply_markup=quick_kb(lang))


@dp.message(F.text.in_(QUICK_LANG))
async def quick_lang(message: Message):
    await cmd_lang(message)


@dp.message(F.text.in_(QUICK_STATS))
async def quick_stats(message: Message):
    await cmd_stats(message)


@dp.message(F.text.in_(QUICK_HELP))
async def quick_help(message: Message):
    lang = await resolve_lang(message.from_user.id, get_lang(message))
    await message.answer(TEXTS[lang]["help"], reply_markup=quick_kb(lang))


@dp.message(Command("mystats"))
async def cmd_stats(message: Message):
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.telegram_id == message.from_user.id))
        u = res.scalar_one_or_none()
        if not u:
            await message.answer("0")
            return
        c = await s.execute(select(func.count(Download.id)).where(Download.user_id == u.id))
        n = c.scalar()
        lang = u.lang if u.lang in LANGS else "en"
        label = {"en": "📊 Downloads", "ar": "📊 التحميلات", "ru": "📊 Скачивания", "fr": "📊 Téléchargements", "es": "📊 Descargas", "zh": "📊 下载"}.get(lang, "📊 Downloads")
        await message.answer(f"{label}: {n}")


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in settings.admin_ids:
        return
    async with SessionLocal() as s:
        uc = (await s.execute(select(func.count(User.id)))).scalar()
        dc = (await s.execute(select(func.count(Download.id)))).scalar()
    await message.answer(f"Users: {uc}\nDownloads: {dc}")


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message):
    task = active_tasks.get(message.from_user.id)
    if task is None or task.done():
        lang = await resolve_lang(message.from_user.id, get_lang(message))
        txt = {"en": "No active operation.", "ar": "لا توجد عملية جارية.", "ru": "Нет активной операции.",
               "fr": "Aucune opération en cours.", "es": "No hay ninguna operación activa.", "zh": "当前没有正在进行的操作。"}.get(lang, "No active operation.")
        await message.answer(txt)
        return
    task.cancel()


@dp.callback_query(F.data == "op:cancel")
async def cb_cancel(callback):
    task = active_tasks.get(callback.from_user.id)
    if task is None or task.done():
        await callback.answer("Nothing to cancel.")
        return
    task.cancel()
    await callback.answer("Cancelling...")


@dp.callback_query(F.data.startswith("mode:"))
async def cb_mode(callback):
    user_mode[callback.from_user.id] = callback.data.split(":")[1]
    await callback.answer(f"OK: {user_mode[callback.from_user.id]}")


@dp.message(F.text.regexp(r"https?://"))
async def handle_url(message: Message):
    url = message.text.strip()
    mode = user_mode.get(message.from_user.id, "video")
    lang = get_lang(message)
    user = await get_or_create_user(message.from_user.id, message.from_user.username or "", lang)
    lang = user.lang
    if user.is_blocked:
        await message.answer(TEXTS[lang]["blocked"], reply_markup=quick_kb(lang))
        return
    old = active_tasks.get(message.from_user.id)
    if old is not None and not old.done():
        await message.answer(
            "Finish or /cancel the current download first." if lang == "en" else "انه اولا التحميل الجاري او ارسل /cancel.",
            reply_markup=quick_kb(lang),
        )
        return
    status = await message.answer(
        progress_bar(0, TEXTS[lang]["downloading"]), reply_markup=cancel_kb(lang)
    )
    active_tasks[message.from_user.id] = asyncio.current_task()  # type: ignore[assignment]
    last_edit = [0.0]

    async def on_progress(pct: float) -> None:
        now = time.monotonic()
        if now - last_edit[0] < 3.0 and pct < 100:
            return
        last_edit[0] = now
        try:
            await status.edit_text(progress_bar(pct, TEXTS[lang]["downloading"]), reply_markup=cancel_kb(lang))
        except Exception:
            pass

    try:
        res = await download_media(url, mode, on_progress, user_cookies=user.cookies_path or "")
        async with SessionLocal() as s:
            s.add(Download(user_id=user.id, url=url, platform=detect_platform(url), file_type=mode, status="done", file_path=res.file_path))
            await s.commit()
        try:
            await message.answer_document(FSInputFile(res.file_path), caption=res.title[:200])
        except Exception as e:
            log.exception("send file failed")
            await message.answer(
                SIMPLE_ERRORS[lang]["too_large"].format(platform=detect_platform(url), limit="50"),
                reply_markup=quick_kb(lang),
            )
            await notify_admins(message.bot, f"⚠ Send file failed\nuser={message.from_user.id}\nurl={url[:200]}\n{str(e)[:400]}")
        try:
            os.remove(res.file_path)
        except OSError:
            pass
    except asyncio.CancelledError:
        async with SessionLocal() as s:
            s.add(Download(user_id=user.id, url=url, platform=detect_platform(url), file_type=mode, status="cancelled", error_simple="cancelled", error_detail="cancelled by user"))
            await s.commit()
        cancelled_txt = "Cancelled ✖" if lang == "en" else "تم الالغاء ✖"
        try:
            await status.edit_text(cancelled_txt)
        except Exception:
            await message.answer(cancelled_txt)
        await message.answer(TEXTS[lang]["choose"], reply_markup=quick_kb(lang))
        return
    except DownloadError as e:
        log.warning("download failed kind=%s url=%s", e.kind, url)
        async with SessionLocal() as s:
            s.add(Download(user_id=user.id, url=url, platform=detect_platform(url), file_type=mode, status="failed", error_simple=e.kind, error_detail=e.detail[:1000]))
            await s.commit()
        limit = "50"
        simple = SIMPLE_ERRORS[lang].get(e.kind, SIMPLE_ERRORS[lang]["unknown"])
        simple_txt = simple.format(platform=detect_platform(url), limit=limit)
        try:
            await status.edit_text(simple_txt)
        except Exception:
            log.exception("status edit failed, sending as new message")
            await message.answer(simple_txt)
        await message.answer(TEXTS[lang]["choose"], reply_markup=quick_kb(lang))
        await notify_admins(
            message.bot,
            f"⚠ Download failed [{e.kind}] on {detect_platform(url)}\nuser={message.from_user.id} @{message.from_user.username}\nurl={url[:200]}\n{e.detail[:500]}",
        )
    except Exception as e:
        log.exception("download failed")
        async with SessionLocal() as s:
            s.add(Download(user_id=user.id, url=url, platform=detect_platform(url), file_type=mode, status="failed", error_simple="unknown", error_detail=str(e)[:1000]))
            await s.commit()
        simple_txt = SIMPLE_ERRORS[lang]["unknown"].format(platform=detect_platform(url))
        try:
            await status.edit_text(simple_txt)
        except Exception:
            await message.answer(simple_txt)
        await message.answer(TEXTS[lang]["choose"], reply_markup=quick_kb(lang))
        await notify_admins(
            message.bot,
            f"⚠ Download crashed on {detect_platform(url)}\nuser={message.from_user.id}\nurl={url[:200]}\n{str(e)[:500]}",
        )
    else:
        try:
            await status.delete()
        except Exception:
            pass
    finally:
        active_tasks.pop(message.from_user.id, None)


@dp.message(Command("mycookies"))
async def cmd_mycookies(message: Message):
    lang = await resolve_lang(message.from_user.id, get_lang(message))
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.telegram_id == message.from_user.id))
        u = res.scalar_one_or_none()
        has = bool(u and u.cookies_path and os.path.exists(u.cookies_path))
    if has:
        txt = "🔑 Your YouTube login is saved and active.\n🔑 تسجيل دخول يوتيوب محفوظ ويعمل."
    else:
        txt = (
            "🔑 No login saved.\n"
            "EN: Install 'Get cookies.txt LOCALLY', open youtube.com logged in, export cookies.txt, and send the file here.\n"
            "AR: ثبت اضافة Get cookies.txt LOCALLY وافتح youtube.com مسجلا، ثم صدر cookies.txt وارسله هنا."
        )
    await message.answer(txt, reply_markup=quick_kb(lang))


@dp.message(Command("forgetcookies"))
async def cmd_forgetcookies(message: Message):
    lang = await resolve_lang(message.from_user.id, get_lang(message))
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.telegram_id == message.from_user.id))
        u = res.scalar_one_or_none()
        if u and u.cookies_path:
            try:
                os.remove(u.cookies_path)
            except OSError:
                pass
            u.cookies_path = ""
            await s.commit()
    await message.answer("Login deleted." if lang == "en" else "تم حذف تسجيل الدخول.", reply_markup=quick_kb(lang))


@dp.message(F.document)
async def handle_cookies_file(message: Message):
    lang = await resolve_lang(message.from_user.id, get_lang(message))
    doc = message.document
    if not doc or not (doc.file_name or "").endswith(".txt") or (doc.file_size or 0) > 300_000:
        await message.answer(TEXTS[lang]["need_link"], reply_markup=quick_kb(lang))
        return
    user = await get_or_create_user(message.from_user.id, message.from_user.username or "", lang)
    path = os.path.join(settings.download_dir, f"cookies_{message.from_user.id}.txt")
    os.makedirs(settings.download_dir, exist_ok=True)
    try:
        tg_file = await message.bot.get_file(doc.file_id)
        await message.bot.download_file(tg_file.file_path or "", destination=path)
    except Exception:
        log.exception("cookies download failed")
        await message.answer(TEXTS[lang]["failed"] + "cookies", reply_markup=quick_kb(lang))
        return
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            head = f.read(2000).lower()
    except OSError:
        head = ""
    if "youtube.com" not in head and "netscape" not in head:
        try:
            os.remove(path)
        except OSError:
            pass
        await message.answer(
            "❌ This file does not look like a YouTube cookies export.\n❌ هذا الملف لا يبدو كوكيز يوتيوب.\nEN: Export it from youtube.com while logged in.\nAR: صدّره من youtube.com وانت مسجل الدخول.",
            reply_markup=quick_kb(lang),
        )
        return
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.telegram_id == message.from_user.id))
        u = res.scalar_one_or_none()
        if u:
            u.cookies_path = path
            await s.commit()
    await message.answer(
        "✅ Login saved! Send the YouTube link again and it will download with your account.\n✅ تم حفظ تسجيل الدخول! ارسل رابط يوتيوب مجددا وسيحمل بحسابك.",
        reply_markup=quick_kb(lang),
    )


@dp.message()
async def fallback(message: Message):
    lang = await resolve_lang(message.from_user.id, get_lang(message))
    await get_or_create_user(message.from_user.id, message.from_user.username or "", lang)
    await message.answer(TEXTS[lang]["need_link"] + "\n\n" + TEXTS[lang]["help"], reply_markup=quick_kb(lang))


async def resolve_token() -> str:
    token = settings.bot_token
    if token and token != "put_telegram_bot_token_here":
        return token
    try:
        from app.models import Setting as SettingRow

        async with SessionLocal() as s:
            row = await s.get(SettingRow, "bot_token")
            if row and row.value and ":" in row.value:
                return row.value
    except Exception:
        pass
    return ""


async def main():
    await init_db()
    token = await resolve_token()
    if not token:
        raise RuntimeError("BOT_TOKEN missing: set it in .env or dashboard /token/save")
    from pathlib import Path as _Path

    pid_file = _Path(__file__).resolve().parent.parent / "bot.pid"
    try:
        pid_file.write_text(str(os.getpid()), encoding="utf-8")
    except OSError:
        pass
    bot = Bot(token=token)
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="help", description="Show help"),
            BotCommand(command="lang", description="Switch language"),
            BotCommand(command="video", description="Download as MP4 video"),
            BotCommand(command="audio", description="Download as MP3 audio"),
            BotCommand(command="mystats", description="My download stats"),
            BotCommand(command="mycookies", description="Check saved login"),
            BotCommand(command="forgetcookies", description="Delete saved login"),
            BotCommand(command="cancel", description="Stop current download"),
        ]
    )
    await dp.start_polling(bot)
    try:
        pid_file.unlink()
    except OSError:
        pass


if __name__ == "__main__":
    asyncio.run(main())

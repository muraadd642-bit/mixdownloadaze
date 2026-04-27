import os
import logging
import threading
import zipfile
import shutil
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 *MixDrop Bot-a xoş gəldin!*\n\n"
        "YouTube playlist və ya mix linkini göndər, mən MP3 formatında yükləyib sənə göndərim!\n\n"
        "⚠️ Böyük playlist-lər bir az vaxt ala bilər, gözlə.",
        parse_mode="Markdown"
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    chat_id = update.message.chat_id

    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("❌ Zəhmət olmasa YouTube linki göndər.")
        return

    await update.message.reply_text("⏳ Yüklənir... Gözlə, bu bir az vaxt ala bilər.")

    def download_and_send():
        import asyncio
        import yt_dlp

        session_path = os.path.join(DOWNLOAD_DIR, str(chat_id))
        os.makedirs(session_path, exist_ok=True)

        cookies_path = "cookies.txt" if os.path.exists("cookies.txt") else None

        ydl_opts = {
            'outtmpl': os.path.join(session_path, '%(playlist_index)s - %(title)s.%(ext)s'),
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'ignoreerrors': True,
            'quiet': True,
            'no_warnings': True,
        }

        if cookies_path:
            ydl_opts['cookiefile'] = cookies_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    total = len([e for e in info['entries'] if e])
                else:
                    total = 1

                asyncio.run(context.bot.send_message(
                    chat_id=chat_id,
                    text=f"📋 Toplam {total} mahnı tapıldı. Yüklənir..."
                ))

                ydl.download([url])

            # ZIP yarat
            zip_path = os.path.join(DOWNLOAD_DIR, f"{chat_id}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for fname in os.listdir(session_path):
                    fpath = os.path.join(session_path, fname)
                    zf.write(fpath, fname)

            shutil.rmtree(session_path)

            # ZIP göndər
            zip_size = os.path.getsize(zip_path) / (1024 * 1024)

            if zip_size > 50:
                asyncio.run(context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ Fayl çox böyükdür ({zip_size:.1f} MB). Telegram 50MB-dan böyük fayl qəbul etmir.\n"
                         "Daha kiçik playlist cəhd et."
                ))
            else:
                asyncio.run(context.bot.send_message(
                    chat_id=chat_id,
                    text="✅ Hazırdır! ZIP göndərilir..."
                ))
                with open(zip_path, 'rb') as f:
                    asyncio.run(context.bot.send_document(
                        chat_id=chat_id,
                        document=f,
                        filename="playlist.zip",
                        caption=f"🎵 {total} mahnı — MixDrop Bot"
                    ))

            os.remove(zip_path)

        except Exception as e:
            logger.error(f"Xəta: {e}")
            asyncio.run(context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Xəta baş verdi: {str(e)}"
            ))

    thread = threading.Thread(target=download_and_send)
    thread.daemon = True
    thread.start()


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    logger.info("Bot işə düşdü!")
    app.run_polling()


if __name__ == "__main__":
    main()

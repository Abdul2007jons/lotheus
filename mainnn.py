import logging
import os
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
from telegram.error import TimedOut
from yt_dlp import YoutubeDL
import asyncio
from datetime import datetime
import json
import sys
import nest_asyncio

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Bot token
TOKEN = '7567026229:AAERefGvQHEGwwHabG0ttnJFFdykREmBSzg'

# Create necessary directories
DOWNLOAD_DIR = Path('downloads')
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Store user preferences
USER_PREFS_FILE = 'user_preferences.json'
try:
    with open(USER_PREFS_FILE, 'r') as f:
        user_preferences = json.load(f)
except FileNotFoundError:
    user_preferences = {}

def save_preferences():
    with open(USER_PREFS_FILE, 'w') as f:
        json.dump(user_preferences, f)

# Default settings
DEFAULT_QUALITY = '192'
DEFAULT_SPEED = '1.0'

class AudioProcessor:
    @staticmethod
    def change_speed(input_path: str, output_path: str, speed_factor: float):
        try:
            input_path = str(Path(input_path))
            output_path = str(Path(output_path))
            
            print(f"Processing audio file: {input_path}")
            
            from moviepy.editor import AudioFileClip
            audio = AudioFileClip(input_path)
            
            # Use lambda function for speed change
            modified_audio = audio.fl(lambda gf, t: gf(t * speed_factor))
            modified_audio = modified_audio.set_duration(audio.duration / speed_factor)
            
            # Write the modified audio
            modified_audio.write_audiofile(output_path)
            
            # Clean up
            audio.close()
            modified_audio.close()
            
            return output_path
        except Exception as e:
            print(f"Error in audio processing: {e}")
            return input_path

def get_ydl_opts(quality='192'):
    return {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': quality,
        }],
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'max_filesize': 50_000_000,  # 50 MB limit
    }

def get_user_settings(user_id: int) -> dict:
    if str(user_id) not in user_preferences:
        user_preferences[str(user_id)] = {
            'quality': DEFAULT_QUALITY,
            'speed': DEFAULT_SPEED,
            'downloads': 0,
            'last_download': None
        }
        save_preferences()
    return user_preferences[str(user_id)]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("⚙️ Settings", callback_data='settings'),
            InlineKeyboardButton("📊 Stats", callback_data='stats')
        ],
        [InlineKeyboardButton("❓ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '🎵 Welcome to Pro YouTube Music Downloader!\n\n'
        'Features:\n'
        '• Multiple quality options (128k-320k)\n'
        '• Speed adjustment (0.5x-2.0x)\n'
        '• Download statistics\n'
        '• Custom preferences\n\n'
        'Send me a YouTube link to start!',
        reply_markup=reply_markup
    )

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    settings = get_user_settings(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("🎨 Quality: " + settings['quality'] + "k", callback_data='quality'),
            InlineKeyboardButton("⚡ Speed: " + settings['speed'] + "x", callback_data='speed')
        ],
        [InlineKeyboardButton("◀️ Back", callback_data='main_menu')]
    ]
    
    await query.edit_message_text(
        "⚙️ Settings Panel\n\n"
        f"🎨 Current Quality: {settings['quality']}k\n"
        f"⚡ Current Speed: {settings['speed']}x",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def quality_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("🔈 128k", callback_data='set_quality_128'),
            InlineKeyboardButton("🔉 192k", callback_data='set_quality_192'),
            InlineKeyboardButton("🔊 320k", callback_data='set_quality_320')
        ],
        [InlineKeyboardButton("◀️ Back to Settings", callback_data='settings')]
    ]
    
    await update.callback_query.edit_message_text(
        "🎨 Select Audio Quality:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def speed_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("🐌 0.5x", callback_data='set_speed_0.5'),
            InlineKeyboardButton("🚶 0.75x", callback_data='set_speed_0.75'),
            InlineKeyboardButton("🚶‍♂️ 1.0x", callback_data='set_speed_1.0')
        ],
        [
            InlineKeyboardButton("🏃 1.25x", callback_data='set_speed_1.25'),
            InlineKeyboardButton("🏃‍♂️ 1.5x", callback_data='set_speed_1.5'),
            InlineKeyboardButton("⚡ 2.0x", callback_data='set_speed_2.0')
        ],
        [InlineKeyboardButton("◀️ Back to Settings", callback_data='settings')]
    ]
    
    await update.callback_query.edit_message_text(
        "⚡ Select Playback Speed:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    stats = get_user_settings(user_id)
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='main_menu')]]
    
    stats_text = (
        "📊 Your Statistics\n\n"
        f"Total Downloads: {stats['downloads']}\n"
        f"Last Download: {stats['last_download'] or 'Never'}\n"
        f"Current Quality: {stats['quality']}k\n"
        f"Current Speed: {stats['speed']}x"
    )
    
    await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='main_menu')]]
    
    help_text = (
        "❓ Help & Information\n\n"
        "1. Send a YouTube link to download\n"
        "2. Adjust quality in settings:\n"
        "   • 128k - Smaller size\n"
        "   • 192k - Balanced\n"
        "   • 320k - Best quality\n\n"
        "3. Adjust speed:\n"
        "   • 0.5x to 2.0x available\n\n"
        "4. Size limit: 50MB\n"
        "5. Supported sites: YouTube, YouTube Music\n\n"
        "Commands:\n"
        "/start - Show main menu\n"
        "/settings - Open settings\n"
        "/stats - View your statistics"
    )
    
    await update.callback_query.edit_message_text(
        help_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def process_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    
    if query.data == 'settings':
        await settings_menu(update, context)
    elif query.data == 'quality':
        await quality_menu(update, context)
    elif query.data == 'speed':
        await speed_menu(update, context)
    elif query.data == 'stats':
        await stats_menu(update, context)
    elif query.data == 'help':
        await help_menu(update, context)
    elif query.data == 'main_menu':
        keyboard = [
            [
                InlineKeyboardButton("⚙️ Settings", callback_data='settings'),
                InlineKeyboardButton("📊 Stats", callback_data='stats')
            ],
            [InlineKeyboardButton("❓ Help", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            '🎵 Welcome to Pro YouTube Music Downloader!\n\n'
            'Features:\n'
            '• Multiple quality options (128k-320k)\n'
            '• Speed adjustment (0.5x-2.0x)\n'
            '• Download statistics\n'
            '• Custom preferences\n\n'
            'Send me a YouTube link to start!',
            reply_markup=reply_markup
        )
    elif query.data.startswith('set_quality_'):
        quality = query.data.split('_')[2]
        user_preferences[str(user_id)]['quality'] = quality
        save_preferences()
        await settings_menu(update, context)
    elif query.data.startswith('set_speed_'):
        speed = query.data.split('_')[2]
        user_preferences[str(user_id)]['speed'] = speed
        save_preferences()
        await settings_menu(update, context)
    
    await query.answer()

async def send_audio_with_retry(update: Update, file_path: str, title: str, duration: int) -> None:
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            with open(file_path, 'rb') as audio:
                await update.message.reply_audio(
                    audio=audio,
                    duration=duration,
                    title=title,
                    caption=f"🎵 {title}\n\n⚙️ Quality: {get_user_settings(update.message.from_user.id)['quality']}k\n⚡ Speed: {get_user_settings(update.message.from_user.id)['speed']}x",
                    read_timeout=30,
                    write_timeout=30,
                    connect_timeout=30,
                    pool_timeout=30
                )
            return True
        except TimedOut:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                await update.message.reply_text("⚠️ File download failed after several retries.")
                return False

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    settings = get_user_settings(user_id)
    url = update.message.text.strip()
    
    if not url.startswith('https://'):
        await update.message.reply_text("Please send a valid YouTube link.")
        return

    status_message = await update.message.reply_text("⏳ Processing your request...")
    
    try:
        with YoutubeDL(get_ydl_opts(settings['quality'])) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info['title']
            
            base_path = Path('downloads')
            input_file = base_path / f"{title}.mp3"
            output_file = base_path / f"{title}_speed_{settings['speed']}.mp3"
            
            print(f"Input file: {input_file}")
            print(f"Output file: {output_file}")
            
            speed = float(settings['speed'])
            processed_file = AudioProcessor.change_speed(str(input_file), str(output_file), speed)
            
            success = await send_audio_with_retry(update, processed_file, title, info['duration'])
            
            if success:
                user_preferences[str(user_id)]['downloads'] += 1
                user_preferences[str(user_id)]['last_download'] = str(datetime.now())
                save_preferences()
            
            try:
                if os.path.exists(input_file):
                    os.remove(input_file)
                if os.path.exists(output_file) and input_file != output_file:
                    os.remove(output_file)
            except Exception as e:
                print(f"Error cleaning up files: {e}")

    except Exception as e:
        logging.error(f"Error while downloading: {e}")
        await update.message.reply_text("❌ An error occurred while downloading the video.")
    finally:
        await status_message.delete()

async def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats_menu))
    application.add_handler(CommandHandler("settings", settings_menu))

    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_audio))

    # Callback query handlers
    application.add_handler(CallbackQueryHandler(process_callback))

    await application.run_polling()

if __name__ == '__main__':
    # First, install nest_asyncio if not already installed
    try:
        import nest_asyncio
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "nest_asyncio"])
        import nest_asyncio
    
    nest_asyncio.apply()
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
        # If there's a running event loop, try to use it
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(main())
            else:
                loop.run_until_complete(main())
        except Exception as e2:
            print(f"Failed to run with existing loop: {e2}")

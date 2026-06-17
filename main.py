# main.py - Complete Single File Solution (Telegram Bot + Web Interface)
import telebot
import yt_dlp
import os
import time
import random
import string
import requests
import logging
import re
import json
import threading
import uuid
import shutil
from datetime import datetime
from urllib.parse import urlparse
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Bot & App Settings ---
BOT_TOKEN = "7510635174:AAGgtVg0KYyTfo0brf1YadFEVU3C8hmgt7g"
CHANNEL_USERNAME = "@SPEED_X_OFFICIAL1"
OWNER_ID = 7224513731
LOG_CHANNEL_ID = -1002780174909
CATBOX_API_URL = "https://catbox.moe/user/api.php"
TELEGRAM_UPLOAD_LIMIT_MB = 200

# --- Flask App Setup ---
app = Flask(__name__)
CORS(app)
app.secret_key = ''.join(random.choices(string.ascii_letters + string.digits, k=32))

# --- Create directories ---
DOWNLOAD_FOLDER = 'downloads'
STATIC_FOLDER = 'static'
TEMP_FOLDER = 'temp'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

# --- Bot Initialization ---
bot = telebot.TeleBot(BOT_TOKEN)
users = {}
user_download_history = {}
download_files = {}

# --- Loading Messages ---
LOADING_MESSAGES = [
    "✨ 𝐕𝐈𝐏 𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐈𝐍𝐆 ✨\n█▒▒▒▒▒▒▒▒▒▒ 10%\n⚡ 𝐼𝓃𝒾𝓉𝒾𝒶𝓁𝒾𝓏𝒾𝓃𝑔...",
    "💎 𝐕𝐈𝐏 𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐈𝐍𝐆 💎\n███▒▒▒▒▒▒▒▒ 30%\n🚀 𝐹𝑒𝓉𝒸𝒽𝒾𝓃𝑔 𝓋𝒾𝒹𝑒𝑜...",
    "👑 𝐕𝐈𝐏 𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐈𝐍𝐆 👑\n██████▒▒▒▒▒ 60%\n🎬 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝒾𝓃𝑔 𝒸𝑜𝓃𝓉𝑒𝓃𝓉...",
    "⭐ 𝐕𝐈𝐏 𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐈𝐍𝐆 ⭐\n██████████▒ 90%\n🔄 𝒫𝓇𝑒𝓅𝒶𝓇𝒾𝓃𝑔 𝒻𝑜𝓇 𝓎𝑜𝓊...",
    "🎯 𝐕𝐈𝐏 𝐑𝐄𝐀𝐃𝐘 🎯\n████████████ 100%\n✅ 𝒜𝓁𝓂𝑜𝓈𝓉 𝓉𝒽𝑒𝓇𝑒..."
]

# --- Utility Functions ---

def get_random_string(length=10):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def cleanup_file(file_path):
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not remove file {file_path}: {e}")

def format_file_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} GB"

def get_supported_platforms():
    return [
        {'name': 'TikTok', 'icon': '🎬', 'id': 'tiktok', 'patterns': ['tiktok.com', 'vm.tiktok']},
        {'name': 'Facebook', 'icon': '📹', 'id': 'facebook', 'patterns': ['facebook.com', 'fb.watch']},
        {'name': 'Instagram', 'icon': '📸', 'id': 'instagram', 'patterns': ['instagram.com', 'instagr.am']},
        {'name': 'YouTube', 'icon': '▶️', 'id': 'youtube', 'patterns': ['youtube.com', 'youtu.be']},
        {'name': 'Twitter/X', 'icon': '🐦', 'id': 'twitter', 'patterns': ['twitter.com', 'x.com']},
        {'name': 'Reddit', 'icon': '🤖', 'id': 'reddit', 'patterns': ['reddit.com', 'redd.it']}
    ]

def detect_platform(url):
    url_lower = url.lower()
    for platform in get_supported_platforms():
        for pattern in platform['patterns']:
            if pattern in url_lower:
                return platform['id']
    return 'unknown'

def extract_video_info(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown Title'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'description': info.get('description', '')[:200],
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'platform': detect_platform(url)
            }
    except Exception as e:
        logger.error(f"Error extracting info: {e}")
        return None

def download_video(url, platform='tiktok', format_type='video'):
    unique_id = get_random_string(8)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_base = f"{platform}_{format_type}_{timestamp}_{unique_id}"
    
    if format_type == 'mp3':
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(TEMP_FOLDER, f'{filename_base}.%(ext)s'),
            'quiet': True,
            'noplaylist': True,
            'postprocessors': [
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}
            ],
        }
    else:
        ydl_opts = {
            'outtmpl': os.path.join(TEMP_FOLDER, f'{filename_base}.%(ext)s'),
            'quiet': True,
            'noplaylist': True,
            'merge_output_format': 'mp4',
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'postprocessors': [{'key': 'FFmpegVideoRemuxer', 'preferedformat': 'mp4'}],
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.tiktok.com/'
            }
        }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if format_type == 'mp3':
                file_path = os.path.join(TEMP_FOLDER, f'{filename_base}.mp3')
            else:
                file_path = ydl.prepare_filename(info)
                if not os.path.exists(file_path):
                    file_path = os.path.join(TEMP_FOLDER, f'{filename_base}.mp4')
            
            if os.path.exists(file_path):
                return {
                    'file_path': file_path,
                    'filename': os.path.basename(file_path),
                    'title': info.get('title', 'video'),
                    'size': os.path.getsize(file_path)
                }
            return None
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None

def upload_to_catbox(file_path):
    if not os.path.exists(file_path):
        logger.error(f"File not found for Catbox upload: {file_path}")
        return None
    try:
        with open(file_path, 'rb') as f:
            files = {'fileToUpload': f}
            data = {'reqtype': 'fileupload'}
            response = requests.post(CATBOX_API_URL, files=files, data=data, timeout=120)
            response.raise_for_status()
            if response.status_code == 200 and response.text.startswith('https://files.catbox.moe/'):
                logger.info(f"Successfully uploaded {file_path} to Catbox.")
                return response.text.strip()
            raise Exception(f"Catbox upload failed: {response.text}")
    except Exception as e:
        logger.error(f"Error uploading to Catbox: {e}")
        return None

# ============================================
# FLASK WEB ROUTES
# ============================================

@app.route('/')
def index():
    platforms = get_supported_platforms()
    return render_template_string(HTML_TEMPLATE, platforms=platforms, channel=CHANNEL_USERNAME)

@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.get_json()
    url = data.get('url', '').strip()
    format_type = data.get('format', 'video')
    
    if not url:
        return jsonify({'error': 'Please provide a URL'}), 400
    
    platform = detect_platform(url)
    if platform == 'unknown':
        return jsonify({'error': 'Unsupported platform. Please use TikTok, Facebook, Instagram, YouTube, Twitter, or Reddit.'}), 400
    
    info = extract_video_info(url)
    result = download_video(url, platform, format_type)
    
    if not result:
        return jsonify({'error': 'Failed to download video. Please check the URL and try again.'}), 400
    
    download_id = uuid.uuid4().hex[:12]
    file_path = result['file_path']
    filename = result['filename']
    
    download_files[download_id] = {
        'file_path': file_path,
        'filename': filename,
        'expires': datetime.now().timestamp() + 3600
    }
    
    return jsonify({
        'success': True,
        'download_id': download_id,
        'filename': filename,
        'title': result['title'],
        'size': format_file_size(result['size']),
        'platform': platform,
        'format': format_type,
        'info': info,
        'download_url': f'/download/{download_id}',
    })

@app.route('/download/<download_id>')
def download_file(download_id):
    if download_id not in download_files:
        return "File not found or expired", 404
    
    file_info = download_files[download_id]
    file_path = file_info['file_path']
    filename = file_info['filename']
    
    if not os.path.exists(file_path):
        return "File not found", 404
    
    return send_file(file_path, as_attachment=True, download_name=filename)

@app.route('/api/check_url', methods=['POST'])
def check_url():
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'valid': False, 'error': 'Please provide a URL'})
    
    platform = detect_platform(url)
    if platform == 'unknown':
        return jsonify({'valid': False, 'error': 'Unsupported platform'})
    
    info = extract_video_info(url)
    return jsonify({
        'valid': True,
        'platform': platform,
        'info': info
    })

@app.route('/api/cleanup', methods=['POST'])
def cleanup_old_files():
    current_time = datetime.now().timestamp()
    expired = []
    for download_id, info in download_files.items():
        if current_time > info['expires']:
            expired.append(download_id)
            try:
                os.remove(info['file_path'])
            except:
                pass
    for download_id in expired:
        del download_files[download_id]
    return jsonify({'cleaned': len(expired)})

# ============================================
# TELEGRAM BOT HANDLERS
# ============================================

def is_user_verified(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking channel membership for user {user_id}: {e}")
        return False

def get_main_menu_markup():
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("🎬 𝐓𝐈𝐊𝐓𝐎𝐊 𝐕𝐈𝐃𝐄𝐎", callback_data="tiktok_btn"),
        telebot.types.InlineKeyboardButton("🎵 𝐓𝐈𝐊𝐓𝐎𝐊 𝐌𝐏𝟑", callback_data="tiktok_mp3_btn")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("📹 𝐅𝐀𝐂𝐄𝐁𝐎𝐎𝐊", callback_data="facebook_btn"),
        telebot.types.InlineKeyboardButton("💎 𝐕𝐈𝐏 𝐇𝐄𝐋𝐏", callback_data="help_btn")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("📢 𝐉𝐎𝐈𝐍 𝐕𝐈𝐏", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"),
        telebot.types.InlineKeyboardButton("👑 𝐎𝐖𝐍𝐄𝐑", url="https://t.me/NIROB_BBZ")
    )
    return markup

def get_video_action_markup(video_url, platform="tiktok"):
    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        telebot.types.InlineKeyboardButton("📥 𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃", url=video_url),
        telebot.types.InlineKeyboardButton("🔄 𝐒𝐇𝐀𝐑𝐄", switch_inline_query=video_url),
        telebot.types.InlineKeyboardButton("⭐ 𝐒𝐀𝐕𝐄", callback_data=f"save_{platform}")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("🏠 𝐌𝐀𝐈𝐍 𝐌𝐄𝐍𝐔", callback_data="main_menu"),
        telebot.types.InlineKeyboardButton("📹 𝐀𝐍𝐎𝐓𝐇𝐄𝐑", callback_data=f"{platform}_again")
    )
    return markup

def get_verification_markup():
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("✨ 𝐉𝐎𝐈𝐍 𝐕𝐈𝐏 𝐂𝐇𝐀𝐍𝐍𝐄𝐋 ✨", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"),
        telebot.types.InlineKeyboardButton("✅ 𝐕𝐄𝐑𝐈𝐅𝐘 𝐕𝐈𝐏 𝐀𝐂𝐂𝐄𝐒𝐒 ✅", callback_data="verify")
    )
    return markup

def send_loading_animation(chat_id):
    msg = bot.send_message(chat_id, LOADING_MESSAGES[0], parse_mode="HTML")
    for i, text in enumerate(LOADING_MESSAGES[1:], 1):
        time.sleep(0.8)
        try:
            bot.edit_message_text(text, chat_id, msg.message_id, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Loading animation stopped: {e}")
            break
    return msg

START_TEXT = """
╔══════════════════════════════╗
║  ✨ 𝐒𝐏𝐄𝐄𝐃_𝐗 𝐕𝐈𝐏 𝐁𝐎𝐓 ✨  ║
╚══════════════════════════════╝

💎 <b>𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐓𝐎 𝐓𝐇𝐄 𝐔𝐋𝐓𝐈𝐌𝐀𝐓𝐄 𝐕𝐈𝐏 𝐄𝐗𝐏𝐄𝐑𝐈𝐄𝐍𝐂𝐄</b> 💎

⚡ <b>𝐅𝐄𝐀𝐓𝐔𝐑𝐄𝐒:</b>

🎬 <b>TikTok Video</b> → HD quality, no watermark
🎵 <b>TikTok MP3</b> → High quality audio extraction
📹 <b>Facebook Video</b> → HD quality download
🚀 <b>Lightning Fast</b> → VIP speed processing
👑 <b>24/7 Support</b> → Always online

────────────────────────
⚠️ <b>𝐕𝐄𝐑𝐈𝐅𝐈𝐂𝐀𝐓𝐈𝐎𝐍 𝐑𝐄𝐐𝐔𝐈𝐑𝐄𝐃</b>
────────────────────────

✨ Join our VIP channel to unlock all features!
"""

VERIFIED_TEXT = """
╔══════════════════════════════╗
║  ✅ 𝐕𝐈𝐏 𝐕𝐄𝐑𝐈𝐅𝐈𝐄𝐃 ✅  ║
╚══════════════════════════════╝

🎉 <b>𝐂𝐎𝐍𝐆𝐑𝐀𝐓𝐔𝐋𝐀𝐓𝐈𝐎𝐍𝐒!</b> 🎉

<b>You now have FULL VIP ACCESS!</b>

💎 <b>What you can do:</b>
• Download TikTok videos (No watermark)
• Convert TikTok to MP3
• Download Facebook videos
• Get instant support

<b>👇 𝐂𝐇𝐎𝐎𝐒𝐄 𝐀𝐍 𝐎𝐏𝐓𝐈𝐎𝐍 𝐁𝐄𝐋𝐎𝐖 👇</b>
"""

HELP_TEXT = """
╔══════════════════════════════╗
║  ❓ 𝐕𝐈𝐏 𝐇𝐄𝐋𝐏 𝐂𝐄𝐍𝐓𝐄𝐑 ❓  ║
╚══════════════════════════════╝

<b>𝐇𝐎𝐖 𝐓𝐎 𝐔𝐒𝐄:</b>

1️⃣ <b>Choose your platform</b>
   ↓ Click on TikTok, TikTok MP3, or Facebook

2️⃣ <b>Send the video link</b>
   ↓ Just paste any supported video URL

3️⃣ <b>Get your VIP file</b>
   ↓ Bot processes & sends your download

<b>𝐍𝐎𝐓𝐄𝐒:</b>
✨ HD Quality guaranteed
⚡ No watermark on TikTok
🎵 Best MP3 quality
📹 Facebook HD supported

<b>𝐍𝐄𝐄𝐃 𝐇𝐄𝐋𝐏?</b>
👨‍💻 Contact: @NIROB_BBZ
📢 Channel: @SPEED_X_OFFICIAL1
"""

INVALID_LINK_MESSAGE = """
╔══════════════════════════════╗
║  ❌ 𝐈𝐍𝐕𝐀𝐋𝐈𝐃 𝐋𝐈𝐍𝐊 ❌  ║
╚══════════════════════════════╝

<b>Please send a valid video link from:</b>

✓ TikTok (vm.tiktok.com / tiktok.com)
✓ Facebook (fb.watch / facebook.com)

<b>Example:</b>
<code>https://vm.tiktok.com/xxxxx/</code>

🔄 <b>Try again with a correct link!</b>
"""

@bot.message_handler(commands=['start', 'help'])
def start_or_help(message):
    user_id = message.from_user.id
    users[user_id] = message.from_user
    if not is_user_verified(user_id):
        bot.send_message(message.chat.id, START_TEXT, reply_markup=get_verification_markup(), parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, VERIFIED_TEXT, reply_markup=get_main_menu_markup(), parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_callback(call):
    user_id = call.from_user.id
    try:
        if is_user_verified(user_id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, VERIFIED_TEXT, reply_markup=get_main_menu_markup(), parse_mode="HTML")
            bot.answer_callback_query(call.id, "✅ VIP ACCESS GRANTED!", show_alert=True)
        else:
            bot.edit_message_text(
                f"⚠️ <b>NOT VERIFIED YET!</b>\n\nPlease join {CHANNEL_USERNAME} and click VERIFY again.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_verification_markup(),
                parse_mode="HTML"
            )
            bot.answer_callback_query(call.id, "❌ Join the VIP channel first!", show_alert=True)
    except Exception as e:
        logger.error(f"Verification callback error for user {user_id}: {e}")
        bot.answer_callback_query(call.id, "❌ Verification failed! Try again.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_main_menu(call):
    bot.edit_message_text(
        text=VERIFIED_TEXT,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=get_main_menu_markup(),
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data in ["tiktok_again", "tiktok_mp3_again", "facebook_again"])
def again_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    handlers = {
        "tiktok_again": ("🎬 <b>Send another TikTok video link:</b>", process_tiktok_link),
        "tiktok_mp3_again": ("🎵 <b>Send another TikTok link for MP3:</b>", process_tiktok_mp3_link),
        "facebook_again": ("📹 <b>Send another Facebook video link:</b>", process_facebook_link)
    }
    if call.data in handlers:
        prompt_msg = bot.send_message(call.message.chat.id, handlers[call.data][0], reply_markup=get_main_menu_markup(), parse_mode="HTML")
        bot.register_next_step_handler(prompt_msg, handlers[call.data][1])
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "help_btn")
def help_callback(call):
    bot.edit_message_text(
        text=HELP_TEXT,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=get_main_menu_markup(),
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data in ["tiktok_btn", "tiktok_mp3_btn", "facebook_btn"])
def handle_menu_buttons(call):
    user_id = call.from_user.id
    if not is_user_verified(user_id):
        bot.answer_callback_query(call.id, "❌ VIP verification required first!", show_alert=True)
        return
    bot.delete_message(call.message.chat.id, call.message.message_id)
    handlers = {
        "tiktok_btn": ("🎬 <b>𝐏𝐀𝐒𝐓𝐄 𝐘𝐎𝐔𝐑 𝐓𝐈𝐊𝐓𝐎𝐊 𝐕𝐈𝐃𝐄𝐎 𝐋𝐈𝐍𝐊</b>\n\n<i>Example: https://vm.tiktok.com/xxxxx/</i>", process_tiktok_link),
        "tiktok_mp3_btn": ("🎵 <b>𝐏𝐀𝐒𝐓𝐄 𝐘𝐎𝐔𝐑 𝐓𝐈𝐊𝐓𝐎𝐊 𝐋𝐈𝐍𝐊 𝐅𝐎𝐑 𝐌𝐏𝟑</b>\n\n<i>I'll extract the audio in high quality!</i>", process_tiktok_mp3_link),
        "facebook_btn": ("📹 <b>𝐏𝐀𝐒𝐓𝐄 𝐘𝐎𝐔𝐑 𝐅𝐀𝐂𝐄𝐁𝐎𝐎𝐊 𝐕𝐈𝐃𝐄𝐎 𝐋𝐈𝐍𝐊</b>\n\n<i>Facebook videos are downloaded in HD quality!</i>", process_facebook_link)
    }
    if call.data in handlers:
        prompt_msg = bot.send_message(call.message.chat.id, handlers[call.data][0], reply_markup=get_main_menu_markup(), parse_mode="HTML")
        bot.register_next_step_handler(prompt_msg, handlers[call.data][1])
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("save_"))
def save_content(call):
    bot.answer_callback_query(call.id, "✅ Content saved! Video will remain here.", show_alert=True)

def process_tiktok_link(message):
    user_id = message.from_user.id
    url = message.text.strip()
    if not any(x in url.lower() for x in ['tiktok.com', 'vm.tiktok']):
        bot.send_message(message.chat.id, INVALID_LINK_MESSAGE, parse_mode="HTML", reply_markup=get_main_menu_markup())
        return
    loading_msg = send_loading_animation(message.chat.id)
    result = download_video(url, 'tiktok', 'video')
    if result:
        file_size_mb = result['size'] / (1024 * 1024)
        caption = f"""
╔══════════════════════════════╗
║  🎬 𝐕𝐈𝐏 𝐓𝐈𝐊𝐓𝐎𝐊 𝐕𝐈𝐃𝐄𝐎 🎬  ║
╚══════════════════════════════╝

👤 <b>Downloaded by:</b> {message.from_user.first_name}
📏 <b>Size:</b> {format_file_size(result['size'])}
💎 <b>Quality:</b> HD (1080p)
✨ <b>Status:</b> No Watermark
"""
        with open(result['file_path'], 'rb') as f:
            bot.send_video(message.chat.id, f, caption=caption, reply_markup=get_video_action_markup(f"https://t.me/{bot.get_me().username}?start=video_{get_random_string()}", "tiktok"), parse_mode="HTML", supports_streaming=True)
        user_download_history.setdefault(user_id, []).append(f"[TikTok] {url}")
    else:
        bot.send_message(message.chat.id, "❌ <b>Download Failed!</b>", parse_mode="HTML", reply_markup=get_main_menu_markup())
    cleanup_file(result['file_path'] if result else None)
    try:
        bot.delete_message(message.chat.id, loading_msg.message_id)
    except:
        pass

def process_tiktok_mp3_link(message):
    user_id = message.from_user.id
    url = message.text.strip()
    if not any(x in url.lower() for x in ['tiktok.com', 'vm.tiktok']):
        bot.send_message(message.chat.id, INVALID_LINK_MESSAGE, parse_mode="HTML", reply_markup=get_main_menu_markup())
        return
    loading_msg = send_loading_animation(message.chat.id)
    result = download_video(url, 'tiktok', 'mp3')
    if result:
        caption = f"""
╔══════════════════════════════╗
║  🎵 𝐕𝐈𝐏 𝐓𝐈𝐊𝐓𝐎𝐊 𝐌𝐏𝟑 🎵  ║
╚══════════════════════════════╝

👤 <b>Downloaded by:</b> {message.from_user.first_name}
📏 <b>Size:</b> {format_file_size(result['size'])}
🎵 <b>Quality:</b> 320kbps (High Quality)
"""
        with open(result['file_path'], 'rb') as audio_file:
            bot.send_audio(message.chat.id, audio_file, caption=caption, reply_markup=get_video_action_markup(f"https://t.me/{bot.get_me().username}?start=mp3_{get_random_string()}", "mp3"), parse_mode="HTML", title="SPEED_X VIP Audio", performer="TikTok MP3")
        user_download_history.setdefault(user_id, []).append(f"[TikTok MP3] {url}")
    else:
        bot.send_message(message.chat.id, "❌ <b>Conversion Failed!</b>", parse_mode="HTML", reply_markup=get_main_menu_markup())
    cleanup_file(result['file_path'] if result else None)
    try:
        bot.delete_message(message.chat.id, loading_msg.message_id)
    except:
        pass

def process_facebook_link(message):
    user_id = message.from_user.id
    url = message.text.strip()
    if 'facebook.com' not in url.lower() and 'fb.watch' not in url.lower():
        bot.send_message(message.chat.id, INVALID_LINK_MESSAGE, parse_mode="HTML", reply_markup=get_main_menu_markup())
        return
    loading_msg = send_loading_animation(message.chat.id)
    result = download_video(url, 'facebook', 'video')
    if result:
        caption = f"""
╔══════════════════════════════╗
║  📹 𝐕𝐈𝐏 𝐅𝐀𝐂𝐄𝐁𝐎𝐎𝐊 𝐕𝐈𝐃𝐄𝐎 📹  ║
╚══════════════════════════════╝

👤 <b>Downloaded by:</b> {message.from_user.first_name}
📏 <b>Size:</b> {format_file_size(result['size'])}
💎 <b>Quality:</b> HD (1080p)
"""
        with open(result['file_path'], 'rb') as f:
            bot.send_video(message.chat.id, f, caption=caption, reply_markup=get_video_action_markup(f"https://t.me/{bot.get_me().username}?start=fb_{get_random_string()}", "facebook"), parse_mode="HTML", supports_streaming=True)
        user_download_history.setdefault(user_id, []).append(f"[Facebook] {url}")
    else:
        bot.send_message(message.chat.id, "❌ <b>Download Failed!</b>", parse_mode="HTML", reply_markup=get_main_menu_markup())
    cleanup_file(result['file_path'] if result else None)
    try:
        bot.delete_message(message.chat.id, loading_msg.message_id)
    except:
        pass

@bot.message_handler(commands=['hiden'])
def hidden_commands(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>OWNER ONLY!</b>", parse_mode="HTML")
        return
    bot.reply_to(message, """
╔══════════════════════════════╗
║  👑 𝐎𝐖𝐍𝐄𝐑 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒 👑  ║
╚══════════════════════════════╝

/botuser → List all bot users
/bot_user_video → Show download history
/n [message] → Broadcast to all users
/stats → Show bot statistics
""", parse_mode="HTML")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>OWNER ONLY!</b>", parse_mode="HTML")
        return
    total_downloads = sum(len(history) for history in user_download_history.values())
    bot.reply_to(message, f"""
╔══════════════════════════════╗
║  📊 𝐁𝐎𝐓 𝐒𝐓𝐀𝐓𝐈𝐒𝐓𝐈𝐂𝐒 📊  ║
╚══════════════════════════════╝

👥 <b>Total Users:</b> {len(users)}
📥 <b>Total Downloads:</b> {total_downloads}
""", parse_mode="HTML")

@bot.message_handler(commands=['botuser'])
def list_bot_users(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>OWNER ONLY!</b>", parse_mode="HTML")
        return
    if not users:
        bot.send_message(message.chat.id, "📭 No users have used the bot yet.", parse_mode="HTML")
        return
    text = f"<b>👥 TOTAL USERS:</b> {len(users)}\n\n"
    for user_id, user_info in list(users.items())[:50]:
        text += f"👤 {user_info.first_name}\n🆔 <code>{user_id}</code>\n───────────\n"
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(commands=['n'])
def broadcast_message(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>OWNER ONLY!</b>", parse_mode="HTML")
        return
    try:
        broadcast_text = message.text.split(" ", 1)[1].strip()
    except:
        bot.reply_to(message, "❌ <b>Usage:</b> /n Your message here", parse_mode="HTML")
        return
    sent = 0
    for user_id in users.keys():
        try:
            bot.send_message(user_id, f"📢 <b>VIP ANNOUNCEMENT</b>\n\n{broadcast_text}", parse_mode="HTML")
            sent += 1
            time.sleep(0.05)
        except:
            pass
    bot.reply_to(message, f"✅ <b>Broadcast Complete!</b>\n\n📨 Sent: {sent}", parse_mode="HTML")

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    user_id = message.from_user.id
    if not is_user_verified(user_id):
        bot.reply_to(message, START_TEXT, reply_markup=get_verification_markup(), parse_mode="HTML")
    else:
        bot.reply_to(message, "❓ <b>Unknown command!</b>\n\nPlease use the buttons below:", reply_markup=get_main_menu_markup(), parse_mode="HTML")

# ============================================
# HTML TEMPLATE (Embedded)
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SPEED_X VIP Downloader</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; padding: 30px 0; }
        .header h1 { font-size: 2.5em; background: linear-gradient(45deg, #f093fb, #f5576c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header p { color: #a8a8b8; margin-top: 5px; }
        .vip-badge {
            display: inline-block;
            background: linear-gradient(45deg, #f093fb, #f5576c);
            padding: 5px 20px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            margin-top: 10px;
            animation: glow 2s infinite;
        }
        @keyframes glow {
            0%, 100% { box-shadow: 0 0 10px rgba(245, 87, 108, 0.5); }
            50% { box-shadow: 0 0 30px rgba(245, 87, 108, 0.8); }
        }
        .card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            margin: 20px 0;
            transition: all 0.3s ease;
        }
        .card:hover { border-color: rgba(245, 87, 108, 0.3); }
        .url-input-group {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 20px 0;
        }
        .url-input-group input {
            flex: 1;
            padding: 15px 20px;
            border-radius: 15px;
            border: 2px solid rgba(255, 255, 255, 0.1);
            background: rgba(255, 255, 255, 0.05);
            color: #fff;
            font-size: 1em;
            transition: all 0.3s ease;
            min-width: 200px;
        }
        .url-input-group input:focus {
            outline: none;
            border-color: #f5576c;
            box-shadow: 0 0 20px rgba(245, 87, 108, 0.2);
        }
        .url-input-group input::placeholder { color: #666; }
        .btn {
            padding: 15px 30px;
            border: none;
            border-radius: 15px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 1em;
            color: #fff;
        }
        .btn-primary { background: linear-gradient(45deg, #f093fb, #f5576c); }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(245, 87, 108, 0.4); }
        .btn-secondary { background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); }
        .btn-secondary:hover { background: rgba(255, 255, 255, 0.2); }
        .btn-success { background: linear-gradient(45deg, #00c6fb, #005bea); }
        .btn-success:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(0, 91, 234, 0.4); }
        .format-buttons {
            display: flex;
            gap: 10px;
            margin: 15px 0;
            flex-wrap: wrap;
        }
        .format-btn {
            padding: 10px 20px;
            border-radius: 10px;
            border: 2px solid rgba(255, 255, 255, 0.1);
            background: rgba(255, 255, 255, 0.05);
            color: #a8a8b8;
            cursor: pointer;
            transition: all 0.3s ease;
            flex: 1;
            min-width: 80px;
            text-align: center;
        }
        .format-btn.active { border-color: #f5576c; background: rgba(245, 87, 108, 0.2); color: #fff; }
        .format-btn:hover { border-color: #f5576c; }
        .platform-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .platform-item {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }
        .platform-item:hover { border-color: rgba(245, 87, 108, 0.3); transform: translateY(-5px); }
        .platform-item .icon { font-size: 2em; display: block; margin-bottom: 8px; }
        .platform-item .name { font-size: 0.8em; color: #a8a8b8; }
        .loading-container { display: none; text-align: center; padding: 40px 0; }
        .loading-container.active { display: block; }
        .spinner {
            width: 60px;
            height: 60px;
            border: 4px solid rgba(255, 255, 255, 0.1);
            border-top: 4px solid #f5576c;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            overflow: hidden;
            margin: 20px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #f093fb, #f5576c);
            width: 0%;
            border-radius: 3px;
            transition: width 0.5s ease;
        }
        .result-container { display: none; margin-top: 30px; }
        .result-container.active { display: block; }
        .video-info {
            display: flex;
            gap: 20px;
            padding: 15px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 15px;
            margin: 15px 0;
            flex-wrap: wrap;
        }
        .video-info .thumbnail {
            width: 120px;
            height: 80px;
            border-radius: 10px;
            object-fit: cover;
            flex-shrink: 0;
        }
        .video-info .details { flex: 1; }
        .video-info .details .title { font-weight: bold; font-size: 1.1em; }
        .video-info .details .meta { color: #a8a8b8; font-size: 0.9em; margin-top: 5px; }
        .download-btn {
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(45deg, #00c6fb, #005bea);
            color: #fff;
            border-radius: 10px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s ease;
            margin: 5px;
        }
        .download-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(0, 91, 234, 0.4); }
        .action-buttons { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 15px; }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .feature-item {
            text-align: center;
            padding: 20px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 15px;
        }
        .feature-item .icon { font-size: 2.5em; margin-bottom: 10px; }
        .feature-item .title { font-weight: bold; }
        .feature-item .desc { color: #a8a8b8; font-size: 0.9em; margin-top: 5px; }
        .footer { text-align: center; padding: 30px 0; color: #555; font-size: 0.9em; }
        .footer a { color: #f5576c; text-decoration: none; }
        .error-message {
            background: rgba(255, 0, 0, 0.1);
            border: 1px solid rgba(255, 0, 0, 0.2);
            border-radius: 10px;
            padding: 15px;
            color: #ff6b6b;
            display: none;
            margin: 10px 0;
        }
        .error-message.active { display: block; }
        @media (max-width: 600px) {
            .header h1 { font-size: 1.8em; }
            .card { padding: 20px; }
            .url-input-group { flex-direction: column; }
            .platform-grid { grid-template-columns: repeat(3, 1fr); }
            .video-info { flex-direction: column; align-items: center; text-align: center; }
            .video-info .thumbnail { width: 100%; height: auto; max-height: 180px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 SPEED_X VIP</h1>
            <p>Ultimate Media Downloader</p>
            <span class="vip-badge">✨ VIP ACCESS ✨</span>
        </div>

        <div class="features">
            <div class="feature-item">
                <div class="icon">🎬</div>
                <div class="title">TikTok HD</div>
                <div class="desc">No watermark, 1080p quality</div>
            </div>
            <div class="feature-item">
                <div class="icon">🎵</div>
                <div class="title">MP3 Converter</div>
                <div class="desc">320kbps high quality audio</div>
            </div>
            <div class="feature-item">
                <div class="icon">📹</div>
                <div class="title">Facebook Videos</div>
                <div class="desc">HD download, any video</div>
            </div>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 10px;">📥 Enter URL</h2>
            <p style="color: #a8a8b8; margin-bottom: 15px;">Paste any supported video link below</p>

            <div class="url-input-group">
                <input type="text" id="urlInput" placeholder="https://vm.tiktok.com/..." value="">
                <button class="btn btn-primary" onclick="startDownload()" id="downloadBtn">
                    <i class="fas fa-download"></i> Download
                </button>
            </div>

            <div class="error-message" id="errorMessage"></div>

            <div style="margin: 15px 0;">
                <p style="color: #a8a8b8; font-size: 0.9em; margin-bottom: 8px;">Format:</p>
                <div class="format-buttons">
                    <button class="format-btn active" data-format="video" onclick="selectFormat('video')">
                        <i class="fas fa-video"></i> Video
                    </button>
                    <button class="format-btn" data-format="mp3" onclick="selectFormat('mp3')">
                        <i class="fas fa-music"></i> MP3
                    </button>
                </div>
            </div>

            <div style="margin: 15px 0;">
                <p style="color: #a8a8b8; font-size: 0.9em; margin-bottom: 8px;">Supported Platforms:</p>
                <div class="platform-grid" id="platformGrid">
                    {% for platform in platforms %}
                    <div class="platform-item" onclick="setUrlExample('{{ platform.patterns[0] }}')">
                        <span class="icon">{{ platform.icon }}</span>
                        <span class="name">{{ platform.name }}</span>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <div class="loading-container" id="loadingContainer">
            <div class="spinner"></div>
            <h3>⏳ Processing Your VIP Download</h3>
            <p style="color: #a8a8b8;" id="loadingStatus">Initializing...</p>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
        </div>

        <div class="result-container" id="resultContainer">
            <div class="card">
                <h3>✅ Download Ready!</h3>
                <div id="resultContent"></div>
            </div>
        </div>

        <div class="footer">
            <p>💎 SPEED_X VIP Bot &copy; 2024 | <a href="https://t.me/{{ channel.strip('@') }}" target="_blank">Join VIP Channel</a></p>
            <p style="font-size: 0.8em; margin-top: 5px;">Powered by yt-dlp | Made with ❤️</p>
        </div>
    </div>

    <script>
        let selectedFormat = 'video';

        function selectFormat(format) {
            selectedFormat = format;
            document.querySelectorAll('.format-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelector(`.format-btn[data-format="${format}"]`).classList.add('active');
        }

        function setUrlExample(pattern) {
            document.getElementById('urlInput').placeholder = `https://${pattern}/...`;
            document.getElementById('urlInput').focus();
        }

        function showError(message) {
            const el = document.getElementById('errorMessage');
            el.textContent = message;
            el.classList.add('active');
        }

        function hideError() { document.getElementById('errorMessage').classList.remove('active'); }

        function showLoading() {
            document.getElementById('loadingContainer').classList.add('active');
            document.getElementById('resultContainer').classList.remove('active');
            document.getElementById('downloadBtn').disabled = true;
            document.getElementById('downloadBtn').innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            updateProgress(0, 'Initializing...');
        }

        function hideLoading() {
            document.getElementById('loadingContainer').classList.remove('active');
            document.getElementById('downloadBtn').disabled = false;
            document.getElementById('downloadBtn').innerHTML = '<i class="fas fa-download"></i> Download';
        }

        function updateProgress(percent, status) {
            document.getElementById('progressFill').style.width = percent + '%';
            document.getElementById('loadingStatus').textContent = status;
        }

        function showResult(data) {
            const container = document.getElementById('resultContainer');
            const content = document.getElementById('resultContent');
            const info = data.info || {};
            content.innerHTML = `
                <div class="video-info">
                    ${info.thumbnail ? `<img src="${info.thumbnail}" class="thumbnail" alt="Thumbnail" onerror="this.style.display='none'">` : ''}
                    <div class="details">
                        <div class="title">${info.title || data.title || 'Video'}</div>
                        <div class="meta">
                            ${info.uploader ? `👤 ${info.uploader} &bull; ` : ''}
                            ${info.duration ? `⏱️ ${formatDuration(info.duration)} &bull; ` : ''}
                            ${data.size ? `📦 ${data.size}` : ''}
                        </div>
                        <div class="meta">
                            ${info.view_count ? `👁️ ${formatNumber(info.view_count)} views` : ''}
                            ${info.like_count ? `❤️ ${formatNumber(info.like_count)} likes` : ''}
                        </div>
                    </div>
                </div>
                <div style="margin: 15px 0;">
                    <span class="vip-badge" style="font-size: 0.8em;">🎯 ${data.platform.toUpperCase()} ${data.format === 'mp3' ? '🎵 MP3' : '🎬 VIDEO'}</span>
                </div>
                <div class="action-buttons">
                    <a href="${data.download_url}" class="download-btn" download>
                        <i class="fas fa-download"></i> Download Now
                    </a>
                    <button class="btn btn-secondary" onclick="downloadAgain()">
                        <i class="fas fa-redo"></i> Another Video
                    </button>
                    <button class="btn btn-secondary" onclick="copyUrl()">
                        <i class="fas fa-copy"></i> Copy Link
                    </button>
                </div>
            `;
            container.classList.add('active');
            container.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        function formatDuration(seconds) {
            const m = Math.floor(seconds / 60);
            const s = seconds % 60;
            return `${m}:${s.toString().padStart(2, '0')}`;
        }

        function formatNumber(num) {
            if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
            if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
            return num;
        }

        function copyUrl() {
            const url = document.getElementById('urlInput').value;
            if (url) {
                navigator.clipboard.writeText(url).then(() => {
                    showSuccess('URL copied to clipboard!');
                }).catch(() => {
                    const input = document.getElementById('urlInput');
                    input.select();
                    document.execCommand('copy');
                    showSuccess('URL copied!');
                });
            }
        }

        function showSuccess(message) {
            const el = document.getElementById('errorMessage');
            el.style.color = '#51cf66';
            el.textContent = '✅ ' + message;
            el.classList.add('active');
            setTimeout(() => { el.style.color = ''; el.classList.remove('active'); }, 3000);
        }

        function downloadAgain() {
            document.getElementById('resultContainer').classList.remove('active');
            document.getElementById('urlInput').value = '';
            document.getElementById('urlInput').focus();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        function startDownload() {
            const url = document.getElementById('urlInput').value.trim();
            hideError();
            if (!url) { showError('⚠️ Please enter a video URL'); return; }
            try { new URL(url); } catch { showError('⚠️ Please enter a valid URL'); return; }

            showLoading();
            updateProgress(10, 'Analyzing URL...');

            fetch('/api/check_url', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            })
            .then(res => res.json())
            .then(data => {
                if (!data.valid) throw new Error(data.error || 'Unsupported platform');
                updateProgress(30, `Detected: ${data.platform.toUpperCase()} - Fetching video...`);
                return data;
            })
            .then(() => {
                updateProgress(50, 'Downloading video (this may take a moment)...');
                return fetch('/api/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, format: selectedFormat })
                });
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                updateProgress(90, 'Finalizing...');
                setTimeout(() => {
                    updateProgress(100, '✅ Done!');
                    hideLoading();
                    showResult(data);
                }, 500);
            })
            .catch(err => {
                hideLoading();
                showError('❌ ' + err.message);
            });
        }

        document.getElementById('urlInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') startDownload();
        });

        document.getElementById('urlInput').addEventListener('paste', function() {
            setTimeout(() => {
                const url = this.value.trim();
                if (url && (url.includes('tiktok.com') || url.includes('facebook.com') || url.includes('youtube.com'))) {
                    // Auto-detect
                }
            }, 100);
        });

        console.log('🎬 SPEED_X VIP Downloader loaded!');
    </script>
</body>
</html>
"""

# ============================================
# RUN BOT AND WEB SERVER
# ============================================

def run_bot():
    logger.info("🚀 Starting Telegram Bot...")
    try:
        bot.polling(none_stop=True, interval=0)
    except Exception as e:
        logger.critical(f"Bot polling failed: {e}")

def run_web():
    logger.info("🌐 Starting Web Server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Clean temp files on startup
    for folder in [TEMP_FOLDER, DOWNLOAD_FOLDER]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                try:
                    os.remove(os.path.join(folder, f))
                    logger.info(f"Cleaned up old file: {f}")
                except:
                    pass

    print("""
    ╔═══════════════════════════════════════════════╗
    ║     𝐒𝐏𝐄𝐄𝐃_𝐗 𝐕𝐈𝐏 𝐁𝐎𝐓 + 𝐖𝐄𝐁 𝐈𝐍𝐓𝐄𝐑𝐅𝐀𝐂𝐄     ║
    ║          ✨ READY TO SERVE ✨                 ║
    ║         🌐 http://localhost:5000             ║
    ╚═══════════════════════════════════════════════╝
    """)

    # Start bot in separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Run web server (main thread)
    run_web()

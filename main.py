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
from flask import Flask, render_template_string, request, jsonify, send_file
from werkzeug.utils import secure_filename

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Settings ---
BOT_TOKEN = "7510635174:AAGgtVg0KYyTfo0brf1YadFEVU3C8hmgt7g"
CHANNEL_USERNAME = "@SPEED_X_OFFICIAL1"
OWNER_ID = 7224513731
LOG_CHANNEL_ID = -1002780174909
CATBOX_API_URL = "https://catbox.moe/user/api.php"
TELEGRAM_UPLOAD_LIMIT_MB = 50   # 50MB এর বেশি হলে Catbox

# --- Flask ---
app = Flask(__name__)
app.secret_key = ''.join(random.choices(string.ascii_letters + string.digits, k=32))

# --- CORS ---
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# --- Directories ---
TEMP_FOLDER = 'temp'
os.makedirs(TEMP_FOLDER, exist_ok=True)

# --- Bot ---
bot = telebot.TeleBot(BOT_TOKEN)
users = {}
user_download_history = {}
download_files = {}

# --- Helper Functions ---
def get_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def cleanup_file(file_path):
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except:
            pass

def format_file_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} GB"

def detect_platform(url):
    url_lower = url.lower()
    if 'tiktok.com' in url_lower or 'vm.tiktok' in url_lower:
        return 'tiktok'
    if 'facebook.com' in url_lower or 'fb.watch' in url_lower:
        return 'facebook'
    return 'unknown'

def extract_video_info(url):
    ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'platform': detect_platform(url)
            }
    except:
        return None

def download_media(url, platform='tiktok', format_type='video'):
    """
    Download video or audio.
    Returns: dict with file_path, filename, title, size, and if it's a photo album, returns 'is_album': True and 'entries': list of image URLs.
    """
    unique_id = get_random_string(8)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_base = f"{platform}_{format_type}_{timestamp}_{unique_id}"
    temp_dir = TEMP_FOLDER

    if format_type == 'mp3':
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(temp_dir, f'{filename_base}.%(ext)s'),
            'quiet': True,
            'noplaylist': True,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}],
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = os.path.join(temp_dir, f'{filename_base}.mp3')
                if os.path.exists(file_path):
                    return {
                        'file_path': file_path,
                        'filename': os.path.basename(file_path),
                        'title': info.get('title', 'audio'),
                        'size': os.path.getsize(file_path),
                        'is_album': False
                    }
        except Exception as e:
            logger.error(f"MP3 download error: {e}")
            return None

    else:  # video
        # Special handling for TikTok photo posts (slideshow)
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,
            'no_warnings': True,
            'outtmpl': os.path.join(temp_dir, f'{filename_base}.%(ext)s'),
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                # Check if it's a photo album (TikTok slideshow)
                if platform == 'tiktok' and info.get('_type') == 'playlist' and 'entries' in info:
                    # Photo album
                    image_urls = []
                    for entry in info['entries']:
                        if entry and 'url' in entry:
                            image_urls.append(entry['url'])
                    if image_urls:
                        # Download each image
                        downloaded_images = []
                        for idx, img_url in enumerate(image_urls):
                            img_ext = img_url.split('.')[-1].split('?')[0][:5]
                            if img_ext not in ['jpg', 'jpeg', 'png', 'webp']:
                                img_ext = 'jpg'
                            img_path = os.path.join(temp_dir, f"{filename_base}_{idx}.{img_ext}")
                            try:
                                r = requests.get(img_url, timeout=30)
                                with open(img_path, 'wb') as f:
                                    f.write(r.content)
                                downloaded_images.append(img_path)
                            except:
                                continue
                        if downloaded_images:
                            return {
                                'is_album': True,
                                'image_paths': downloaded_images,
                                'title': info.get('title', 'Photo Album'),
                                'uploader': info.get('uploader', 'Unknown')
                            }
                # Normal video
                ydl.download([url])
                file_path = ydl.prepare_filename(info)
                if not os.path.exists(file_path):
                    # try alternative name
                    alt = os.path.join(temp_dir, f'{filename_base}.mp4')
                    if os.path.exists(alt):
                        file_path = alt
                if os.path.exists(file_path):
                    return {
                        'file_path': file_path,
                        'filename': os.path.basename(file_path),
                        'title': info.get('title', 'video'),
                        'size': os.path.getsize(file_path),
                        'is_album': False
                    }
        except Exception as e:
            logger.error(f"Video download error: {e}")
            return None

def upload_to_catbox(file_path):
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'rb') as f:
            files = {'fileToUpload': f}
            data = {'reqtype': 'fileupload'}
            response = requests.post(CATBOX_API_URL, files=files, data=data, timeout=120)
            if response.status_code == 200 and response.text.startswith('https://files.catbox.moe/'):
                return response.text.strip()
    except:
        pass
    return None

# ============================================
# FLASK WEB ROUTES
# ============================================

@app.route('/')
def index():
    # শুধু TikTok ও Facebook
    platforms = [
        {'name': 'TikTok', 'icon': '🎬', 'id': 'tiktok', 'patterns': ['tiktok.com', 'vm.tiktok']},
        {'name': 'Facebook', 'icon': '📹', 'id': 'facebook', 'patterns': ['facebook.com', 'fb.watch']}
    ]
    return render_template_string(HTML_TEMPLATE, platforms=platforms, channel=CHANNEL_USERNAME)

@app.route('/api/download', methods=['POST', 'OPTIONS'])
def api_download():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json()
    url = data.get('url', '').strip()
    format_type = data.get('format', 'video')
    if not url:
        return jsonify({'error': 'Please provide a URL'}), 400

    platform = detect_platform(url)
    if platform == 'unknown':
        return jsonify({'error': 'Only TikTok and Facebook are supported.'}), 400

    result = download_media(url, platform, format_type)
    if not result:
        return jsonify({'error': 'Download failed. Please check URL.'}), 400

    # If album, return image paths
    if result.get('is_album'):
        # Store images temporarily
        download_id = uuid.uuid4().hex[:12]
        download_files[download_id] = {
            'type': 'album',
            'image_paths': result['image_paths'],
            'expires': datetime.now().timestamp() + 3600,
            'title': result['title'],
            'uploader': result.get('uploader', '')
        }
        return jsonify({
            'success': True,
            'download_id': download_id,
            'type': 'album',
            'title': result['title'],
            'uploader': result.get('uploader', ''),
            'image_count': len(result['image_paths']),
            'download_url': f'/download/{download_id}'
        })

    # Single file
    download_id = uuid.uuid4().hex[:12]
    download_files[download_id] = {
        'type': 'file',
        'file_path': result['file_path'],
        'filename': result['filename'],
        'expires': datetime.now().timestamp() + 3600,
        'title': result['title'],
        'size': result['size']
    }
    return jsonify({
        'success': True,
        'download_id': download_id,
        'type': 'file',
        'filename': result['filename'],
        'title': result['title'],
        'size': format_file_size(result['size']),
        'platform': platform,
        'format': format_type,
        'download_url': f'/download/{download_id}'
    })

@app.route('/download/<download_id>')
def download_file(download_id):
    if download_id not in download_files:
        return "File not found or expired", 404
    info = download_files[download_id]
    if info['type'] == 'album':
        # For album, send all images as a zip? Or just return first? We'll send a zip.
        import zipfile
        import io
        from flask import send_file as flask_send_file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zipf:
            for idx, img_path in enumerate(info['image_paths']):
                if os.path.exists(img_path):
                    zipf.write(img_path, f"image_{idx+1}.jpg")
        zip_buffer.seek(0)
        return flask_send_file(zip_buffer, as_attachment=True, download_name=f"{info['title']}.zip", mimetype='application/zip')
    else:
        file_path = info['file_path']
        filename = info['filename']
        if not os.path.exists(file_path):
            return "File not found", 404
        return send_file(file_path, as_attachment=True, download_name=filename)

@app.route('/api/check_url', methods=['POST', 'OPTIONS'])
def check_url():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'valid': False, 'error': 'No URL'})
    platform = detect_platform(url)
    if platform == 'unknown':
        return jsonify({'valid': False, 'error': 'Only TikTok & Facebook supported'})
    info = extract_video_info(url)
    return jsonify({'valid': True, 'platform': platform, 'info': info})

@app.route('/api/send_to_telegram', methods=['POST', 'OPTIONS'])
def send_to_telegram():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json()
    download_id = data.get('download_id')
    user_id = data.get('user_id')  # Telegram user ID (numeric)
    if not download_id or not user_id:
        return jsonify({'error': 'Missing download_id or user_id'}), 400
    if download_id not in download_files:
        return jsonify({'error': 'Invalid download_id'}), 400
    info = download_files[download_id]
    try:
        user_id = int(user_id)
    except:
        return jsonify({'error': 'Invalid user_id'}), 400

    # Send file to user via bot
    try:
        if info['type'] == 'album':
            # Send media group
            media_group = []
            for idx, img_path in enumerate(info['image_paths']):
                if os.path.exists(img_path):
                    with open(img_path, 'rb') as f:
                        # send one by one or group
                        pass
            # Actually we need to send media group, but telebot send_media_group expects list of InputMediaPhoto
            from telebot.types import InputMediaPhoto
            media = []
            for img_path in info['image_paths']:
                if os.path.exists(img_path):
                    media.append(InputMediaPhoto(open(img_path, 'rb')))
            if media:
                bot.send_media_group(user_id, media)
                return jsonify({'success': True, 'message': 'Album sent to Telegram!'})
            else:
                return jsonify({'error': 'No images found'}), 400
        else:
            file_path = info['file_path']
            if not os.path.exists(file_path):
                return jsonify({'error': 'File missing'}), 400
            # Check size
            size_mb = os.path.getsize(file_path) / (1024*1024)
            if size_mb > TELEGRAM_UPLOAD_LIMIT_MB:
                # Upload to Catbox and send link
                link = upload_to_catbox(file_path)
                if link:
                    bot.send_message(user_id, f"📥 File too large for Telegram. Download from here:\n{link}")
                    return jsonify({'success': True, 'message': 'Large file link sent via Catbox'})
                else:
                    return jsonify({'error': 'Failed to upload large file'}), 400
            else:
                with open(file_path, 'rb') as f:
                    if info['filename'].endswith('.mp3'):
                        bot.send_audio(user_id, f, caption=info.get('title', 'Audio'))
                    else:
                        bot.send_video(user_id, f, caption=info.get('title', 'Video'), supports_streaming=True)
                return jsonify({'success': True, 'message': 'File sent to Telegram!'})
    except Exception as e:
        logger.error(f"Send to Telegram error: {e}")
        return jsonify({'error': str(e)}), 400

# ============================================
# TELEGRAM BOT HANDLERS
# ============================================

def is_user_verified(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
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
    msgs = [
        "✨ 𝐕𝐈𝐏 𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐈𝐍𝐆 ✨\n█▒▒▒▒▒▒▒▒▒▒ 10%",
        "💎 𝐕𝐈𝐏 𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐈𝐍𝐆 💎\n███▒▒▒▒▒▒▒▒ 30%",
        "👑 𝐕𝐈𝐏 𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐈𝐍𝐆 👑\n██████▒▒▒▒▒ 60%",
        "⭐ 𝐕𝐈𝐏 𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐈𝐍𝐆 ⭐\n██████████▒ 90%",
        "🎯 𝐕𝐈𝐏 𝐑𝐄𝐀𝐃𝐘 🎯\n████████████ 100%"
    ]
    msg = bot.send_message(chat_id, msgs[0], parse_mode="HTML")
    for i, text in enumerate(msgs[1:], 1):
        time.sleep(0.5)
        try:
            bot.edit_message_text(text, chat_id, msg.message_id, parse_mode="HTML")
        except:
            break
    return msg

START_TEXT = """╔══════════════════════════════╗
║  ✨ 𝐒𝐏𝐄𝐄𝐃_𝐗 𝐕𝐈𝐏 𝐁𝐎𝐓 ✨  ║
╚══════════════════════════════╝

💎 <b>𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐓𝐎 𝐓𝐇𝐄 𝐔𝐋𝐓𝐈𝐌𝐀𝐓𝐄 𝐕𝐈𝐏 𝐄𝐗𝐏𝐄𝐑𝐈𝐄𝐍𝐂𝐄</b> 💎

🎬 TikTok Video (HD, no watermark)
🎵 TikTok MP3 (320kbps)
📹 Facebook Video (HD)

⚠️ <b>𝐕𝐄𝐑𝐈𝐅𝐈𝐂𝐀𝐓𝐈𝐎𝐍 𝐑𝐄𝐐𝐔𝐈𝐑𝐄𝐃</b>
Join our VIP channel first!
"""

VERIFIED_TEXT = """╔══════════════════════════════╗
║  ✅ 𝐕𝐈𝐏 𝐕𝐄𝐑𝐈𝐅𝐈𝐄𝐃 ✅  ║
╚══════════════════════════════╝

🎉 <b>𝐂𝐎𝐍𝐆𝐑𝐀𝐓𝐔𝐋𝐀𝐓𝐈𝐎𝐍𝐒!</b> 🎉

<b>You now have FULL VIP ACCESS!</b>

👇 <b>𝐂𝐇𝐎𝐎𝐒𝐄 𝐀𝐍 𝐎𝐏𝐓𝐈𝐎𝐍</b> 👇
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
    if is_user_verified(user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, VERIFIED_TEXT, reply_markup=get_main_menu_markup(), parse_mode="HTML")
        bot.answer_callback_query(call.id, "✅ VIP ACCESS GRANTED!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "❌ Join the VIP channel first!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_main_menu(call):
    bot.edit_message_text(VERIFIED_TEXT, call.message.chat.id, call.message.message_id,
                          reply_markup=get_main_menu_markup(), parse_mode="HTML")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data in ["tiktok_btn", "tiktok_mp3_btn", "facebook_btn"])
def handle_menu_buttons(call):
    user_id = call.from_user.id
    if not is_user_verified(user_id):
        bot.answer_callback_query(call.id, "❌ Verify first!", show_alert=True)
        return
    bot.delete_message(call.message.chat.id, call.message.message_id)
    handlers = {
        "tiktok_btn": ("🎬 Send TikTok video link:", process_tiktok),
        "tiktok_mp3_btn": ("🎵 Send TikTok link for MP3:", process_tiktok_mp3),
        "facebook_btn": ("📹 Send Facebook video link:", process_facebook)
    }
    if call.data in handlers:
        prompt_msg = bot.send_message(call.message.chat.id, handlers[call.data][0], reply_markup=get_main_menu_markup(), parse_mode="HTML")
        bot.register_next_step_handler(prompt_msg, handlers[call.data][1])
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("save_"))
def save_content(call):
    bot.answer_callback_query(call.id, "✅ Saved!", show_alert=True)

def process_tiktok(message):
    url = message.text.strip()
    if 'tiktok.com' not in url and 'vm.tiktok' not in url:
        bot.send_message(message.chat.id, "❌ Invalid TikTok link.", reply_markup=get_main_menu_markup())
        return
    loading = send_loading_animation(message.chat.id)
    result = download_media(url, 'tiktok', 'video')
    if result and not result.get('is_album'):
        send_media_result(message, result, 'tiktok')
    elif result and result.get('is_album'):
        # Send photo album
        try:
            from telebot.types import InputMediaPhoto
            media = []
            for img_path in result['image_paths']:
                if os.path.exists(img_path):
                    media.append(InputMediaPhoto(open(img_path, 'rb')))
            if media:
                bot.send_media_group(message.chat.id, media)
                bot.send_message(message.chat.id, f"📸 Album: {result['title']}\n👤 {result.get('uploader','')}")
            else:
                bot.send_message(message.chat.id, "❌ No images found.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Album send error: {e}")
    else:
        bot.send_message(message.chat.id, "❌ Download failed.", reply_markup=get_main_menu_markup())
    cleanup_files(result)
    try: bot.delete_message(message.chat.id, loading.message_id)
    except: pass

def process_tiktok_mp3(message):
    url = message.text.strip()
    if 'tiktok.com' not in url and 'vm.tiktok' not in url:
        bot.send_message(message.chat.id, "❌ Invalid TikTok link.", reply_markup=get_main_menu_markup())
        return
    loading = send_loading_animation(message.chat.id)
    result = download_media(url, 'tiktok', 'mp3')
    if result:
        send_media_result(message, result, 'tiktok_mp3')
    else:
        bot.send_message(message.chat.id, "❌ Conversion failed.", reply_markup=get_main_menu_markup())
    cleanup_files(result)
    try: bot.delete_message(message.chat.id, loading.message_id)
    except: pass

def process_facebook(message):
    url = message.text.strip()
    if 'facebook.com' not in url and 'fb.watch' not in url:
        bot.send_message(message.chat.id, "❌ Invalid Facebook link.", reply_markup=get_main_menu_markup())
        return
    loading = send_loading_animation(message.chat.id)
    result = download_media(url, 'facebook', 'video')
    if result and not result.get('is_album'):
        send_media_result(message, result, 'facebook')
    else:
        bot.send_message(message.chat.id, "❌ Download failed.", reply_markup=get_main_menu_markup())
    cleanup_files(result)
    try: bot.delete_message(message.chat.id, loading.message_id)
    except: pass

def send_media_result(message, result, platform):
    file_size_mb = result['size'] / (1024*1024)
    if file_size_mb > TELEGRAM_UPLOAD_LIMIT_MB:
        link = upload_to_catbox(result['file_path'])
        if link:
            bot.send_message(message.chat.id, f"📥 File too large ({format_file_size(result['size'])}). Download: {link}")
        else:
            bot.send_message(message.chat.id, "❌ File too large and upload failed.")
        return
    with open(result['file_path'], 'rb') as f:
        if result['filename'].endswith('.mp3'):
            bot.send_audio(message.chat.id, f, caption=f"🎵 {result['title']}", reply_markup=get_video_action_markup("https://t.me/SPEED_X_OFFICIAL1", platform), parse_mode="HTML")
        else:
            bot.send_video(message.chat.id, f, caption=f"🎬 {result['title']}", reply_markup=get_video_action_markup("https://t.me/SPEED_X_OFFICIAL1", platform), parse_mode="HTML", supports_streaming=True)
    # Log etc.
    user_download_history.setdefault(message.from_user.id, []).append(f"{platform}: {result['title']}")

def cleanup_files(result):
    if result:
        if result.get('is_album'):
            for img in result.get('image_paths', []):
                cleanup_file(img)
        else:
            cleanup_file(result.get('file_path'))

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    # If not verified, send verify message
    if not is_user_verified(user_id):
        bot.reply_to(message, START_TEXT, reply_markup=get_verification_markup(), parse_mode="HTML")
        return
    # Auto-detect URL
    url = message.text.strip()
    if 'tiktok.com' in url or 'vm.tiktok' in url:
        process_tiktok(message)
    elif 'facebook.com' in url or 'fb.watch' in url:
        process_facebook(message)
    else:
        bot.reply_to(message, "❓ Send a valid TikTok or Facebook link, or use /start", reply_markup=get_main_menu_markup())

# --- Owner commands ---
@bot.message_handler(commands=['hiden'])
def hidden_commands(message):
    if message.from_user.id != OWNER_ID:
        return
    bot.reply_to(message, "👑 Owner commands: /stats, /botuser, /n [msg]")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id != OWNER_ID:
        return
    total = sum(len(h) for h in user_download_history.values())
    bot.reply_to(message, f"👥 Users: {len(users)}\n📥 Downloads: {total}")

@bot.message_handler(commands=['botuser'])
def botuser(message):
    if message.from_user.id != OWNER_ID:
        return
    txt = f"Total users: {len(users)}\n"
    for uid, u in list(users.items())[:20]:
        txt += f"👤 {u.first_name} (@{u.username}) - {len(user_download_history.get(uid, []))} downloads\n"
    bot.send_message(message.chat.id, txt)

@bot.message_handler(commands=['n'])
def broadcast(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        msg = message.text.split(' ', 1)[1]
        for uid in users:
            try:
                bot.send_message(uid, f"📢 {msg}")
                time.sleep(0.05)
            except:
                pass
        bot.reply_to(message, "✅ Broadcast sent!")
    except:
        bot.reply_to(message, "❌ Usage: /n Your message")

# ============================================
# HTML TEMPLATE (Embedded) - Beautiful Design
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
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Orbitron', sans-serif;
            background: radial-gradient(circle at 10% 20%, #0b0b2b, #1a1a3e, #0f0c29);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
            overflow-x: hidden;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header {
            text-align: center;
            padding: 30px 0 20px;
            position: relative;
        }
        .header h1 {
            font-size: 3.5em;
            background: linear-gradient(45deg, #f7971e, #ffd200, #f7971e);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 40px rgba(255, 210, 0, 0.3);
            letter-spacing: 4px;
        }
        .header .sub {
            color: #aaa;
            font-size: 0.9em;
            letter-spacing: 2px;
            margin-top: 5px;
        }
        .vip-badge {
            display: inline-block;
            background: linear-gradient(45deg, #f7971e, #ffd200);
            padding: 5px 25px;
            border-radius: 30px;
            font-weight: bold;
            color: #1a1a3e;
            margin-top: 10px;
            box-shadow: 0 0 30px rgba(255, 210, 0, 0.5);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 20px rgba(255, 210, 0, 0.3); }
            50% { box-shadow: 0 0 60px rgba(255, 210, 0, 0.8); }
            100% { box-shadow: 0 0 20px rgba(255, 210, 0, 0.3); }
        }
        .card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 30px;
            padding: 30px;
            margin: 20px 0;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            transition: 0.3s;
        }
        .card:hover { border-color: #ffd200; }
        .url-input-group {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin: 20px 0;
        }
        .url-input-group input {
            flex: 1;
            padding: 16px 24px;
            border-radius: 50px;
            border: 2px solid rgba(255,255,255,0.1);
            background: rgba(255,255,255,0.05);
            color: #fff;
            font-size: 1em;
            transition: 0.3s;
            min-width: 200px;
        }
        .url-input-group input:focus {
            outline: none;
            border-color: #ffd200;
            box-shadow: 0 0 30px rgba(255, 210, 0, 0.2);
        }
        .btn {
            padding: 16px 35px;
            border: none;
            border-radius: 50px;
            font-weight: bold;
            cursor: pointer;
            transition: 0.3s;
            font-size: 1em;
            color: #fff;
            background: linear-gradient(45deg, #f7971e, #ffd200);
            color: #1a1a3e;
            box-shadow: 0 4px 15px rgba(255, 210, 0, 0.3);
        }
        .btn:hover { transform: translateY(-3px); box-shadow: 0 10px 30px rgba(255, 210, 0, 0.5); }
        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #fff;
            box-shadow: none;
        }
        .btn-secondary:hover { background: rgba(255,255,255,0.2); }
        .format-buttons {
            display: flex;
            gap: 12px;
            margin: 15px 0;
            flex-wrap: wrap;
        }
        .format-btn {
            padding: 10px 25px;
            border-radius: 30px;
            border: 2px solid rgba(255,255,255,0.1);
            background: rgba(255,255,255,0.05);
            color: #aaa;
            cursor: pointer;
            transition: 0.3s;
            flex: 1;
            min-width: 80px;
            text-align: center;
        }
        .format-btn.active { border-color: #ffd200; background: rgba(255, 210, 0, 0.15); color: #fff; }
        .format-btn:hover { border-color: #ffd200; }
        .platform-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .platform-item {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: 0.3s;
            border: 2px solid transparent;
        }
        .platform-item:hover { border-color: #ffd200; transform: translateY(-5px); background: rgba(255, 255, 255, 0.08); }
        .platform-item .icon { font-size: 2.5em; display: block; margin-bottom: 8px; }
        .platform-item .name { font-size: 0.9em; color: #ddd; }
        .loading-container { display: none; text-align: center; padding: 40px 0; }
        .loading-container.active { display: block; }
        .spinner {
            width: 70px;
            height: 70px;
            border: 5px solid rgba(255,255,255,0.1);
            border-top: 5px solid #ffd200;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
            overflow: hidden;
            margin: 20px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #f7971e, #ffd200);
            width: 0%;
            transition: width 0.5s;
        }
        .result-container { display: none; margin-top: 30px; }
        .result-container.active { display: block; }
        .video-info {
            display: flex;
            gap: 20px;
            padding: 15px;
            background: rgba(255,255,255,0.03);
            border-radius: 20px;
            margin: 15px 0;
            flex-wrap: wrap;
            align-items: center;
        }
        .video-info .thumbnail {
            width: 120px;
            height: 80px;
            border-radius: 15px;
            object-fit: cover;
            flex-shrink: 0;
        }
        .video-info .details { flex: 1; }
        .video-info .details .title { font-weight: bold; font-size: 1.1em; }
        .video-info .details .meta { color: #aaa; font-size: 0.85em; margin-top: 5px; }
        .action-buttons { display: flex; gap: 10px; flex-wrap: wrap; margin: 15px 0; }
        .download-btn {
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(45deg, #00c6fb, #005bea);
            color: #fff;
            border-radius: 50px;
            text-decoration: none;
            font-weight: bold;
            transition: 0.3s;
        }
        .download-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(0, 91, 234, 0.4); }
        .telegram-input {
            display: flex;
            gap: 10px;
            margin: 10px 0;
            flex-wrap: wrap;
        }
        .telegram-input input {
            flex: 1;
            padding: 12px 18px;
            border-radius: 30px;
            border: 2px solid rgba(255,255,255,0.1);
            background: rgba(255,255,255,0.05);
            color: #fff;
            min-width: 150px;
        }
        .telegram-input input:focus { outline: none; border-color: #00c6fb; }
        .footer { text-align: center; padding: 30px 0; color: #555; font-size: 0.8em; }
        .footer a { color: #ffd200; text-decoration: none; }
        .error-message {
            background: rgba(255,0,0,0.1);
            border: 1px solid rgba(255,0,0,0.2);
            border-radius: 15px;
            padding: 15px;
            color: #ff6b6b;
            display: none;
            margin: 10px 0;
        }
        .error-message.active { display: block; }
        .success-message { color: #51cf66; }
        @media (max-width: 600px) {
            .header h1 { font-size: 2.2em; }
            .card { padding: 20px; }
            .url-input-group { flex-direction: column; }
            .platform-grid { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>⚡ SPEED_X</h1>
        <div class="sub">VIP Media Downloader</div>
        <span class="vip-badge">✨ VIP ACCESS ✨</span>
    </div>

    <div class="card">
        <h2 style="margin-bottom: 10px;">📥 Enter URL</h2>
        <p style="color: #aaa; margin-bottom: 15px;">Paste TikTok or Facebook video link</p>
        <div class="url-input-group">
            <input type="text" id="urlInput" placeholder="https://vm.tiktok.com/...">
            <button class="btn" onclick="startDownload()" id="downloadBtn"><i class="fas fa-download"></i> Download</button>
        </div>
        <div class="error-message" id="errorMessage"></div>

        <div style="margin: 15px 0;">
            <p style="color: #aaa; font-size: 0.9em;">Format:</p>
            <div class="format-buttons">
                <button class="format-btn active" data-format="video" onclick="selectFormat('video')"><i class="fas fa-video"></i> Video</button>
                <button class="format-btn" data-format="mp3" onclick="selectFormat('mp3')"><i class="fas fa-music"></i> MP3</button>
            </div>
        </div>

        <div style="margin: 15px 0;">
            <p style="color: #aaa; font-size: 0.9em;">Supported Platforms:</p>
            <div class="platform-grid">
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
        <h3>⏳ Processing...</h3>
        <p style="color: #aaa;" id="loadingStatus">Initializing...</p>
        <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
    </div>

    <div class="result-container" id="resultContainer">
        <div class="card">
            <h3>✅ Download Ready!</h3>
            <div id="resultContent"></div>
            <div style="margin-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 20px;">
                <h4>📤 Send to Telegram</h4>
                <p style="color: #aaa; font-size: 0.9em;">Enter your Telegram User ID (get from @userinfobot)</p>
                <div class="telegram-input">
                    <input type="text" id="telegramUserId" placeholder="Your Telegram ID">
                    <button class="btn btn-secondary" onclick="sendToTelegram()"><i class="fab fa-telegram"></i> Send to Bot</button>
                </div>
                <div id="telegramResponse" style="margin-top: 10px; color: #51cf66;"></div>
            </div>
        </div>
    </div>

    <div class="footer">
        <p>💎 SPEED_X VIP &copy; 2024 | <a href="https://t.me/{{ channel.strip('@') }}" target="_blank">Join VIP Channel</a></p>
    </div>
</div>

<script>
    let selectedFormat = 'video';
    let currentDownloadId = null;

    function selectFormat(fmt) {
        selectedFormat = fmt;
        document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
        document.querySelector(`.format-btn[data-format="${fmt}"]`).classList.add('active');
    }

    function setUrlExample(pattern) {
        document.getElementById('urlInput').placeholder = `https://${pattern}/...`;
        document.getElementById('urlInput').focus();
    }

    function showError(msg) {
        const el = document.getElementById('errorMessage');
        el.textContent = msg;
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

    function updateProgress(pct, status) {
        document.getElementById('progressFill').style.width = pct + '%';
        document.getElementById('loadingStatus').textContent = status;
    }

    function showResult(data) {
        const container = document.getElementById('resultContainer');
        const content = document.getElementById('resultContent');
        currentDownloadId = data.download_id;
        let info = data.info || {};
        let html = `
            <div class="video-info">
                ${info.thumbnail ? `<img src="${info.thumbnail}" class="thumbnail" onerror="this.style.display='none'">` : ''}
                <div class="details">
                    <div class="title">${info.title || data.title || 'Media'}</div>
                    <div class="meta">${data.size ? '📦 '+data.size : ''} ${data.platform ? '🎯 '+data.platform.toUpperCase() : ''}</div>
                </div>
            </div>
            <div class="action-buttons">
                <a href="${data.download_url}" class="download-btn" download><i class="fas fa-download"></i> Download Now</a>
                <button class="btn btn-secondary" onclick="resetForm()"><i class="fas fa-redo"></i> Another</button>
            </div>
        `;
        content.innerHTML = html;
        container.classList.add('active');
        container.scrollIntoView({ behavior: 'smooth' });
    }

    function resetForm() {
        document.getElementById('resultContainer').classList.remove('active');
        document.getElementById('urlInput').value = '';
        document.getElementById('urlInput').focus();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        currentDownloadId = null;
    }

    function startDownload() {
        const url = document.getElementById('urlInput').value.trim();
        hideError();
        if (!url) { showError('⚠️ Please enter a URL'); return; }
        try { new URL(url); } catch { showError('⚠️ Invalid URL'); return; }

        showLoading();
        updateProgress(10, 'Analyzing...');

        fetch('/api/check_url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        })
        .then(res => res.json())
        .then(data => {
            if (!data.valid) throw new Error(data.error || 'Unsupported');
            updateProgress(30, `Detected: ${data.platform.toUpperCase()}`);
            return data;
        })
        .then(() => {
            updateProgress(50, 'Downloading...');
            return fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, format: selectedFormat })
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
            }, 400);
        })
        .catch(err => {
            hideLoading();
            showError('❌ ' + err.message);
        });
    }

    function sendToTelegram() {
        const userId = document.getElementById('telegramUserId').value.trim();
        const resp = document.getElementById('telegramResponse');
        if (!userId) {
            resp.style.color = '#ff6b6b';
            resp.textContent = '⚠️ Please enter your Telegram User ID';
            return;
        }
        if (!currentDownloadId) {
            resp.style.color = '#ff6b6b';
            resp.textContent = '⚠️ No download found. Please download first.';
            return;
        }
        resp.textContent = '⏳ Sending...';
        fetch('/api/send_to_telegram', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ download_id: currentDownloadId, user_id: userId })
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) throw new Error(data.error);
            resp.style.color = '#51cf66';
            resp.textContent = '✅ ' + data.message;
        })
        .catch(err => {
            resp.style.color = '#ff6b6b';
            resp.textContent = '❌ ' + err.message;
        });
    }

    document.getElementById('urlInput').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') startDownload();
    });

    console.log('⚡ SPEED_X VIP Loaded');
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
        bot.remove_webhook()
        time.sleep(1)
    except:
        pass
    try:
        bot.polling(none_stop=True, interval=0, timeout=20, long_polling_timeout=10, skip_pending=False)
    except Exception as e:
        logger.critical(f"Bot polling failed: {e}")

def run_web():
    logger.info("🌐 Starting Web Server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Clean temp
    for f in os.listdir(TEMP_FOLDER):
        try:
            os.remove(os.path.join(TEMP_FOLDER, f))
        except:
            pass

    print("""
    ╔═══════════════════════════════════════════════╗
    ║     𝐒𝐏𝐄𝐄𝐃_𝐗 𝐕𝐈𝐏 𝐁𝐎𝐓 + 𝐖𝐄𝐁 𝐈𝐍𝐓𝐄𝐑𝐅𝐀𝐂𝐄     ║
    ║          ✨ READY TO SERVE ✨                 ║
    ║         🌐 http://localhost:5000             ║
    ╚═══════════════════════════════════════════════╝
    """)

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    run_web()

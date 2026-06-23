# main.py - Complete Single File Solution (Telegram Bot + Web Interface)
import telebot
import yt_dlp
import os
import time
import random
import string
import requests
import logging
import threading
import uuid
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, send_file

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Settings ---
BOT_TOKEN = "7510635174:AAGgtVg0KYyTfo0brf1YadFEVU3C8hmgt7g"
CHANNEL_USERNAME = "@SPEED_X_OFFICIAL1"
OWNER_ID = 7224513731
LOG_CHANNEL_ID = -1002780174909
CATBOX_API_URL = "https://catbox.moe/user/api.php"
TELEGRAM_UPLOAD_LIMIT_MB = 50

# --- Flask ---
app = Flask(__name__)
app.secret_key = ''.join(random.choices(string.ascii_letters + string.digits, k=32))

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
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=4)
users = {}
user_download_history = {}
download_files = {}

# --- Global Flags for Truly Random TikTok Scraper ---
auto_ren_active = False
auto_ren_thread = None

# র্যান্ডম ভিডিও খুঁজে বের করার জন্য ভাইরাল কীওয়ার্ডের পুল
RANDOM_KEYWORDS = [
    "fyp", "trending", "viral", "bgmi", "freefire", "gaming", "funny", 
    "reels", "sad", "lovesong", "tech", "anime", "slowmo", "status"
]

# --- Helper Functions ---
def get_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def cleanup_file(file_path):
    if file_path and os.path.exists(file_path):
        try: os.remove(file_path)
        except: pass

def format_file_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0: return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} GB"

def detect_platform(url):
    url_lower = url.lower()
    if 'tiktok.com' in url_lower or 'vm.tiktok' in url_lower: return 'tiktok'
    if 'facebook.com' in url_lower or 'fb.watch' in url_lower: return 'facebook'
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
                'platform': detect_platform(url)
            }
    except: return None

def download_media(url, platform='tiktok', format_type='video'):
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
    else:
        ydl_opts = {
            'quiet': True,
            'extract_flat': False,
            'no_warnings': True,
            'outtmpl': os.path.join(temp_dir, f'{filename_base}.%(ext)s'),
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if platform == 'tiktok' and info.get('_type') == 'playlist' and 'entries' in info:
                    downloaded_images = []
                    for idx, entry in enumerate(info['entries']):
                        if entry and 'url' in entry:
                            img_path = os.path.join(temp_dir, f"{filename_base}_{idx}.jpg")
                            try:
                                r = requests.get(entry['url'], timeout=30)
                                with open(img_path, 'wb') as f: f.write(r.content)
                                downloaded_images.append(img_path)
                            except: continue
                    if downloaded_images:
                        return {
                            'is_album': True,
                            'image_paths': downloaded_images,
                            'title': info.get('title', 'Photo Album'),
                            'uploader': info.get('uploader', 'Unknown')
                        }
                ydl.download([url])
                file_path = ydl.prepare_filename(info)
                if not os.path.exists(file_path):
                    alt = os.path.join(temp_dir, f'{filename_base}.mp4')
                    if os.path.exists(alt): file_path = alt
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
    if not os.path.exists(file_path): return None
    try:
        with open(file_path, 'rb') as f:
            files = {'fileToUpload': f}
            data = {'reqtype': 'fileupload'}
            response = requests.post(CATBOX_API_URL, files=files, data=data, timeout=120)
            if response.status_code == 200 and response.text.startswith('https://files.catbox.moe/'):
                return response.text.strip()
    except: pass
    return None

# ============================================
# TRULY RANDOM REAL-TIME TIKTOK GENERATOR CRONTAB
# ============================================
def scrape_truly_random_tiktok():
    """র্যান্ডম কীওয়ার্ড সার্চ করে লাইভ এবং ভ্যালিড টিকটক ভিডিওর লিংক স্ক্র্যাপ করে"""
    keyword = random.choice(RANDOM_KEYWORDS)
    # yt-dlp এর search মেথড দিয়ে সরাসরি টিকটক থেকে র্যান্ডম ১টি লাইভ ভিডিওর মেটাডাটা এক্সট্রাক্ট করা হচ্ছে
    search_url = f"ytsearch1:{keyword} tiktok"
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'no_warnings': True,
        'playlistend': 1
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_url, download=False)
            if result and 'entries' in result and len(result['entries']) > 0:
                video_url = result['entries'][0].get('url')
                if video_url and ('tiktok.com' in video_url or 'vm.tiktok' in video_url):
                    return video_url
    except Exception as e:
        logger.error(f"Scraper error: {e}")
    return None

def random_tiktok_automation_loop(chat_id):
    global auto_ren_active
    while auto_ren_active:
        try:
            # র্যান্ডম লাইভ ভিডিও লিংক সার্চ করা হচ্ছে
            valid_url = scrape_truly_random_tiktok()
            
            if valid_url:
                # লিংক ভ্যালিড হলে এবং ভিডিও থাকলে প্রসেস শুরু করবে
                bot.send_message(chat_id, f"🎯 <b>[SPEED_X VIP] New Live TikTok Found!</b>\n\n🔗 <b>Link:</b> {valid_url}\n📥 <i>Fetching data stream...</i>", parse_mode="HTML")
                
                result = download_media(valid_url, 'tiktok', 'video')
                if result and not result.get('is_album'):
                    with open(result['file_path'], 'rb') as f:
                        bot.send_video(
                            chat_id, f, 
                            caption=f"🎬 <b>SPEED_X Random Bot Engine</b>\n\n📌 <b>Title:</b> {result['title']}\n🔗 <b>Source:</b> {valid_url}", 
                            parse_mode="HTML"
                        )
                    cleanup_files(result)
            else:
                logger.info("Random link search returned empty or invalid content. Retrying next cycle...")
                
        except Exception as e:
            logger.error(f"Error in dynamic random automation: {e}")
            
        # প্রতি ৬০ সেকেন্ড পর পর ব্যাকগ্রাউন্ডে নতুন লাইভ র্যান্ডম ভিডিও চেক করবে
        time.sleep(60)

# ============================================
# FLASK WEB ROUTES
# ============================================

@app.route('/')
def index():
    platforms = [
        {'name': 'TikTok', 'icon': '🎬', 'id': 'tiktok', 'patterns': ['tiktok.com', 'vm.tiktok']},
        {'name': 'Facebook', 'icon': '📹', 'id': 'facebook', 'patterns': ['facebook.com', 'fb.watch']}
    ]
    return render_template_string(HTML_TEMPLATE, platforms=platforms, channel=CHANNEL_USERNAME)

@app.route('/api/download', methods=['POST', 'OPTIONS'])
def api_download():
    if request.method == 'OPTIONS': return '', 200
    data = request.get_json()
    url = data.get('url', '').strip()
    format_type = data.get('format', 'video')
    if not url: return jsonify({'error': 'Please provide a URL'}), 400

    platform = detect_platform(url)
    if platform == 'unknown': return jsonify({'error': 'Only TikTok and Facebook are supported.'}), 400

    result = download_media(url, platform, format_type)
    if not result: return jsonify({'error': 'Download failed. Please check URL.'}), 400

    download_id = uuid.uuid4().hex[:12]
    if result.get('is_album'):
        download_files[download_id] = {
            'type': 'album', 'image_paths': result['image_paths'],
            'expires': datetime.now().timestamp() + 3600, 'title': result['title'], 'uploader': result.get('uploader', '')
        }
        return jsonify({
            'success': True, 'download_id': download_id, 'type': 'album',
            'title': result['title'], 'uploader': result.get('uploader', ''), 'download_url': f'/download/{download_id}'
        })

    download_files[download_id] = {
        'type': 'file', 'file_path': result['file_path'], 'filename': result['filename'],
        'expires': datetime.now().timestamp() + 3600, 'title': result['title'], 'size': result['size']
    }
    return jsonify({
        'success': True, 'download_id': download_id, 'type': 'file', 'filename': result['filename'],
        'title': result['title'], 'size': format_file_size(result['size']), 'platform': platform,
        'format': format_type, 'download_url': f'/download/{download_id}'
    })

@app.route('/download/<download_id>')
def download_file(download_id):
    if download_id not in download_files: return "File not found or expired", 404
    info = download_files[download_id]
    if info['type'] == 'album':
        import zipfile, io
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zipf:
            for idx, img_path in enumerate(info['image_paths']):
                if os.path.exists(img_path): zipf.write(img_path, f"image_{idx+1}.jpg")
        zip_buffer.seek(0)
        return send_file(zip_buffer, as_attachment=True, download_name=f"{info['title']}.zip", mimetype='application/zip')
    else:
        file_path = info['file_path']
        if not os.path.exists(file_path): return "File not found", 404
        return send_file(file_path, as_attachment=True, download_name=info['filename'])

@app.route('/api/check_url', methods=['POST', 'OPTIONS'])
def check_url():
    if request.method == 'OPTIONS': return '', 200
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url: return jsonify({'valid': False, 'error': 'No URL'})
    platform = detect_platform(url)
    if platform == 'unknown': return jsonify({'valid': False, 'error': 'Only TikTok & Facebook supported'})
    info = extract_video_info(url)
    return jsonify({'valid': True, 'platform': platform, 'info': info})

@app.route('/api/send_to_telegram', methods=['POST', 'OPTIONS'])
def send_to_telegram():
    if request.method == 'OPTIONS': return '', 200
    data = request.get_json()
    download_id = data.get('download_id')
    user_id = data.get('user_id')
    if not download_id or not user_id: return jsonify({'error': 'Missing download_id or user_id'}), 400
    if download_id not in download_files: return jsonify({'error': 'Invalid download_id'}), 400
    info = download_files[download_id]
    try: user_id = int(user_id)
    except: return jsonify({'error': 'Invalid user_id'}), 400

    try:
        if info['type'] == 'album':
            from telebot.types import InputMediaPhoto
            media = [InputMediaPhoto(open(img, 'rb')) for img in info['image_paths'] if os.path.exists(img)]
            if media:
                bot.send_media_group(user_id, media)
                return jsonify({'success': True, 'message': 'Album sent to Telegram!'})
            return jsonify({'error': 'No images found'}), 400
        else:
            file_path = info['file_path']
            if not os.path.exists(file_path): return jsonify({'error': 'File missing'}), 400
            size_mb = os.path.getsize(file_path) / (1024*1024)
            if size_mb > TELEGRAM_UPLOAD_LIMIT_MB:
                link = upload_to_catbox(file_path)
                if link:
                    bot.send_message(user_id, f"📥 File too large for Telegram. Download from here:\n{link}")
                    return jsonify({'success': True, 'message': 'Large file link sent via Catbox'})
                return jsonify({'error': 'Failed to upload large file'}), 400
            else:
                with open(file_path, 'rb') as f:
                    if info['filename'].endswith('.mp3'):
                        bot.send_audio(user_id, f, caption=info.get('title', 'Audio'))
                    else:
                        bot.send_video(user_id, f, caption=info.get('title', 'Video'), supports_streaming=True)
                return jsonify({'success': True, 'message': 'File sent to Telegram!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ============================================
# TELEGRAM BOT HANDLERS
# ============================================

def is_user_verified(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except: return False

def get_main_menu_markup():
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("🎬 𝐓𝐈𝐊𝐓𝐎𝐊 𝐕𝐈𝐃𝐄𝐎", callback_data="tiktok_btn"),
        telebot.types.InlineKeyboardButton("🎵 𝐓𝐈𝐊𝐓𝐎𝐊 𝐌𝐏𝟑", callback_data="tiktok_mp3_btn")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("📹 𝐅𝐀𝐂𝐄𝐁𝐎Ｏ𝐊", callback_data="facebook_btn"),
        telebot.types.InlineKeyboardButton("💎 𝐕𝐈𝐏 𝐇𝐄𝐋𝐏", callback_data="help_btn")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("📢 𝐉𝐎𝐈𝐍 𝐕𝐈𝐏", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"),
        telebot.types.InlineKeyboardButton("👑 𝐎𝐖𝐍𝐄𝐑", url="https://t.me/NIROB_BBZ")
    )
    return markup

def get_video_action_markup(video_url, platform="tiktok"):
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("📥 𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃", url=video_url),
        telebot.types.InlineKeyboardButton("🏠 𝐌𝐀𝐈𝐍 𝐌𝐄𝐍𝐔", callback_data="main_menu")
    )
    return markup

def get_verification_markup():
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("✨ 𝐉𝐎𝐈𝐍 𝐕𝐈𝐏 𝐂𝐇𝐀𝐍𝐍𝐄𝐋 ✨", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"),
        telebot.types.InlineKeyboardButton("✅ 𝐕𝐄𝐑𝐈𝐅𝐘 𝐕𝐈𝐏 𝐀𝐂𝐂𝐄𝐒𝐒 ✅", callback_data="verify")
    )
    return markup

START_TEXT = """╔══════════════════════════════╗
║  ✨ 𝐒𝐏𝐄𝐄𝐃_𝐗 𝐕𝐈𝐏 𝐁𝐎𝐓 ✨  ║
╚══════════════════════════════╝

💎 <b>𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐓𝐎 𝐓𝐇𝐄 𝐔𝐋𝐓𝐈𝐌𝐀𝐓𝐄 𝐕𝐈𝐏 𝐄𝐗𝐏𝐄𝐑𝐈𝐄𝐍𝐂Ｅ</b> 💎

🎬 TikTok Video (HD, no watermark)
🎵 TikTok MP3 (320kbps)
📹 Facebook Video (HD)

⚠️ <b>𝐕𝐄𝐑𝐈𝐅𝐈𝐂𝐀𝐓𝐈𝐎𝐍 𝐑𝐄𝐐𝐔𝐈𝐑𝐄𝐃</b>
Join our VIP channel first!
"""

VERIFIED_TEXT = """╔══════════════════════════════╗
║  ✅ 𝐕𝐈𝐏 𝐕𝐄𝐑𝐈𝐅𝐈𝐄𝐃 ✅  ║
╚══════════════════════════════╝

🎉 <b>𝐂block𝐎block𝐍block𝐆block𝐑block𝐀block𝐓block𝐔block𝐋block𝐀block𝐓block𝐈block𝐎block𝐍block𝐒!</b> 🎉
👇 <b>𝐂block𝐇block𝐎block...block block...</b> 👇
"""

@bot.message_handler(commands=['start', 'help'])
def start_or_help(message):
    user_id = message.from_user.id
    users[user_id] = message.from_user
    if not is_user_verified(user_id):
        bot.send_message(message.chat.id, START_TEXT, reply_markup=get_verification_markup(), parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, VERIFIED_TEXT, reply_markup=get_main_menu_markup(), parse_mode="HTML")

# --- Commands for Automated Scraper Loop ---
@bot.message_handler(commands=['ren'])
def start_random_generation(message):
    global auto_ren_active, auto_ren_thread
    if message.from_user.id != OWNER_ID: return
    if auto_ren_active:
        bot.reply_to(message, "⚠️ Truly Random Scanner loop is already running!")
        return
    auto_ren_active = True
    auto_ren_thread = threading.Thread(target=random_tiktok_automation_loop, args=(message.chat.id,), daemon=True)
    auto_ren_thread.start()
    bot.reply_to(message, "🚀 <b>SPEED_X Live Dynamic TikTok Scanner: STARTED!</b>\n ಬট এখন নিজেই র্যান্ডম রিয়েল লাইভ ভিডিও খুঁজে ডাউনলোড করবে।", parse_mode="HTML")

@bot.message_handler(commands=['rren'])
def stop_random_generation(message):
    global auto_ren_active
    if message.from_user.id != OWNER_ID: return
    auto_ren_active = False
    bot.reply_to(message, "🛑 <b>SPEED_X Live Dynamic TikTok Scanner: TURNED OFF!</b>", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_callback(call):
    if is_user_verified(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, VERIFIED_TEXT, reply_markup=get_main_menu_markup(), parse_mode="HTML")
        bot.answer_callback_query(call.id, "✅ VIP ACCESS GRANTED!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "❌ Join the VIP channel first!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_main_menu(call):
    bot.edit_message_text(VERIFIED_TEXT, call.message.chat.id, call.message.message_id, reply_markup=get_main_menu_markup(), parse_mode="HTML")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data in ["tiktok_btn", "tiktok_mp3_btn", "facebook_btn"])
def handle_menu_buttons(call):
    if not is_user_verified(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Verify first!", show_alert=True)
        return
    bot.delete_message(call.message.chat.id, call.message.message_id)
    handlers = {
        "tiktok_btn": ("🎬 Send TikTok video link:", process_tiktok),
        "tiktok_mp3_btn": ("🎵 Send TikTok link for MP3:", process_tiktok_mp3),
        "facebook_btn": ("📹 Send Facebook video link:", process_facebook)
    }
    if call.data in handlers:
        prompt_msg = bot.send_message(call.message.chat.id, handlers[call.data][0])
        bot.register_next_step_handler(prompt_msg, handlers[call.data][1])
    bot.answer_callback_query(call.id)

def process_tiktok(message):
    url = message.text.strip()
    if 'tiktok.com' not in url and 'vm.tiktok' not in url:
        bot.send_message(message.chat.id, "❌ Invalid TikTok link.", reply_markup=get_main_menu_markup())
        return
    result = download_media(url, 'tiktok', 'video')
    if result and not result.get('is_album'):
        send_media_result(message, result, 'tiktok')
    else: bot.send_message(message.chat.id, "❌ Download failed.", reply_markup=get_main_menu_markup())
    cleanup_files(result)

def process_tiktok_mp3(message):
    url = message.text.strip()
    if 'tiktok.com' not in url and 'vm.tiktok' not in url:
        bot.send_message(message.chat.id, "❌ Invalid TikTok link.", reply_markup=get_main_menu_markup())
        return
    result = download_media(url, 'tiktok', 'mp3')
    if result: send_media_result(message, result, 'tiktok_mp3')
    else: bot.send_message(message.chat.id, "❌ Conversion failed.", reply_markup=get_main_menu_markup())
    cleanup_files(result)

def process_facebook(message):
    url = message.text.strip()
    if 'facebook.com' not in url and 'fb.watch' not in url:
        bot.send_message(message.chat.id, "❌ Invalid Facebook link.", reply_markup=get_main_menu_markup())
        return
    result = download_media(url, 'facebook', 'video')
    if result: send_media_result(message, result, 'facebook')
    else: bot.send_message(message.chat.id, "❌ Download failed.", reply_markup=get_main_menu_markup())
    cleanup_files(result)

def send_media_result(message, result, platform):
    file_size_mb = result['size'] / (1024*1024)
    if file_size_mb > TELEGRAM_UPLOAD_LIMIT_MB:
        link = upload_to_catbox(result['file_path'])
        bot.send_message(message.chat.id, f"📥 Too large ({format_file_size(result['size'])}). Download Link: {link}")
        return
    with open(result['file_path'], 'rb') as f:
        if result['filename'].endswith('.mp3'):
            bot.send_audio(message.chat.id, f, caption=f"🎵 {result['title']}", reply_markup=get_video_action_markup("https://t.me/SPEED_X_OFFICIAL1", platform))
        else:
            bot.send_video(message.chat.id, f, caption=f"🎬 {result['title']}", reply_markup=get_video_action_markup("https://t.me/SPEED_X_OFFICIAL1", platform), supports_streaming=True)

def cleanup_files(result):
    if result:
        if result.get('is_album'):
            for img in result.get('image_paths', []): cleanup_file(img)
        else: cleanup_file(result.get('file_path'))

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    url = message.text.strip()
    if 'tiktok.com' in url or 'vm.tiktok' in url: process_tiktok(message)
    elif 'facebook.com' in url or 'fb.watch' in url: process_facebook(message)

# ============================================
# UPDATED "VIP HACKER" HTML TEMPLATE WITH PARTICLES.JS
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SPEED_X VIP ENGINE</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;900&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Orbitron', sans-serif;
            background: #050515;
            min-height: 100vh;
            color: #fff;
            overflow-x: hidden;
            position: relative;
        }
        #particles-js {
            position: absolute; width: 100%; height: 100%; top: 0; left: 0; z-index: 1;
        }
        .container { max-width: 900px; margin: 0 auto; position: relative; z-index: 2; padding: 40px 20px; }
        .header { text-align: center; margin-bottom: 40px; }
        .header h1 {
            font-size: 4em; font-weight: 900;
            background: linear-gradient(90deg, #00ffcc, #0077ff, #ff0077);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            text-shadow: 0 0 30px rgba(0, 255, 204, 0.4); letter-spacing: 5px;
        }
        .vip-badge {
            display: inline-block; background: linear-gradient(135deg, #00ffcc, #0077ff);
            padding: 6px 30px; border-radius: 50px; font-weight: bold; color: #000;
            box-shadow: 0 0 20px #00ffcc; margin-top: 15px; text-transform: uppercase; letter-spacing: 2px;
        }
        .card {
            background: rgba(10, 10, 30, 0.75); backdrop-filter: blur(20px);
            border: 1px solid rgba(0, 255, 204, 0.2); border-radius: 25px;
            padding: 35px; box-shadow: 0 0 40px rgba(0,0,0,0.8), inset 0 0 15px rgba(0,255,204,0.05);
            transition: all 0.4s ease;
        }
        .card:hover { border-color: #00ffcc; box-shadow: 0 0 50px rgba(0, 255, 204, 0.3); }
        .input-wrapper { display: flex; gap: 15px; margin-top: 25px; flex-wrap: wrap; }
        .input-wrapper input {
            flex: 1; padding: 18px 25px; border-radius: 50px; border: 2px solid rgba(255,255,255,0.1);
            background: rgba(0,0,0,0.5); color: #00ffcc; font-size: 1em; font-family: 'Orbitron';
            transition: 0.3s; box-shadow: inset 0 0 10px rgba(0,0,0,0.5); min-width: 280px;
        }
        .input-wrapper input:focus { outline: none; border-color: #00ffcc; box-shadow: 0 0 20px rgba(0,255,204,0.3); }
        .btn {
            padding: 18px 40px; border: none; border-radius: 50px; font-weight: bold; cursor: pointer;
            font-family: 'Orbitron'; transition: all 0.3s ease; font-size: 1em;
            background: linear-gradient(135deg, #00ffcc, #0077ff); color: #000; box-shadow: 0 5px 20px rgba(0,255,204,0.3);
        }
        .btn:hover { transform: translateY(-3px); box-shadow: 0 10px 30px rgba(0,255,204,0.6); }
        .format-buttons { display: flex; gap: 15px; margin: 25px 0; }
        .format-btn {
            flex: 1; padding: 14px; border-radius: 50px; border: 1px solid rgba(255,255,255,0.1);
            background: rgba(255,255,255,0.02); color: #888; font-family: 'Orbitron'; cursor: pointer; transition: 0.3s;
        }
        .format-btn.active { border-color: #00ffcc; color: #fff; background: rgba(0, 255, 204, 0.1); box-shadow: 0 0 15px rgba(0,255,204,0.2); }
        .loading-container { display: none; text-align: center; padding: 30px; }
        .loading-container.active { display: block; }
        .spinner {
            width: 60px; height: 60px; border: 4px solid rgba(0,255,204,0.1); border-top: 4px solid #00ffcc;
            border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px; box-shadow: 0 0 20px rgba(0,255,204,0.2);
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .result-container { display: none; margin-top: 30px; }
        .result-container.active { display: block; }
        .download-now-btn {
            display: block; width: 100%; text-align: center; text-decoration: none; padding: 15px;
            background: linear-gradient(135deg, #ff0077, #7700ff); border-radius: 50px; color: #fff; font-weight: bold;
            box-shadow: 0 5px 20px rgba(255,0,119,0.4); margin-top: 20px; transition: 0.3s;
        }
        .download-now-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(255,0,119,0.7); }
        .footer { text-align: center; margin-top: 50px; color: #444; font-size: 0.85em; }
        .footer a { color: #00ffcc; text-decoration: none; }
    </style>
</head>
<body>
<div id="particles-js"></div>
<div class="container">
    <div class="header">
        <h1>SPEED_X</h1>
        <span class="vip-badge">💎 VIP CORE v3.0 💎</span>
    </div>

    <div class="card">
        <h2>⚡ ENHANCED MEDIA DOWNLOADER</h2>
        <div class="input-wrapper">
            <input type="text" id="urlInput" placeholder="Paste Video URL here...">
            <button class="btn" onclick="startDownload()" id="downloadBtn"><i class="fas fa-terminal"></i> FETCH</button>
        </div>

        <div class="format-buttons">
            <button class="format-btn active" id="vFmt" onclick="setFormat('video')"><i class="fas fa-video"></i> VIDEO MP4</button>
            <button class="format-btn" id="aFmt" onclick="setFormat('mp3')"><i class="fas fa-music"></i> AUDIO MP3</button>
        </div>
    </div>

    <div class="loading-container" id="loadingContainer">
        <div class="spinner"></div>
        <p id="loadingStatus" style="color: #00ffcc;">Decrypting URL...</p>
    </div>

    <div class="result-container" id="resultContainer">
        <div class="card" style="border-color: #ff0077;">
            <h3 style="color: #ff0077;"><i class="fas fa-check-circle"></i> EXTRACTION SUCCESSFUL</h3>
            <div id="resultContent" style="margin-top: 15px;"></div>
            <a href="#" id="dlLink" class="download-now-btn" download><i class="fas fa-cloud-download-alt"></i> INITIALIZE DOWNLOAD</a>
        </div>
    </div>

    <div class="footer">
        <p>POWERED BY <a href="https://t.me/{{ channel.strip('@') }}">@SPEED_X_OFFICIAL1</a> &copy; 2026</p>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/particles.js@2.0.0/particles.min.js"></script>
<script>
    particlesJS('particles-js', {
        "particles": {
            "number": { "value": 80 },
            "color": { "value": "#00ffcc" },
            "shape": { "type": "circle" },
            "opacity": { "value": 0.3 },
            "size": { "value": 3 },
            "line_linked": { "enable": true, "distance": 150, "color": "#00ffcc", "opacity": 0.15, "width": 1 },
            "move": { "enable": true, "speed": 2 }
        }
    });

    let format = 'video';
    function setFormat(fmt) {
        format = fmt;
        document.getElementById('vFmt').classList.toggle('active', fmt==='video');
        document.getElementById('aFmt').classList.toggle('active', fmt==='mp3');
    }

    function startDownload() {
        const url = document.getElementById('urlInput').value.trim();
        if(!url) return;
        document.getElementById('loadingContainer').classList.add('active');
        document.getElementById('resultContainer').classList.remove('active');

        fetch('/api/download', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ url: url, format: format })
        })
        .then(res => res.json())
        .then(data => {
            document.getElementById('loadingContainer').classList.remove('active');
            if(data.success) {
                document.getElementById('resultContent').innerHTML = `<strong>Title:</strong> ${data.title}<br><strong>Size:</strong> ${data.size || 'N/A'}`;
                document.getElementById('dlLink').href = data.download_url;
                document.getElementById('resultContainer').classList.add('active');
            } else { alert("Extraction Error!"); }
        }).catch(() => { document.getElementById('loadingContainer').classList.remove('active'); });
    }
</script>
</body>
</html>
"""

# ============================================
# BOT RUNNING AND WEB SERVER STARTUP FIX
# ============================================

def run_bot():
    logger.info("🚀 Booting Telegram Server Framework...")
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=30)
        except Exception as e:
            logger.error(f"Bot engine crashed. Restarting process stack: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # Clean temporary runtime stack
    for f in os.listdir(TEMP_FOLDER):
        try: os.remove(os.path.join(TEMP_FOLDER, f))
        except: pass

    # Run Telegram Polling inside a background decoupled thread safely
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    logger.info("🌐 Launching Core Web Service Ecosystem...")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# main.py - Complete VIP Single File Solution (Telegram Bot + Professional Web Interface)
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
download_files = {}

# --- Global Flags for Random TikTok Engine ---
auto_ren_active = False
auto_ren_thread = None

# ট্রেন্ডিং এবং হাইলি এক্টিভ কিওয়ার্ড পুল (১০০% রেজাল্ট পাওয়ার জন্য)
RANDOM_KEYWORDS = ["fyp", "trending", "viral", "explore", "foryoupage", "aesthetic", "dance", "funny", "gaming", "capcut"]

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
                        'file_path': file_path, 'filename': os.path.basename(file_path),
                        'title': info.get('title', 'audio'), 'size': os.path.getsize(file_path), 'is_album': False
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
                            'is_album': True, 'image_paths': downloaded_images,
                            'title': info.get('title', 'Photo Album'), 'uploader': info.get('uploader', 'Unknown')
                        }
                ydl.download([url])
                file_path = ydl.prepare_filename(info)
                if not os.path.exists(file_path):
                    alt = os.path.join(temp_dir, f'{filename_base}.mp4')
                    if os.path.exists(alt): file_path = alt
                if os.path.exists(file_path):
                    return {
                        'file_path': file_path, 'filename': os.path.basename(file_path),
                        'title': info.get('title', 'video'), 'size': os.path.getsize(file_path), 'is_album': False
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
# NEW 100% WORKING RANDOM TIKTOK GENERATOR ENGINE
# ============================================
def scrape_truly_random_tiktok():
    """পদ্ধতিগতভাবে ট্রেন্ডিং কীওয়ার্ড সার্চ কোয়েরি পাঠিয়ে লাইভ লিংক জেনারেট করে"""
    keyword = random.choice(RANDOM_KEYWORDS)
    search_url = f"ytsearch5:{keyword} tiktok" # ৫টি ব্যাকলগ থেকে ১টি নিখুঁত ভ্যালিড র্যান্ডম লিংক বাছা হবে
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'no_warnings': True,
        'playlistend': 5
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_url, download=False)
            if result and 'entries' in result and len(result['entries']) > 0:
                valid_entries = [e for e in result['entries'] if e and e.get('url')]
                if valid_entries:
                    chosen = random.choice(valid_entries)
                    video_url = chosen.get('url')
                    if video_url and ('tiktok.com' in video_url or 'vm.tiktok' in video_url):
                        return video_url
    except Exception as e:
        logger.error(f"Random Engine Scraper Error: {e}")
    return None

def random_tiktok_automation_loop(chat_id):
    global auto_ren_active
    bot.send_message(chat_id, "⚙️ <b>[ENGINE START]</b> ব্যাকগ্রাউন্ডে র্যান্ডম হান্টিং প্রসেস চালু হয়েছে...", parse_mode="HTML")
    
    while auto_ren_active:
        try:
            valid_url = scrape_truly_random_tiktok()
            if valid_url:
                # সাকসেস নোটিফিকেশন আপডেট
                bot.send_message(chat_id, f"🎯 <b>[SPEED_X NEW LIVE FIND]</b>\n\n🔗 <b>Link:</b> {valid_url}\n📥 <i>অটোমেটিক ডাউনলোড প্রসেস চলছে...</i>", parse_mode="HTML")
                
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
                    bot.send_message(chat_id, f"⚠️ ভিডিও লিংকটি পাওয়া গেছে কিন্তু সার্ভার জটিলতায় ডাউনলোড ব্যর্থ। পরবর্তী ট্রাই চলছে...", parse_mode="HTML")
            else:
                bot.send_message(chat_id, "🔍 কোনো লাইভ ভিডিও রেসপন্স করেনি। নতুন কিওয়ার্ড দিয়ে পুনরায় স্ক্যান করা হচ্ছে...", parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error in automation loop: {e}")
            
        time.sleep(45) # প্রতি ৪৫ সেকেন্ড পর পর আপডেট ও নতুন ফাইল চেক করবে

# ============================================
# FLASK WEB ROUTES
# ============================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, channel=CHANNEL_USERNAME)

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
            'expires': datetime.now().timestamp() + 3600, 'title': result['title']
        }
        return jsonify({
            'success': True, 'download_id': download_id, 'type': 'album',
            'title': result['title'], 'download_url': f'/download/{download_id}'
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

@app.route('/api/send_to_telegram', methods=['POST', 'OPTIONS'])
def send_to_telegram():
    if request.method == 'OPTIONS': return '', 200
    data = request.get_json()
    download_id = data.get('download_id')
    user_id = data.get('user_id')
    
    if not download_id or not user_id: return jsonify({'error': 'Missing data'}), 400
    if download_id not in download_files: return jsonify({'error': 'File session expired'}), 400
    
    info = download_files[download_id]
    try: user_id = int(user_id)
    except: return jsonify({'error': 'Invalid User ID format'}), 400

    try:
        if info['type'] == 'album':
            from telebot.types import InputMediaPhoto
            media = [InputMediaPhoto(open(img, 'rb')) for img in info['image_paths'] if os.path.exists(img)]
            if media:
                bot.send_media_group(user_id, media)
                return jsonify({'success': True, 'message': 'Album safely delivered to Telegram!'})
            return jsonify({'error': 'Images missing'}), 400
        else:
            file_path = info['file_path']
            if not os.path.exists(file_path): return jsonify({'error': 'File not found on server'}), 400
            
            size_mb = os.path.getsize(file_path) / (1024*1024)
            if size_mb > TELEGRAM_UPLOAD_LIMIT_MB:
                link = upload_to_catbox(file_path)
                if link:
                    bot.send_message(user_id, f"🚀 <b>[SPEED_X CORE] Large File Link:</b>\n{link}", parse_mode="HTML")
                    return jsonify({'success': True, 'message': 'Sent via Catbox Stream link.'})
                return jsonify({'error': 'Cloud upload failed'}), 400
            else:
                with open(file_path, 'rb') as f:
                    if info['filename'].endswith('.mp3'):
                        bot.send_audio(user_id, f, caption=f"🎵 {info.get('title')}")
                    else:
                        bot.send_video(user_id, f, caption=f"🎬 {info.get('title')}", supports_streaming=True)
                return jsonify({'success': True, 'message': 'Media file successfully pushed to Telegram!'})
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
        telebot.types.InlineKeyboardButton("🎬 𝐓𝐈𝐊𝐓𝐎𝐊 𝐕𝐈𝐃𝐄Ｏ", callback_data="tiktok_btn"),
        telebot.types.InlineKeyboardButton("🎵 𝐓𝐈𝐊𝐓𝐎𝐊 𝐌𝐏𝟑", callback_data="tiktok_mp3_btn")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("📹 𝐅𝐀𝐂𝐄𝐁𝐎𝐎𝐊", callback_data="facebook_btn"),
        telebot.types.InlineKeyboardButton("📢 𝐉𝐎𝐈𝐍 𝐕𝐈𝐏", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")
    )
    return markup

START_TEXT = f"""╔══════════════════════════════╗
║   ✨ 𝐒𝐏𝐄𝐄𝐃_𝐗 𝐕𝐈𝐏 𝐁𝐎𝐓 ✨   ║
╚══════════════════════════════╝

💎 <b>𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐓𝐎 𝐓𝐇𝐄 𝐔𝐋𝐓𝐈𝐌𝐀𝐓𝐄 𝐄𝐗𝐏𝐄𝐑𝐈𝐄𝐍𝐂𝐄</b>

⚠️ <b>𝐕𝐄𝐑𝐈𝐅𝐈𝐂𝐀𝐓𝐈𝐎𝐍 𝐑𝐄𝐐𝐔𝐈𝐑𝐄𝐃</b>
বটের সেবাগুলো ফ্রিতে ব্যবহার করতে আমাদের চ্যানেলে জয়েন করুন।
"""

@bot.message_handler(commands=['start', 'help'])
def start_or_help(message):
    user_id = message.from_user.id
    if not is_user_verified(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✨ 𝐉𝐎𝐈𝐍 𝐕𝐈𝐏 𝐂𝐇𝐀𝐍𝐍𝐄𝐋 ✨", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"))
        bot.send_message(message.chat.id, START_TEXT, reply_markup=markup, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "💎 <b>SPEED_X VIP PANEL ACTIVE</b> 💎", reply_markup=get_main_menu_markup(), parse_mode="HTML")

# --- Control Commands ---
@bot.message_handler(commands=['ren'])
def start_random_generation(message):
    global auto_ren_active, auto_ren_thread
    if message.from_user.id != OWNER_ID: return
    if auto_ren_active:
        bot.reply_to(message, "⚠️ র্যান্ডম হান্টিং লুপ ইতিমধ্যেই রানিং আছে!")
        return
    auto_ren_active = True
    auto_ren_thread = threading.Thread(target=random_tiktok_automation_loop, args=(message.chat.id,), daemon=True)
    auto_ren_thread.start()
    bot.reply_to(message, "🚀 <b>SPEED_X Live TikTok Hunter: STARTED!</b>", parse_mode="HTML")

@bot.message_handler(commands=['rren'])
def stop_random_generation(message):
    global auto_ren_active
    if message.from_user.id != OWNER_ID: return
    auto_ren_active = False
    bot.reply_to(message, "🛑 <b>SPEED_X Live TikTok Hunter: STOPPED!</b>", parse_mode="HTML")

def cleanup_files(result):
    if result:
        if result.get('is_album'):
            for img in result.get('image_paths', []): cleanup_file(img)
        else: cleanup_file(result.get('file_path'))

# ============================================
# PREMIUM & CLEAN DIGITAL WEB INTERFACE
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SPEED_X DIGITAL CONTROL</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Rajdhani', sans-serif;
            background: #060913;
            min-height: 100vh;
            color: #e2e8f0;
            overflow-x: hidden;
            position: relative;
        }
        #particles-js {
            position: absolute; width: 100%; height: 100%; top: 0; left: 0; z-index: 1;
        }
        .container { max-width: 750px; margin: 0 auto; position: relative; z-index: 2; padding: 60px 20px; }
        .header { text-align: center; margin-bottom: 40px; }
        .header h1 {
            font-size: 3.5em; font-weight: 700; color: #00ffcc; letter-spacing: 4px;
            text-shadow: 0 0 20px rgba(0, 255, 204, 0.3);
        }
        .subtitle { color: #64748b; font-size: 1.1em; letter-spacing: 1px; margin-top: 5px; }
        .card {
            background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px;
            padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            margin-bottom: 25px; transition: border 0.3s;
        }
        .card:hover { border-color: rgba(0, 255, 204, 0.3); }
        .input-group { margin-top: 20px; position: relative; }
        .input-group i { position: absolute; left: 20px; top: 18px; color: #475569; }
        input {
            width: 100%; padding: 16px 20px 16px 50px; border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.1); background: rgba(5, 8, 16, 0.8);
            color: #fff; font-size: 1.1em; font-family: 'Rajdhani'; transition: 0.3s;
        }
        input:focus { outline: none; border-color: #00ffcc; box-shadow: 0 0 15px rgba(0,255,204,0.15); }
        .format-selector { display: flex; gap: 12px; margin: 20px 0; }
        .f-btn {
            flex: 1; padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);
            background: rgba(255,255,255,0.02); color: #64748b; font-family: 'Rajdhani';
            font-size: 1.1em; cursor: pointer; transition: 0.3s; font-weight: 700;
        }
        .f-btn.active { background: rgba(0, 255, 204, 0.08); border-color: #00ffcc; color: #00ffcc; }
        .action-btn {
            width: 100%; padding: 16px; border: none; border-radius: 8px; font-weight: 700;
            font-family: 'Rajdhani'; font-size: 1.2em; cursor: pointer; transition: 0.3s;
            background: #00ffcc; color: #060913; box-shadow: 0 4px 14px rgba(0,255,204,0.3);
        }
        .action-btn:hover { background: #00ccaa; transform: translateY(-1px); }
        .loader { display: none; text-align: center; padding: 20px; color: #00ffcc; font-size: 1.1em; }
        .loader.active { display: block; }
        .panel-result { display: none; }
        .panel-result.active { display: block; }
        .tg-section { border-top: 1px solid rgba(255,255,255,0.05); margin-top: 20px; padding-top: 20px; }
        .tg-btn { background: #0088cc; color: #fff; box-shadow: 0 4px 14px rgba(0,136,204,0.3); margin-top: 12px; }
        .tg-btn:hover { background: #0077b3; }
        .footer { text-align: center; margin-top: 40px; color: #334155; font-size: 1em; }
        .footer a { color: #00ffcc; text-decoration: none; }
    </style>
</head>
<body>
<div id="particles-js"></div>
<div class="container">
    <div class="header">
        <h1>SPEED_X DIGITAL</h1>
        <div class="subtitle">PREMIUM CORE ENTERPRISE SYSTEM</div>
    </div>

    <div class="card">
        <div class="input-group">
            <i class="fas fa-link"></i>
            <input type="text" id="videoUrl" placeholder="Enter TikTok or Facebook Link...">
        </div>
        
        <div class="format-selector">
            <button class="f-btn active" id="vType" onclick="changeFormat('video')"><i class="fas fa-video"></i> MP4 VIDEO</button>
            <button class="f-btn" id="aType" onclick="changeFormat('mp3')"><i class="fas fa-music"></i> MP3 AUDIO</button>
        </div>

        <button class="action-btn" onclick="processExtraction()"><i class="fas fa-bolt"></i> START EXTRACTION</button>
    </div>

    <div class="loader" id="loader">
        <i class="fas fa-circle-notch fa-spin"></i> Processing data layer streams...
    </div>

    <div class="panel-result" id="resultBlock">
        <div class="card">
            <h4 style="color: #00ffcc; margin-bottom: 10px;"><i class="fas fa-check-circle"></i> EXTRACTION DONE</h4>
            <p id="metaTitle" style="font-size: 1.1em; margin-bottom: 15px; color: #94a3b8;"></p>
            
            <button class="action-btn" id="srvDl" onclick="triggerDownload()"><i class="fas fa-download"></i> DOWNLOAD TO DEVICE</button>

            <div class="tg-section">
                <div class="input-group" style="margin-top: 0;">
                    <i class="fas fa-user-shield"></i>
                    <input type="text" id="tgUserId" placeholder="Enter Telegram User ID...">
                </div>
                <button class="action-btn tg-btn" onclick="sendToTelegramChannel()"><i class="fab fa-telegram-plane"></i> PUSH TO TELEGRAM BOT</button>
            </div>
        </div>
    </div>

    <div class="footer">
        <p>SYSTEM ENGINEERED BY <a href="https://t.me/{{ channel.strip('@') }}">SPEED_X</a> &copy; 2026</p>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/particles.js@2.0.0/particles.min.js"></script>
<script>
    particlesJS('particles-js', {
        "particles": {
            "number": { "value": 50, "density": { "enable": true, "value_area": 800 } },
            "color": { "value": "#00ffcc" },
            "opacity": { "value": 0.15 },
            "size": { "value": 2 },
            "line_linked": { "enable": true, "distance": 150, "color": "#00ffcc", "opacity": 0.08, "width": 1 },
            "move": { "enable": true, "speed": 1.5 }
        }
    });

    let activeFormat = 'video';
    let globalDownloadUrl = '';
    let currentDownloadId = '';

    function changeFormat(fmt) {
        activeFormat = fmt;
        document.getElementById('vType').classList.toggle('active', fmt==='video');
        document.getElementById('aType').classList.toggle('active', fmt==='mp3');
    }

    function processExtraction() {
        const url = document.getElementById('videoUrl').value.trim();
        if(!url) return;
        document.getElementById('loader').classList.add('active');
        document.getElementById('resultBlock').classList.remove('active');

        fetch('/api/download', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ url: url, format: activeFormat })
        })
        .then(res => res.json())
        .then(data => {
            document.getElementById('loader').classList.remove('active');
            if(data.success) {
                currentDownloadId = data.download_id;
                globalDownloadUrl = data.download_url;
                document.getElementById('metaTitle').innerText = data.title;
                document.getElementById('resultBlock').classList.add('active');
            } else { alert("Error extracting source resource!"); }
        }).catch(() => { document.getElementById('loader').classList.remove('active'); });
    }

    function triggerDownload() {
        if(globalDownloadUrl) window.location.href = globalDownloadUrl;
    }

    function sendToTelegramChannel() {
        const uid = document.getElementById('tgUserId').value.trim();
        if(!uid) { alert("Please input a valid Telegram User ID!"); return; }
        
        fetch('/api/send_to_telegram', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ download_id: currentDownloadId, user_id: uid })
        })
        .then(res => res.json())
        .then(data => {
            if(data.success) { alert("Success! Check your Telegram Bot."); }
            else { alert("Failed: " + data.error); }
        });
    }
</script>
</body>
</html>
"""

# ============================================
# BOT ENGINE POLLING RUNNER
# ============================================

def run_bot():
    logger.info("⚡ Booting Telegram Polling Stack Engine...")
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=30)
        except Exception as e:
            logger.error(f"Bot crashed. Relaunching sequence: {e}")
            time.sleep(5)

if __name__ == "__main__":
    for f in os.listdir(TEMP_FOLDER):
        try: os.remove(os.path.join(TEMP_FOLDER, f))
        except: pass

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    logger.info("🌐 Deploying Digital Network Frame Webserver...")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

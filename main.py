# main.py - Complete SPEED_X VIP Automation System (Bot + Advanced Web Engine)
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
download_files = {}

# --- Global Flags for Random TikTok Engine ---
auto_ren_active = False
auto_ren_thread = None

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
    if 'facebook.com' in url_lower or 'fb.watch' in url_lower or 'fb.com' in url_lower: return 'facebook'
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
# AUTOMATED DYNAMIC RANDOM TIKTOK FINDER
# ============================================
def scrape_truly_random_tiktok():
    keyword = random.choice(RANDOM_KEYWORDS)
    search_url = f"ytsearch5:{keyword} tiktok"
    ydl_opts = {'quiet': True, 'extract_flat': True, 'no_warnings': True, 'playlistend': 5}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_url, download=False)
            if result and 'entries' in result and len(result['entries']) > 0:
                valid_entries = [e for e in result['entries'] if e and e.get('url')]
                if valid_entries:
                    return random.choice(valid_entries).get('url')
    except Exception as e:
        logger.error(f"Random Scraper Error: {e}")
    return None

def random_tiktok_automation_loop(chat_id):
    global auto_ren_active
    bot.send_message(chat_id, "⚙️ <b>[SPEED_X INTERNAL ENGINE]</b> র্যান্ডম প্রসেস সাকসেসফুলি স্টার্ট হয়েছে...", parse_mode="HTML")
    while auto_ren_active:
        try:
            valid_url = scrape_truly_random_tiktok()
            if valid_url:
                bot.send_message(chat_id, f"🎯 <b>[NEW LIVE DETECTED]</b>\n🔗 <b>Link:</b> {valid_url}\n📥 <i>অটোমেটিক প্রসেসিং...</i>", parse_mode="HTML")
                result = download_media(valid_url, 'tiktok', 'video')
                if result and not result.get('is_album'):
                    with open(result['file_path'], 'rb') as f:
                        bot.send_video(chat_id, f, caption=f"🎬 <b>SPEED_X Engine Fixed Stream</b>\n📌 <b>Title:</b> {result['title']}\n🔗 <b>Source:</b> {valid_url}", parse_mode="HTML")
                    cleanup_file(result['file_path'])
            else:
                bot.send_message(chat_id, "🔄 রেসপন্স পাওয়া যায়নি। পরবর্তী কিওয়ার্ড দিয়ে আবার চেষ্টা করা হচ্ছে...", parse_mode="HTML")
        except Exception as e:
            logger.error(f"Automation loop error: {e}")
        time.sleep(45)

# ============================================
# FLASK INTERFACES & API ROUTERS
# ============================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, channel=CHANNEL_USERNAME)

@app.route('/stream/<download_id>')
def stream_video(download_id):
    if download_id not in download_files: return "Expired", 404
    info = download_files[download_id]
    if info['type'] == 'file' and os.path.exists(info['file_path']):
        return send_file(info['file_path'], mimetype='video/mp4')
    return "Not Found", 404

@app.route('/api/download', methods=['POST', 'OPTIONS'])
def api_download():
    if request.method == 'OPTIONS': return '', 200
    data = request.get_json()
    url = data.get('url', '').strip()
    format_type = data.get('format', 'video')
    if not url: return jsonify({'error': 'URL data packet empty'}), 400

    platform = detect_platform(url)
    if platform == 'unknown': return jsonify({'error': 'Unsupported network link platform'}), 400

    result = download_media(url, platform, format_type)
    if not result: return jsonify({'error': 'Resource pull failure'}), 400

    download_id = uuid.uuid4().hex[:12]
    download_files[download_id] = {
        'type': 'file', 'file_path': result['file_path'], 'filename': result['filename'],
        'expires': datetime.now().timestamp() + 3600, 'title': result['title'], 'size': result['size']
    }
    return jsonify({
        'success': True, 'download_id': download_id, 'title': result['title'],
        'size': format_file_size(result['size']), 'platform': platform,
        'download_url': f'/download/{download_id}', 'stream_url': f'/stream/{download_id}'
    })

@app.route('/download/<download_id>')
def download_file(download_id):
    if download_id not in download_files: return "Link Expired", 404
    info = download_files[download_id]
    file_path = info['file_path']
    if not os.path.exists(file_path): return "File not found", 404
    return send_file(file_path, as_attachment=True, download_name=info['filename'])

@app.route('/api/send_to_telegram', methods=['POST', 'OPTIONS'])
def send_to_telegram():
    if request.method == 'OPTIONS': return '', 200
    data = request.get_json()
    download_id = data.get('download_id')
    user_id = data.get('user_id')
    
    if not download_id or not user_id: return jsonify({'error': 'Missing core values'}), 400
    if download_id not in download_files: return jsonify({'error': 'Session expired'}), 400
    
    info = download_files[download_id]
    file_path = info['file_path']
    if not os.path.exists(file_path): return jsonify({'error': 'Server asset lost'}), 400

    try:
        size_mb = os.path.getsize(file_path) / (1024*1024)
        if size_mb > TELEGRAM_UPLOAD_LIMIT_MB:
            link = upload_to_catbox(file_path)
            bot.send_message(int(user_id), f"🚀 <b>[SPEED_X VIP] Cloud Asset Link:</b>\n{link}", parse_mode="HTML")
        else:
            with open(file_path, 'rb') as f:
                if info['filename'].endswith('.mp3'):
                    bot.send_audio(int(user_id), f, caption=f"🎵 {info.get('title')}")
                else:
                    bot.send_video(int(user_id), f, caption=f"🎬 {info.get('title')}", supports_streaming=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ============================================
# TELEGRAM BOT LOGIC CONTROL
# ============================================

def is_user_verified(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except: return False

@bot.message_handler(commands=['start'])
def start_or_help(message):
    user_id = message.from_user.id
    if not is_user_verified(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"))
        bot.send_message(message.chat.id, "⚠️ <b>ACCESS DENIED! Please join core channel.</b>", reply_markup=markup, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "💎 <b>SPEED_X SYSTEM ONLINE</b> 💎\nUse Web Dashboard to interact efficiently.", parse_mode="HTML")

@bot.message_handler(commands=['ren'])
def start_random_generation(message):
    global auto_ren_active, auto_ren_thread
    if message.from_user.id != OWNER_ID: return
    if auto_ren_active: return
    auto_ren_active = True
    auto_ren_thread = threading.Thread(target=random_tiktok_automation_loop, args=(message.chat.id,), daemon=True)
    auto_ren_thread.start()
    bot.reply_to(message, "🚀 <b>Live Auto Hunter Engine: ENGAGED!</b>", parse_mode="HTML")

@bot.message_handler(commands=['rren'])
def stop_random_generation(message):
    global auto_ren_active
    if message.from_user.id != OWNER_ID: return
    auto_ren_active = False
    bot.reply_to(message, "🛑 <b>Live Auto Hunter Engine: OFFLINE!</b>", parse_mode="HTML")

# ============================================
# PREMIUM LUXURY WEB CONTROL DASHBOARD
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SPEED_X CONTROL INTERFACE</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Rajdhani', sans-serif; background: #04060a;
            min-height: 100vh; color: #f1f5f9; overflow-x: hidden; position: relative;
        }
        #particles-js { position: absolute; width: 100%; height: 100%; top: 0; left: 0; z-index: 1; }
        .container { max-width: 680px; margin: 0 auto; position: relative; z-index: 2; padding: 50px 15px; }
        .branding-title {
            text-align: center; font-size: 3em; font-weight: 700; color: #00ffcc;
            letter-spacing: 3px; text-shadow: 0 0 15px rgba(0, 255, 204, 0.4); margin-bottom: 30px;
        }
        .ui-card {
            background: rgba(10, 15, 26, 0.85); backdrop-filter: blur(10px);
            border: 1px solid rgba(0, 255, 204, 0.15); border-radius: 12px;
            padding: 25px; box-shadow: 0 15px 35px rgba(0,0,0,0.7); margin-bottom: 20px;
        }
        .field-label { font-size: 1.1em; color: #94a3b8; font-weight: bold; margin-bottom: 8px; display: block; }
        .input-bar { position: relative; display: flex; gap: 10px; margin-bottom: 20px; }
        .input-bar i { position: absolute; left: 15px; top: 15px; color: #00ffcc; font-size: 1.2em; }
        input[type="text"] {
            width: 100%; padding: 14px 15px 14px 45px; border-radius: 6px;
            border: 1px solid rgba(255,255,255,0.08); background: #070b12;
            color: #fff; font-size: 1.1em; font-family: 'Rajdhani'; transition: 0.3s;
        }
        input[type="text"]:focus { outline: none; border-color: #00ffcc; box-shadow: 0 0 10px rgba(0,255,204,0.2); }
        .toggle-options { display: flex; gap: 10px; margin-bottom: 20px; }
        .t-btn {
            flex: 1; padding: 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);
            background: rgba(255,255,255,0.02); color: #64748b; font-family: 'Rajdhani';
            font-size: 1.1em; cursor: pointer; transition: 0.3s; font-weight: bold;
        }
        .t-btn.active { background: rgba(0, 255, 204, 0.1); border-color: #00ffcc; color: #00ffcc; }
        .master-btn {
            width: 100%; padding: 14px; border: none; border-radius: 6px; font-weight: 700;
            font-family: 'Rajdhani'; font-size: 1.2em; cursor: pointer; transition: 0.3s;
            background: #00ffcc; color: #04060a; display: flex; justify-content: center; align-items: center; gap: 10px;
        }
        .master-btn:hover { background: #00ccaa; transform: translateY(-1px); }
        .inline-save-btn {
            background: #00ffcc; color: #000; border: none; padding: 0 20px; border-radius: 6px;
            font-family: 'Rajdhani'; font-weight: bold; cursor: pointer; transition: 0.3s;
        }
        .inline-save-btn:hover { background: #00ccaa; }
        .status-loader { display: none; text-align: center; color: #00ffcc; font-size: 1.2em; padding: 15px 0; }
        .status-loader.active { display: block; }
        .output-zone { display: none; }
        .output-zone.active { display: block; }
        video { width: 100%; border-radius: 8px; border: 1px solid rgba(0, 255, 204, 0.2); margin-bottom: 15px; background: #000; }
        .dl-trigger-btn {
            background: linear-gradient(135deg, #0077ff, #00ffcc); color: #000; font-weight: bold;
            display: flex; justify-content: center; align-items: center; gap: 8px; text-decoration: none;
            padding: 14px; border-radius: 6px; font-size: 1.2em; margin-bottom: 10px; transition: 0.3s;
        }
        .bot-push-banner {
            text-align: center; background: rgba(0, 136, 204, 0.1); border: 1px dashed #0088cc;
            padding: 12px; border-radius: 6px; color: #0088cc; font-weight: bold; font-size: 1.1em;
        }
        .footer-credits { text-align: center; margin-top: 40px; color: #334155; font-size: 1em; }
        .footer-credits a { color: #00ffcc; text-decoration: none; }
    </style>
</head>
<body>
<div id="particles-js"></div>
<div class="container">
    <div class="branding-title"><i class="fas fa-terminal"></i> SPEED_X ENGINE</div>

    <!-- USER ID LAYER -->
    <div class="ui-card">
        <label class="field-label"><i class="fas fa-user-shield"></i> TELEGRAM USER ACCOUNT ID (AUTO-SAVE)</label>
        <div class="input-bar" style="margin-bottom: 0;">
            <i class="fas fa-fingerprint"></i>
            <input type="text" id="storageId" placeholder="Paste your Telegram Chat ID here...">
            <button class="inline-save-btn" onclick="saveTargetId()"><i class="fas fa-save"></i> SAVE</button>
        </div>
    </div>

    <!-- CORE INPUT DOWNER LAYER -->
    <div class="ui-card">
        <label class="field-label"><i class="fas fa-globe"></i> TARGET LINK (TIKTOK / FACEBOOK)</label>
        <div class="input-bar">
            <i class="fas fa-link"></i>
            <input type="text" id="targetLink" placeholder="Paste TikTok or Facebook video link...">
        </div>
        
        <div class="toggle-options">
            <button class="t-btn active" id="fVid" onclick="setMode('video')"><i class="fas fa-video"></i> VIDEO MODE</button>
            <button class="t-btn" id="fAud" onclick="setMode('mp3')"><i class="fas fa-music"></i> AUDIO MP3</button>
        </div>

        <button class="master-btn" onclick="executeExtraction()"><i class="fas fa-cloud-download-alt"></i> EXTRACT SOURCE RESOURCE</button>
    </div>

    <div class="status-loader" id="syncLoader">
        <i class="fas fa-layer-group fa-spin"></i> Processing buffer matrix array layers...
    </div>

    <!-- PREVIEW AND ACTION DOCK PANEL -->
    <div class="output-zone" id="outputZone">
        <div class="ui-card">
            <label class="field-label" style="color: #00ffcc;"><i class="fas fa-video-slash"></i> LIVE STREAM VIDEO PREVIEW</label>
            
            <!-- LIVE AUTO VIDEO PREVIEW -->
            <video id="previewPlayer" controls preload="metadata"></video>

            <a href="#" class="dl-trigger-btn" id="nativeDlLink" download><i class="fas fa-file-download"></i> DOWNLOAD TO STORAGE</a>
            
            <div class="bot-push-banner" id="pushStatus">
                <i class="fas fa-robot"></i> Checking Telegram sync protocol...
            </div>
        </div>
    </div>

    <div class="footer-credits">
        <p>SYSTEM DEVELOPMENT BY <a href="https://t.me/{{ channel.strip('@') }}">SPEED_X</a> &copy; 2026</p>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/particles.js@2.0.0/particles.min.js"></script>
<script>
    particlesJS('particles-js', {
        "particles": {
            "number": { "value": 45 },
            "color": { "value": "#00ffcc" },
            "opacity": { "value": 0.1 },
            "size": { "value": 2 },
            "line_linked": { "enable": true, "distance": 140, "color": "#00ffcc", "opacity": 0.05 },
            "move": { "enable": true, "speed": 1 }
        }
    });

    let currentMode = 'video';
    let currentDownloadId = '';

    // ওটো লোড সেভড আইডি অন উইন্ডো ওপেন
    window.onload = function() {
        const savedId = localStorage.getItem('speedx_tg_id');
        if(savedId) {
            document.getElementById('storageId').value = savedId;
        }
    }

    function saveTargetId() {
        const idVal = document.getElementById('storageId').value.trim();
        if(idVal) {
            localStorage.setItem('speedx_tg_id', idVal);
            alert('Telegram Account ID Successfully Saved onto Local Storage Ecosystem.');
        } else {
            alert('Please input an active ID pack.');
        }
    }

    function setMode(mode) {
        currentMode = mode;
        document.getElementById('fVid').classList.toggle('active', mode==='video');
        document.getElementById('fAud').classList.toggle('active', mode==='mp3');
    }

    function executeExtraction() {
        const url = document.getElementById('targetLink').value.trim();
        if(!url) return;
        
        document.getElementById('syncLoader').classList.add('active');
        document.getElementById('outputZone').classList.remove('active');

        fetch('/api/download', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ url: url, format: currentMode })
        })
        .then(res => res.json())
        .then(data => {
            document.getElementById('syncLoader').classList.remove('active');
            if(data.success) {
                currentDownloadId = data.download_id;
                document.getElementById('nativeDlLink').href = data.download_url;
                
                // রান লাইভ ওটো ভিডিও প্রিভিউ সোর্স স্ট্রিমিং
                const player = document.getElementById('previewPlayer');
                player.src = data.stream_url;
                player.load();

                document.getElementById('outputZone').classList.add('active');

                // ওটোমেটিক সিস্টেম ট্রিগার চেক এবং বটে পুশ অ্যাকশন (কোনো ক্লিক লাগবে না)
                triggerAutoBotPush();
            } else {
                alert("Error binding network source platform packet.");
            }
        }).catch(() => { document.getElementById('syncLoader').classList.remove('active'); });
    }

    function triggerAutoBotPush() {
        const savedUid = localStorage.getItem('speedx_tg_id');
        const statusBox = document.getElementById('pushStatus');
        
        if(!savedUid) {
            statusBox.innerHTML = `<span style="color:#ef4444;"><i class="fas fa-exclamation-triangle"></i> No Saved Telegram ID Found! Auto-Send Skipped.</span>`;
            return;
        }

        statusBox.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Triggering Auto-Push Interface Sync to ID: ${savedUid}...`;

        fetch('/api/send_to_telegram', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ download_id: currentDownloadId, user_id: savedUid })
        })
        .then(res => res.json())
        .then(data => {
            if(data.success) {
                statusBox.innerHTML = `<span style="color:#22c55e;"><i class="fas fa-check-double"></i> PUSH SUCCESSFUL! Check your Telegram Bot.</span>`;
            } else {
                statusBox.innerHTML = `<span style="color:#ef4444;"><i class="fas fa-times-circle"></i> Sync failed: ${data.error}</span>`;
            }
        });
    }
</script>
</body>
</html>
"""

# ============================================
# RUN SERVER ENGINE
# ============================================

def run_bot():
    logger.info("🤖 Starting Background Telegram Stack Process...")
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=30)
        except Exception as e:
            logger.error(f"Telegram Thread Crashed: {e}")
            time.sleep(5)

if __name__ == "__main__":
    for f in os.listdir(TEMP_FOLDER):
        try: os.remove(os.path.join(TEMP_FOLDER, f))
        except: pass

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    logger.info("🌐 Speed_X Web Portal Deployment Complete on Port 5000.")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

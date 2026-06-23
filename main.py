# main.py - SPEED_X VIP Ultimate Core Automation System
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

# --- Global Flags for Fast Random Generator ---
auto_ren_active = False
auto_ren_thread = None

# --- Helper Functions ---
def get_random_string(length=9):
    # টিকটকের সাব-ইউআরএল এর জন্য ক্যারেক্টার জেনারেশন
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))

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

    ydl_opts = {
        'quiet': True,
        'extract_flat': False,
        'no_warnings': True,
        'outtmpl': os.path.join(temp_dir, f'{filename_base}.%(ext)s'),
        'socket_timeout': 15,
        'retries': 2
    }
    
    if format_type == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}]
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = os.path.join(temp_dir, f'{filename_base}.mp3')
                if os.path.exists(file_path):
                    return {
                        'file_path': file_path, 'filename': os.path.basename(file_path),
                        'title': info.get('title', 'Audio Asset'), 'size': os.path.getsize(file_path)
                    }
        except: return None
    else:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                if not os.path.exists(file_path):
                    alt = os.path.join(temp_dir, f'{filename_base}.mp4')
                    if os.path.exists(alt): file_path = alt
                if os.path.exists(file_path):
                    return {
                        'file_path': file_path, 'filename': os.path.basename(file_path),
                        'title': info.get('title', 'Video Asset'), 'size': os.path.getsize(file_path)
                    }
        except: return None

def upload_to_catbox(file_path):
    if not os.path.exists(file_path): return None
    try:
        with open(file_path, 'rb') as f:
            files = {'fileToUpload': f}
            data = {'reqtype': 'fileupload'}
            response = requests.post(CATBOX_API_URL, files=files, data=data, timeout=60)
            if response.status_code == 200 and response.text.startswith('https://files.catbox.moe/'):
                return response.text.strip()
    except: pass
    return None

# ============================================
# 1-SECOND TIKTOK RANDOM LINK BRUTE GENERATOR
# ============================================
def fast_tiktok_generator_loop(chat_id):
    global auto_ren_active
    bot.send_message(chat_id, "🚀 <b>[SPEED_X CORE]</b> আল্ট্রা-ফাস্ট ১ সেকেন্ড র্যান্ডম ইঞ্জিন চালু হয়েছে...", parse_mode="HTML")
    
    while auto_ren_active:
        # এক্সাম্পল ফরম্যাট অনুযায়ী লিংক তৈরি: https://vt.tiktok.com/ZSCRXXxLF/
        random_suffix = get_random_string(9)
        generated_url = f"https://vt.tiktok.com/{random_suffix}/"
        
        try:
            # অত্যন্ত দ্রুত ডাউনলোডের ট্রাই (ব্যাকগ্রাউন্ডে ফাস্ট থ্রেডিং মেকানিজম)
            result = download_media(generated_url, 'tiktok', 'video')
            if result:
                bot.send_message(chat_id, f"🎯 <b>[HIT SUCCESSFUL]</b>\n🔗 <b>Link:</b> {generated_url}", parse_mode="HTML")
                with open(result['file_path'], 'rb') as f:
                    bot.send_video(chat_id, f, caption=f"🎬 <b>SPEED_X Fast Engine Hunt</b>\n🔗 <b>Source:</b> {generated_url}", parse_mode="HTML")
                cleanup_file(result['file_path'])
        except:
            pass
        
        time.sleep(1) # ঠিক ১ সেকেন্ড পর পর লুপ ঘুরবে এবং জেনারেট করবে

# ============================================
# FLASK APIS & CONTROLLERS
# ============================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, channel=CHANNEL_USERNAME)

@app.route('/stream/<download_id>')
def stream_video(download_id):
    if download_id not in download_files: return "Expired", 404
    info = download_files[download_id]
    if os.path.exists(info['file_path']):
        return send_file(info['file_path'], mimetype='video/mp4')
    return "Not Found", 404

@app.route('/api/download', methods=['POST', 'OPTIONS'])
def api_download():
    if request.method == 'OPTIONS': return '', 200
    data = request.get_json()
    url = data.get('url', '').strip()
    format_type = data.get('format', 'video')
    if not url: return jsonify({'error': 'Empty Target Package'}), 400

    platform = detect_platform(url)
    if platform == 'unknown': return jsonify({'error': 'Unsupported Core Platform'}), 400

    result = download_media(url, platform, format_type)
    if not result: return jsonify({'error': 'Source Parsing Failed'}), 400

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
    if download_id not in download_files: return "Session Expired", 404
    info = download_files[download_id]
    file_path = info['file_path']
    if not os.path.exists(file_path): return "File Loss Error", 404
    return send_file(file_path, as_attachment=True, download_name=info['filename'])

@app.route('/api/send_to_telegram', methods=['POST', 'OPTIONS'])
def send_to_telegram():
    if request.method == 'OPTIONS': return '', 200
    data = request.get_json()
    download_id = data.get('download_id')
    user_id = data.get('user_id')
    
    if not download_id or not user_id: return jsonify({'error': 'Values Mismatched'}), 400
    if download_id not in download_files: return jsonify({'error': 'Session Closed'}), 400
    
    info = download_files[download_id]
    file_path = info['file_path']
    if not os.path.exists(file_path): return jsonify({'error': 'Asset not on server'}), 400

    try:
        size_mb = os.path.getsize(file_path) / (1024*1024)
        if size_mb > TELEGRAM_UPLOAD_LIMIT_MB:
            link = upload_to_catbox(file_path)
            bot.send_message(int(user_id), f"🚀 <b>[SPEED_X CORE] Large File Streaming Link:</b>\n{link}", parse_mode="HTML")
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
# TELEGRAM BOT HANDLERS & FILTERS
# ============================================

@bot.message_handler(commands=['start'])
def start_panel(message):
    bot.send_message(message.chat.id, "💎 <b>SPEED_X DUAL NET SYSTEM ONLINE</b> 💎\nUse the web dashboard for automated extraction panels.", parse_mode="HTML")

@bot.message_handler(commands=['ren'])
def start_fast_ren(message):
    global auto_ren_active, auto_ren_thread
    if message.from_user.id != OWNER_ID: 
        bot.reply_to(message, "❌ <b>ACCESS DENIED! You are not authorized Owner.</b>", parse_mode="HTML")
        return
    if auto_ren_active: 
        bot.reply_to(message, "⚠️ Engine Already Operating.")
        return
    auto_ren_active = True
    auto_ren_thread = threading.Thread(target=fast_tiktok_generator_loop, args=(message.chat.id,), daemon=True)
    auto_ren_thread.start()
    bot.reply_to(message, "🚀 <b>Owner Core Brute Engine Enabled (1s Loop Active).</b>", parse_mode="HTML")

@bot.message_handler(commands=['rren'])
def stop_fast_ren(message):
    global auto_ren_active
    if message.from_user.id != OWNER_ID: return
    auto_ren_active = False
    bot.reply_to(message, "🛑 <b>Owner Core Brute Engine Offline.</b>", parse_mode="HTML")

# ============================================
# ADVANCED VIP DIGITAL LAYOUT DESIGN
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SPEED_X VIP PANEL</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Rajdhani', sans-serif; background: #050811;
            min-height: 100vh; color: #f1f5f9; overflow-x: hidden; position: relative;
        }
        #particles-js { position: absolute; width: 100%; height: 100%; top: 0; left: 0; z-index: 1; }
        .container { max-width: 700px; margin: 0 auto; position: relative; z-index: 2; padding: 40px 15px; }
        .branding-title {
            text-align: center; font-size: 3.2em; font-weight: 700; color: #00ffcc;
            letter-spacing: 3px; text-shadow: 0 0 20px rgba(0, 255, 204, 0.5); margin-bottom: 25px;
        }
        .ui-card {
            background: rgba(9, 14, 26, 0.9); backdrop-filter: blur(12px);
            border: 1px solid rgba(0, 255, 204, 0.2); border-radius: 12px;
            padding: 25px; box-shadow: 0 20px 40px rgba(0,0,0,0.8); margin-bottom: 20px;
        }
        .field-label { font-size: 1.1em; color: #00ffcc; font-weight: bold; margin-bottom: 10px; display: block; letter-spacing: 1px; }
        .input-bar { position: relative; display: flex; gap: 10px; margin-bottom: 20px; }
        .input-bar i { position: absolute; left: 15px; top: 15px; color: #00ffcc; font-size: 1.2em; }
        input[type="text"] {
            width: 100%; padding: 14px 15px 14px 45px; border-radius: 6px;
            border: 1px solid rgba(0, 255, 204, 0.2); background: #03050a;
            color: #fff; font-size: 1.1em; font-family: 'Rajdhani'; transition: 0.3s;
        }
        input[type="text"]:focus { outline: none; border-color: #00ffcc; box-shadow: 0 0 15px rgba(0,255,204,0.3); }
        
        .toggle-options { display: flex; gap: 10px; margin-bottom: 20px; }
        .t-btn {
            flex: 1; padding: 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);
            background: rgba(255,255,255,0.02); color: #64748b; font-family: 'Rajdhani';
            font-size: 1.1em; cursor: pointer; transition: 0.3s; font-weight: bold;
        }
        .t-btn.active { background: rgba(0, 255, 204, 0.12); border-color: #00ffcc; color: #00ffcc; }
        
        .master-btn {
            width: 100%; padding: 15px; border: none; border-radius: 6px; font-weight: 700;
            font-family: 'Rajdhani'; font-size: 1.25em; cursor: pointer; transition: 0.3s;
            background: #00ffcc; color: #050811; display: flex; justify-content: center; align-items: center; gap: 10px;
            box-shadow: 0 0 15px rgba(0,255,204,0.3);
        }
        .master-btn:hover { background: #00ccaa; transform: translateY(-1px); box-shadow: 0 0 25px rgba(0,255,204,0.5); }
        
        .inline-save-btn {
            background: #00ffcc; color: #000; border: none; padding: 0 22px; border-radius: 6px;
            font-family: 'Rajdhani'; font-weight: bold; cursor: pointer; transition: 0.3s;
        }
        .inline-save-btn:hover { background: #00ccaa; }

        /* ADVANCED PROGRESS LOADING BAR */
        .progress-container { display: none; margin-top: 15px; }
        .progress-container.active { display: block; }
        .progress-bar-wrapper {
            width: 100%; background: #111827; height: 10px; border-radius: 20px; overflow: hidden; border: 1px solid rgba(0,255,204,0.1);
        }
        .progress-bar-fill {
            height: 100%; width: 0%; background: linear-gradient(90deg, #00ffcc, #0088cc);
            box-shadow: 0 0 10px #00ffcc; transition: width 0.4s ease;
        }
        .progress-text { font-size: 1em; color: #94a3b8; margin-top: 5px; text-align: center; font-weight: bold; }

        .output-zone { display: none; }
        .output-zone.active { display: block; }
        video { width: 100%; border-radius: 8px; border: 1px solid rgba(0, 255, 204, 0.3); margin-bottom: 15px; background: #000; }
        
        .dl-trigger-btn {
            background: linear-gradient(135deg, #0088cc, #00ffcc); color: #050811; font-weight: bold;
            display: flex; justify-content: center; align-items: center; gap: 8px; text-decoration: none;
            padding: 14px; border-radius: 6px; font-size: 1.2em; margin-bottom: 15px; transition: 0.3s;
        }
        .dl-trigger-btn:hover { opacity: 0.9; transform: scale(1.01); }
        
        .bot-push-banner {
            text-align: center; background: rgba(0, 255, 204, 0.05); border: 1px dashed #00ffcc;
            padding: 12px; border-radius: 6px; color: #00ffcc; font-weight: bold; font-size: 1.1em;
        }
        .platform-badge {
            display: inline-block; padding: 4px 10px; border-radius: 4px; font-size: 0.9em; font-weight: bold; margin-bottom: 10px;
        }
        .badge-tiktok { background: #ff0050; color: #fff; }
        .badge-facebook { background: #1877f2; color: #fff; }

        .footer-credits { text-align: center; margin-top: 40px; color: #334155; font-size: 1em; }
        .footer-credits a { color: #00ffcc; text-decoration: none; }
    </style>
</head>
<body>
<div id="particles-js"></div>
<div class="container">
    <div class="branding-title"><i class="fas fa-bolt"></i> SPEED_X VIP DASHBOARD</div>

    <!-- SAVE USER ID LAYER -->
    <div class="ui-card">
        <label class="field-label"><i class="fas fa-fingerprint"></i> TELEGRAM USER ACCOUNT SIGNATURE ID (SAVED)</label>
        <div class="input-bar" style="margin-bottom: 0;">
            <i class="fas fa-user-shield"></i>
            <input type="text" id="storageId" placeholder="Enter Telegram Chat ID for Auto-Push Sync...">
            <button class="inline-save-btn" onclick="saveTargetId()"><i class="fas fa-save"></i> SAVE ID</button>
        </div>
    </div>

    <!-- CORE USER ENGINE INTERFACE -->
    <div class="ui-card">
        <label class="field-label"><i class="fas fa-link"></i> ENTER NETWORK LINK RESOURCE (TIKTOK / FACEBOOK)</label>
        <div class="input-bar">
            <i class="fas fa-share-alt"></i>
            <input type="text" id="targetLink" placeholder="Paste TikTok or Facebook video stream link here...">
        </div>
        
        <div class="toggle-options">
            <button class="t-btn active" id="fVid" onclick="setMode('video')"><i class="fas fa-video"></i> MP4 VIDEO PANEL</button>
            <button class="t-btn" id="fAud" onclick="setMode('mp3')"><i class="fas fa-music"></i> AUDIO REMIX MP3</button>
        </div>

        <button class="master-btn" onclick="executeExtraction()"><i class="fas fa-atom"></i> INITIATE EXTRACT SYSTEM</button>

        <!-- DIGITAL LOADING BAR STRUCTURE -->
        <div class="progress-container" id="progressBarContainer">
            <div class="progress-bar-wrapper">
                <div class="progress-bar-fill" id="progressBarFill"></div>
            </div>
            <div class="progress-text" id="progressStatusText">Syncing Server Pipeline Layers... 0%</div>
        </div>
    </div>

    <!-- RESPONSE OUTPUT VIEW SYSTEM -->
    <div class="output-zone" id="outputZone">
        <div class="ui-card">
            <div id="platformContainer"></div>
            <label class="field-label" style="color: #00ffcc;"><i class="fas fa-play-circle"></i> AUTO STREAM VIDEO PREVIEW PLAYER</label>
            
            <!-- AUTO LIVE PREVIEW -->
            <video id="previewPlayer" controls preload="metadata"></video>

            <!-- DEVICE NATIVE DOWNLOAD BUTTON -->
            <a href="#" class="dl-trigger-btn" id="nativeDlLink" download><i class="fas fa-cloud-download-alt"></i> DOWNLOAD DIRECT TO DEVICE STORAGE</a>
            
            <!-- AUTO TELEGRAM DISPATCH STATUS PANEL -->
            <div class="bot-push-banner" id="pushStatus">
                <i class="fas fa-sync fa-spin"></i> Triggering system channel link core protocols...
            </div>
        </div>
    </div>

    <div class="footer-credits">
        <p>VIP SOFTWARE ENGINEERED BY <a href="https://t.me/{{ channel.strip('@') }}">SPEED_X</a> &copy; 2026</p>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/particles.js@2.0.0/particles.min.js"></script>
<script>
    particlesJS('particles-js', {
        "particles": {
            "number": { "value": 50 },
            "color": { "value": "#00ffcc" },
            "opacity": { "value": 0.12 },
            "size": { "value": 2 },
            "line_linked": { "enable": true, "distance": 130, "color": "#00ffcc", "opacity": 0.06 },
            "move": { "enable": true, "speed": 1.2 }
        }
    });

    let currentMode = 'video';
    let currentDownloadId = '';

    window.onload = function() {
        const savedId = localStorage.getItem('speedx_tg_id');
        if(savedId) { document.getElementById('storageId').value = savedId; }
    }

    function saveTargetId() {
        const idVal = document.getElementById('storageId').value.trim();
        if(idVal) {
            localStorage.setItem('speedx_tg_id', idVal);
            alert('Core Token ID Safely Registered in Storage Stack.');
        }
    }

    function setMode(mode) {
        currentMode = mode;
        document.getElementById('fVid').classList.toggle('active', mode==='video');
        document.getElementById('fAud').classList.toggle('active', mode==='mp3');
    }

    function runFakeProgressBar(callback) {
        const bar = document.getElementById('progressBarFill');
        const text = document.getElementById('progressStatusText');
        const container = document.getElementById('progressBarContainer');
        
        container.classList.add('active');
        bar.style.width = '0%';
        
        let width = 0;
        const interval = setInterval(() => {
            if (width >= 90) {
                clearInterval(interval);
                callback();
            } else {
                width += Math.floor(Math.random() * 15) + 5;
                if(width > 90) width = 90;
                bar.style.width = width + '%';
                text.innerText = `Fetching Buffer Array... ${width}%`;
            }
        }, 120);

        return interval;
    }

    function executeExtraction() {
        const url = document.getElementById('targetLink').value.trim();
        if(!url) return;
        
        document.getElementById('outputZone').classList.remove('active');
        
        const progressInterval = runFakeProgressBar(() => {
            // প্রগ্রেস বার ৯০% এ যাওয়ার পর আসল ডাটা ফেচ রিকোয়েস্ট ফায়ার করবে
            fetch('/api/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ url: url, format: currentMode })
            })
            .then(res => res.json())
            .then(data => {
                clearInterval(progressInterval);
                const bar = document.getElementById('progressBarFill');
                const text = document.getElementById('progressStatusText');
                
                if(data.success) {
                    bar.style.width = '100%';
                    text.innerText = 'Extraction Completed Securely! 100%';
                    
                    setTimeout(() => {
                        document.getElementById('progressBarContainer').classList.remove('active');
                        currentDownloadId = data.download_id;
                        document.getElementById('nativeDlLink').href = data.download_url;
                        
                        // সেট প্লাটফর্ম ব্যাজ
                        const badgeBox = document.getElementById('platformContainer');
                        if(data.platform === 'tiktok') {
                            badgeBox.innerHTML = `<span class="platform-badge badge-tiktok"><i class="fab fa-tiktok"></i> TIKTOK SYSTEM ACTIVE</span>`;
                        } else {
                            badgeBox.innerHTML = `<span class="platform-badge badge-facebook"><i class="fab fa-facebook"></i> FACEBOOK SYSTEM ACTIVE</span>`;
                        }

                        // স্ট্রিমিং সোর্স ইনজেক্ট
                        const player = document.getElementById('previewPlayer');
                        player.src = data.stream_url;
                        player.load();

                        document.getElementById('outputZone').classList.add('active');
                        triggerAutoBotPush();
                    }, 400);
                } else {
                    document.getElementById('progressBarContainer').classList.remove('active');
                    alert("Resource pipeline failed to map stream data.");
                }
            }).catch(() => {
                clearInterval(progressInterval);
                document.getElementById('progressBarContainer').classList.remove('active');
            });
        });
    }

    function triggerAutoBotPush() {
        const savedUid = localStorage.getItem('speedx_tg_id');
        const statusBox = document.getElementById('pushStatus');
        
        if(!savedUid) {
            statusBox.innerHTML = `<span style="color:#ef4444;"><i class="fas fa-user-slash"></i> Sync Skipped: No Saved ID Configuration Found.</span>`;
            return;
        }

        statusBox.innerHTML = `<i class="fas fa-satellite-dish fa-spin"></i> Auto-Pushing Stream Vector Array directly to Bot Client: [${savedUid}]`;

        fetch('/api/send_to_telegram', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ download_id: currentDownloadId, user_id: savedUid })
        })
        .then(res => res.json())
        .then(data => {
            if(data.success) {
                statusBox.innerHTML = `<span style="color:#00ffcc;"><i class="fas fa-check-double"></i> DISPATCH SUCCESSFUL! Asset Pushed To Saved Telegram Account.</span>`;
            } else {
                statusBox.innerHTML = `<span style="color:#ef4444;"><i class="fas fa-circle-exclamation"></i> Dispatch Fail Error: ${data.error}</span>`;
            }
        });
    }
</script>
</body>
</html>
"""

# ============================================
# RUN TIME SERVICE LOOP RUNNER
# ============================================

def run_bot():
    logger.info("⚡ Activating Telebot Engine Framework Layers...")
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=30)
        except Exception as e:
            logger.error(f"Bot crash runtime error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    for f in os.listdir(TEMP_FOLDER):
        try: os.remove(os.path.join(TEMP_FOLDER, f))
        except: pass

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    logger.info("🌐 Speed_X Luxury Core Dashboard Interface Alive on Port 5000.")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

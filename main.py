# main.py - SPEED_X VIP Ultimate Core Automation System & Web Panel
import os
import sys
import time
import string
import random
import threading
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, send_file
import telebot
import yt_dlp

app = Flask(__name__)
app.secret_key = 'speed_x_super_secret_key_nirob_bbz'

# --- CORS & Headers ---
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# --- Directories ---
TEMP_FOLDER = 'temp'
os.makedirs(TEMP_FOLDER, exist_ok=True)

# --- Bot Configuration ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
try:
    bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=4)
except Exception:
    bot = None

download_files = {}

# --- Global Control & App Settings (Managed via /admin) ---
app_config = {
    "site_status": True,                 # Website On/Off switch
    "maintenance_msg": "Website is currently under maintenance by NIROB BBZ. Please check back later!",
    "popup_active": True,                # Popup switch (On/Off)
    "popup_title": "🔥 SPEED_X VIP NOTICE 🔥",
    "popup_content": "Welcome to SPEED_X Ultimate Core System! Join our Telegram channels and enjoy VIP automated downloading & tools.",
    "popup_btn_text": "Join Telegram",
    "popup_btn_url": "https://t.me/SPEED_X_OFFICIAL1",       # Custom button link
    "popup_show_button": True            # Show/Hide button on popup
}

ADMIN_CREDENTIALS = {
    "email": "admin@nirob.com",
    "password": "admin"
}

# --- Global Flags for Fast Random Generator ---
auto_ren_active = False
auto_ren_thread = None

# --- Helper Functions ---
def get_random_string(length=9):
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
    if 'instagram.com' in url_lower: return 'instagram'
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

    if format_type == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({
            'format': 'best[ext=mp4]/best/bestvideo+bestaudio',
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if format_type == 'audio':
                filename = os.path.splitext(filename)[0] + '.mp3'
            
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                return True, filename, unique_id, format_file_size(file_size)
    except Exception as e:
        print(f"Download Error: {e}")
    
    return False, str(e) if 'e' in locals() else "Download failed", None, None

# --- Middleware for Maintenance Mode ---
@app.before_request
def check_maintenance():
    if not app_config["site_status"]:
        if request.path.startswith('/admin') or request.path.startswith('/static'):
            return
        return render_template_string(MAINTENANCE_TEMPLATE, msg=app_config["maintenance_msg"])

# --- HTML Templates ---

MAINTENANCE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Maintenance - SPEED_X VIP</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        body { background: #070913; color: #fff; font-family: 'Poppins', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; text-align: center; }
        .box { background: rgba(255,255,255,0.03); padding: 40px; border-radius: 20px; border: 1px solid rgba(0,255,200,0.2); box-shadow: 0 0 30px rgba(0,255,200,0.1); max-width: 500px; }
        h1 { color: #00ffc8; margin-bottom: 15px; }
        p { color: #a0aec0; line-height: 1.6; }
        .credit { margin-top: 25px; font-size: 12px; color: #718096; text-transform: uppercase; letter-spacing: 2px; }
    </style>
</head>
<body>
    <div class="box">
        <h1>⚠️ SYSTEM OFFLINE</h1>
        <p>{{ msg }}</p>
        <div class="credit">VIP SOFTWARE ENGINEERED BY NIROB BBZ © 2026</div>
    </div>
</body>
</html>
"""

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SPEED_X VIP DASHBOARD - NIROB BBZ</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Poppins', sans-serif; }
        body { background: #070913; color: #fff; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 15px; }
        .container { width: 100%; max-width: 440px; background: #0b0f19; border: 1px solid rgba(0, 255, 200, 0.25); border-radius: 22px; padding: 25px; box-shadow: 0 15px 35px rgba(0,0,0,0.8), 0 0 20px rgba(0,255,200,0.08); }
        
        .main-title { text-align: center; margin-bottom: 22px; }
        .main-title i { color: #00ffc8; font-size: 32px; display: block; margin-bottom: 8px; text-shadow: 0 0 20px rgba(0,255,200,0.7); animation: pulseGlow 2s infinite alternate; }
        .main-title h1 { font-size: 20px; font-weight: 700; color: #00ffc8; letter-spacing: 1px; text-shadow: 0 0 10px rgba(0,255,200,0.3); }

        .card-box { background: rgba(17, 24, 39, 0.7); border: 1px solid rgba(0, 255, 200, 0.12); border-radius: 16px; padding: 16px; margin-bottom: 16px; transition: 0.3s; }
        .card-box:hover { border-color: rgba(0,255,200,0.3); box-shadow: 0 0 15px rgba(0,255,200,0.05); }
        
        .card-label { font-size: 11px; text-transform: uppercase; color: #9ca3af; letter-spacing: 0.8px; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; font-weight: 600; }
        .card-label i { color: #00ffc8; font-size: 13px; }

        .input-row { display: flex; gap: 8px; }
        input[type="text"] { flex: 1; padding: 12px 14px; background: rgba(11, 15, 25, 0.95); border: 1px solid #1f2937; border-radius: 10px; color: #fff; font-size: 13px; outline: none; transition: 0.3s; }
        input[type="text"]:focus { border-color: #00ffc8; box-shadow: 0 0 10px rgba(0,255,200,0.3); }
        
        .action-btn { background: linear-gradient(135deg, #00ffc8, #00b894); color: #070913; border: none; border-radius: 10px; padding: 0 16px; font-weight: 700; font-size: 11px; cursor: pointer; text-transform: uppercase; transition: 0.2s; white-space: nowrap; box-shadow: 0 4px 12px rgba(0,255,200,0.2); }
        .action-btn:hover { transform: scale(1.02); opacity: 0.9; }

        .paste-row-btn { background: rgba(31, 41, 55, 0.9); color: #d1d5db; border: 1px solid #374151; border-radius: 10px; padding: 12px; font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 8px; justify-content: center; width: 100%; margin-bottom: 12px; transition: 0.2s; }
        .paste-row-btn:hover { background: #374151; color: #fff; border-color: #00ffc8; }

        .format-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
        .format-option { background: rgba(11, 15, 25, 0.9); border: 1px solid #1f2937; border-radius: 12px; padding: 12px; text-align: center; cursor: pointer; transition: all 0.3s ease; display: flex; flex-direction: column; align-items: center; gap: 6px; font-size: 11px; font-weight: 600; color: #9ca3af; }
        .format-option i { font-size: 18px; color: #00ffc8; }
        .format-option.active { border-color: #00ffc8; background: rgba(0,255,200,0.08); color: #fff; box-shadow: 0 0 12px rgba(0,255,200,0.15); transform: translateY(-1px); }

        .extract-btn { width: 100%; padding: 15px; background: linear-gradient(135deg, #00ffc8 0%, #00b894 100%); color: #070913; border: none; border-radius: 12px; font-weight: 700; font-size: 13px; text-transform: uppercase; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 5px 20px rgba(0,255,200,0.35); transition: 0.3s; letter-spacing: 0.5px; }
        .extract-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,255,200,0.5); }

        /* Success Animation & Result Box */
        .result-box { margin-top: 18px; background: rgba(11, 15, 25, 0.95); border: 1px solid rgba(0,255,200,0.5); border-radius: 14px; padding: 16px; display: none; animation: successPop 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; box-shadow: 0 0 25px rgba(0,255,200,0.25); position: relative; overflow: hidden; }
        .result-box::before { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle, rgba(0,255,200,0.1) 0%, transparent 70%); animation: rotateGlow 6s linear infinite; pointer-events: none; }
        
        .result-box h3 { font-size: 14px; color: #00ffc8; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; font-weight: 700; text-shadow: 0 0 10px rgba(0,255,200,0.5); }
        .result-box h3 i { animation: bounceCheck 0.6s ease infinite alternate; font-size: 16px; }
        
        .preview-container { width: 100%; max-height: 220px; border-radius: 10px; overflow: hidden; background: #000; margin-bottom: 12px; border: 1px solid rgba(0,255,200,0.2); display: flex; justify-content: center; align-items: center; }
        .preview-container video, .preview-container audio { width: 100%; max-height: 200px; outline: none; }
        
        .file-info { font-size: 12px; color: #d1d5db; margin-bottom: 14px; word-break: break-all; line-height: 1.5; background: rgba(0,0,0,0.3); padding: 8px 10px; border-radius: 8px; }
        
        .download-action-btn { width: 100%; padding: 13px; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #fff; border-radius: 10px; text-align: center; text-decoration: none; font-weight: 700; font-size: 12px; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 4px 15px rgba(37,99,235,0.4); transition: 0.2s; text-transform: uppercase; }
        .download-action-btn:hover { transform: scale(1.02); background: linear-gradient(135deg, #1d4ed8, #1e40af); box-shadow: 0 6px 20px rgba(37,99,235,0.6); }

        /* Popup Styles */
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); display: none; justify-content: center; align-items: center; z-index: 9999; padding: 20px; }
        .modal-card { background: #0b0f19; border: 1px solid rgba(0,255,200,0.4); border-radius: 20px; width: 100%; max-width: 380px; padding: 25px; text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.8), 0 0 25px rgba(0,255,200,0.15); position: relative; animation: scaleUp 0.3s ease forwards; }
        .modal-icon { width: 55px; height: 55px; background: rgba(0,255,200,0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 15px; color: #00ffc8; font-size: 24px; border: 1px solid rgba(0,255,200,0.3); }
        .modal-card h2 { font-size: 18px; color: #fff; margin-bottom: 10px; font-weight: 700; }
        .modal-card p { color: #9ca3af; font-size: 13px; line-height: 1.6; margin-bottom: 20px; }
        .modal-btn { display: block; width: 100%; padding: 13px; background: linear-gradient(135deg, #00ffc8, #00b894); color: #070913; font-weight: 700; border-radius: 10px; text-decoration: none; font-size: 13px; box-shadow: 0 4px 15px rgba(0,255,200,0.3); }
        .modal-close { position: absolute; top: 12px; right: 15px; background: none; border: none; color: #6b7280; font-size: 20px; cursor: pointer; transition: 0.2s; }
        .modal-close:hover { color: #fff; }

        .footer { margin-top: 20px; text-align: center; font-size: 10px; color: #6b7280; letter-spacing: 1px; text-transform: uppercase; }
        .footer span { color: #00ffc8; font-weight: 600; }

        /* Keyframes Animations */
        @keyframes pulseGlow {
            from { text-shadow: 0 0 10px rgba(0,255,200,0.4); }
            to { text-shadow: 0 0 25px rgba(0,255,200,0.9); }
        }
        @keyframes successPop {
            0% { opacity: 0; transform: scale(0.9) translateY(15px); }
            100% { opacity: 1; transform: scale(1) translateY(0); }
        }
        @keyframes bounceCheck {
            from { transform: translateY(0); }
            to { transform: translateY(-3px); }
        }
        @keyframes scaleUp {
            from { transform: scale(0.85); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        @keyframes rotateGlow {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>

    <!-- Popup Modal -->
    {% if config.popup_active %}
    <div class="modal-overlay" id="popupModal">
        <div class="modal-card">
            <button class="modal-close" onclick="closePopup()">&times;</button>
            <div class="modal-icon"><i class="fa-solid fa-bell"></i></div>
            <h2>{{ config.popup_title }}</h2>
            <p>{{ config.popup_content }}</p>
            {% if config.popup_show_button %}
            <a href="{{ config.popup_btn_url }}" target="_blank" class="modal-btn">{{ config.popup_btn_text }}</a>
            {% endif %}
        </div>
    </div>
    <script>
        window.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => { document.getElementById('popupModal').style.display = 'flex'; }, 400);
        });
        function closePopup() { document.getElementById('popupModal').style.display = 'none'; }
    </script>
    {% endif %}

    <div class="container">
        <div class="main-title">
            <i class="fa-solid fa-bolt"></i>
            <h1>SPEED_X VIP DASHBOARD</h1>
        </div>

        <!-- Telegram Signature ID Box -->
        <div class="card-box">
            <div class="card-label"><i class="fa-solid fa-fingerprint"></i> Telegram User Account Signature ID</div>
            <div class="input-row">
                <input type="text" id="tgId" placeholder="Enter Telegram ID..." value="7224513731">
                <button type="button" class="action-btn" onclick="saveTgId()">Save ID</button>
            </div>
        </div>

        <!-- Network Link Resource Box -->
        <div class="card-box">
            <div class="card-label"><i class="fa-solid fa-link"></i> Enter Media Link (TikTok / Facebook)</div>
            
            <div class="input-row" style="margin-bottom: 10px;">
                <input type="text" id="mediaUrl" placeholder="Paste link here...">
            </div>
            <button type="button" class="paste-row-btn" id="pasteBtn"><i class="fa-solid fa-paste"></i> Paste Link from Clipboard</button>

            <!-- Format Selector -->
            <div class="format-grid">
                <div class="format-option active" id="optVideo" onclick="setFormat('video')">
                    <i class="fa-solid fa-video"></i> MP4 Video Panel
                </div>
                <div class="format-option" id="optAudio" onclick="setFormat('audio')">
                    <i class="fa-solid fa-music"></i> Audio Remix MP3
                </div>
            </div>

            <button type="button" class="extract-btn" id="submitBtn" onclick="processMedia()"><i class="fa-solid fa-atom"></i> Initiate Extract System</button>

            <!-- Success Box with Live Preview & Neon Animation -->
            <div class="result-box" id="resultBox">
                <h3><i class="fa-solid fa-circle-check"></i> Extraction Successful!</h3>
                <div class="preview-container" id="previewContainer"></div>
                <div class="file-info" id="fileInfo"></div>
                <a href="#" id="downloadLink" class="download-action-btn"><i class="fa-solid fa-download"></i> Download Processed File</a>
            </div>
        </div>

        <div class="footer">VIP Software Engineered by <span>NIROB BBZ</span> © 2026</div>
    </div>

    <script>
        let currentFormat = 'video';

        function setFormat(fmt) {
            currentFormat = fmt;
            if(fmt === 'video') {
                document.getElementById('optVideo').classList.add('active');
                document.getElementById('optAudio').classList.remove('active');
            } else {
                document.getElementById('optAudio').classList.add('active');
                document.getElementById('optVideo').classList.remove('active');
            }
        }

        function saveTgId() {
            const id = document.getElementById('tgId').value;
            if(id) alert('Telegram Signature ID Saved Successfully: ' + id);
            else alert('Please enter a valid ID.');
        }

        document.getElementById('pasteBtn').addEventListener('click', async () => {
            try {
                const text = await navigator.clipboard.readText();
                document.getElementById('mediaUrl').value = text;
            } catch (err) {
                alert('Clipboard access denied. Please paste manually.');
            }
        });

        async function processMedia() {
            const url = document.getElementById('mediaUrl').value.trim();
            const submitBtn = document.getElementById('submitBtn');
            const resultBox = document.getElementById('resultBox');
            const previewContainer = document.getElementById('previewContainer');
            const fileInfo = document.getElementById('fileInfo');
            const downloadLink = document.getElementById('downloadLink');

            if(!url) {
                alert('Please enter or paste a valid link first.');
                return;
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Extracting & Processing...';
            resultBox.style.display = 'none';

            try {
                const res = await fetch('/api/process', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ url: url, format: currentFormat })
                });
                const data = await res.json();

                if(data.success) {
                    fileInfo.innerHTML = `<b>Platform:</b> ${data.platform.toUpperCase()}<br><b>File Size:</b> ${data.filesize}<br><b>File:</b> ${data.filename}`;
                    downloadLink.href = data.download_url;
                    
                    // Render Proper Preview
                    previewContainer.innerHTML = '';
                    if(data.format === 'audio') {
                        const audio = document.createElement('audio');
                        audio.controls = true;
                        audio.src = data.stream_url;
                        previewContainer.appendChild(audio);
                    } else {
                        const video = document.createElement('video');
                        video.controls = true;
                        video.autoplay = true;
                        video.muted = true;
                        video.src = data.stream_url;
                        previewContainer.appendChild(video);
                    }

                    resultBox.style.display = 'block';
                } else {
                    alert('Error: ' + data.message);
                }
            } catch(e) {
                alert('Network connection error.');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fa-solid fa-atom"></i> Initiate Extract System';
            }
        }
    </script>
</body>
</html>
"""

ADMIN_LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login - SPEED_X</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { background: #070913; color: #fff; font-family: 'Poppins', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: #0b0f19; border: 1px solid rgba(0,255,200,0.3); padding: 35px; border-radius: 18px; width: 100%; max-width: 380px; box-shadow: 0 15px 30px rgba(0,0,0,0.6); }
        h2 { color: #00ffc8; text-align: center; margin-bottom: 20px; font-size: 20px; }
        .input-group { margin-bottom: 16px; }
        label { display: block; font-size: 12px; color: #9ca3af; margin-bottom: 6px; }
        input { width: 100%; padding: 12px; background: rgba(17, 24, 39, 0.8); border: 1px solid #1f2937; border-radius: 10px; color: #fff; outline: none; font-size: 13px; }
        input:focus { border-color: #00ffc8; }
        .btn { width: 100%; padding: 12px; background: #00ffc8; color: #070913; border: none; border-radius: 10px; font-weight: 700; font-size: 13px; cursor: pointer; margin-top: 10px; text-transform: uppercase; }
        .error { color: #ef4444; font-size: 12px; text-align: center; margin-bottom: 12px; }
        .back-link { display: block; text-align: center; margin-top: 18px; color: #9ca3af; text-decoration: none; font-size: 12px; }
        .back-link:hover { color: #00ffc8; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>ADMIN PORTAL</h2>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <div class="input-group">
                <label>Email Address</label>
                <input type="email" name="email" value="admin@nirob.com" required>
            </div>
            <div class="input-group">
                <label>Password</label>
                <input type="password" name="password" placeholder="Enter password (default: admin)" required>
            </div>
            <button type="submit" class="btn">Login securely</button>
        </form>
        <a href="/" class="back-link">&larr; Back to Home</a>
    </div>
</body>
</html>
"""

ADMIN_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - SPEED_X</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Poppins', sans-serif; }
        body { background: #070913; color: #fff; display: flex; min-height: 100vh; }
        .sidebar { width: 250px; background: #0b0f19; border-right: 1px solid #1f2937; padding: 25px 18px; display: flex; flex-direction: column; justify-content: space-between; }
        .sidebar h2 { color: #00ffc8; font-size: 18px; margin-bottom: 25px; font-weight: 700; }
        .sidebar a { display: flex; align-items: center; gap: 10px; color: #9ca3af; text-decoration: none; padding: 10px 14px; border-radius: 8px; margin-bottom: 6px; transition: 0.2s; font-size: 13px; }
        .sidebar a:hover, .sidebar a.active { background: rgba(0,255,200,0.1); color: #00ffc8; }
        
        .main-content { flex: 1; padding: 35px; overflow-y: auto; max-width: 900px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 1px solid #1f2937; padding-bottom: 15px; }
        .header h1 { font-size: 22px; color: #fff; }
        
        .card { background: #0b0f19; border: 1px solid #1f2937; border-radius: 14px; padding: 22px; margin-bottom: 20px; box-shadow: 0 8px 20px rgba(0,0,0,0.3); }
        .card h3 { font-size: 16px; color: #00ffc8; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
        
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .form-group { margin-bottom: 14px; }
        .form-group.full { grid-column: span 2; }
        label { display: block; font-size: 12px; color: #9ca3af; margin-bottom: 6px; font-weight: 500; }
        input[type="text"], textarea { width: 100%; padding: 10px 12px; background: rgba(17, 24, 39, 0.8); border: 1px solid #374151; border-radius: 8px; color: #fff; font-size: 13px; outline: none; }
        input:focus, textarea:focus { border-color: #00ffc8; }
        textarea { resize: vertical; height: 90px; }
        
        .toggle-switch { display: flex; align-items: center; gap: 10px; cursor: pointer; margin-top: 4px; }
        .toggle-switch input { display: none; }
        .slider { width: 44px; height: 24px; background: #374151; border-radius: 12px; position: relative; transition: 0.3s; }
        .slider::before { content: ''; position: absolute; width: 18px; height: 18px; background: #fff; border-radius: 50%; top: 3px; left: 3px; transition: 0.3s; }
        input:checked + .slider { background: #00ffc8; }
        input:checked + .slider::before { transform: translateX(20px); }
        
        .btn-save { padding: 12px 22px; background: #00ffc8; color: #070913; border: none; border-radius: 10px; font-weight: 700; cursor: pointer; transition: 0.2s; font-size: 13px; text-transform: uppercase; }
        .btn-save:hover { background: #00b894; }
        
        .alert-success { background: rgba(0,255,200,0.1); border: 1px solid rgba(0,255,200,0.3); color: #00ffc8; padding: 10px 15px; border-radius: 8px; margin-bottom: 18px; font-size: 13px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div>
            <h2>SPEED_X ADMIN</h2>
            <a href="/admin/dashboard" class="active"><i class="fa-solid fa-chart-line"></i> Dashboard</a>
            <a href="/" target="_blank"><i class="fa-solid fa-globe"></i> View Website</a>
        </div>
        <div>
            <a href="/admin/logout" style="color: #ef4444;"><i class="fa-solid fa-right-from-bracket"></i> Logout</a>
        </div>
    </div>
    
    <div class="main-content">
        <div class="header">
            <h1>Control Panel Dashboard</h1>
            <span style="color: #9ca3af; font-size: 12px;">Logged in as <b>admin@nirob.com</b></span>
        </div>

        {% if saved %}
        <div class="alert-success"><i class="fa-solid fa-check-circle"></i> Settings updated successfully!</div>
        {% endif %}

        <form method="POST">
            <div class="card">
                <h3><i class="fa-solid fa-power-off"></i> Website Status Control</h3>
                <div class="form-group">
                    <label>Website Online / Offline Switch</label>
                    <label class="toggle-switch">
                        <input type="checkbox" name="site_status" {% if config.site_status %}checked{% endif %}>
                        <div class="slider"></div>
                    </label>
                    <span style="font-size: 11px; color: #6b7280; margin-top: 5px; display: block;">When turned off, visitors will see the custom maintenance screen.</span>
                </div>
                <div class="form-group" style="margin-top: 12px;">
                    <label>Maintenance Custom Message</label>
                    <textarea name="maintenance_msg">{{ config.maintenance_msg }}</textarea>
                </div>
            </div>

            <div class="card">
                <h3><i class="fa-solid fa-bullhorn"></i> Dynamic Popup Controller</h3>
                <div class="form-grid">
                    <div class="form-group">
                        <label>Popup Feature Status</label>
                        <label class="toggle-switch">
                            <input type="checkbox" name="popup_active" {% if config.popup_active %}checked{% endif %}>
                            <div class="slider"></div>
                        </label>
                    </div>
                    <div class="form-group">
                        <label>Show Action Button in Popup</label>
                        <label class="toggle-switch">
                            <input type="checkbox" name="popup_show_button" {% if config.popup_show_button %}checked{% endif %}>
                            <div class="slider"></div>
                        </label>
                    </div>
                    <div class="form-group full">
                        <label>Popup Title Heading</label>
                        <input type="text" name="popup_title" value="{{ config.popup_title }}" required>
                    </div>
                    <div class="form-group full">
                        <label>Popup Description / Announcement Text</label>
                        <textarea name="popup_content" required>{{ config.popup_content }}</textarea>
                    </div>
                    <div class="form-group">
                        <label>Button Label Text</label>
                        <input type="text" name="popup_btn_text" value="{{ config.popup_btn_text }}" required>
                    </div>
                    <div class="form-group">
                        <label>Button Target URL</label>
                        <input type="text" name="popup_btn_url" value="{{ config.popup_btn_url }}" required>
                    </div>
                </div>
            </div>

            <button type="submit" class="btn-save"><i class="fa-solid fa-floppy-disk"></i> Save All Changes</button>
        </form>
    </div>
</body>
</html>
"""

# --- Flask Routes ---

@app.route('/')
def index():
    return render_template_string(INDEX_TEMPLATE, config=app_config)

@app.route('/admin', methods=['GET', 'POST'])
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email == ADMIN_CREDENTIALS['email'] and password == ADMIN_CREDENTIALS['password']:
            session['admin_logged'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Invalid Email or Password! (Use admin@nirob.com / admin)"
    return render_template_string(ADMIN_LOGIN_TEMPLATE, error=error)

@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    
    saved = False
    if request.method == 'POST':
        app_config['site_status'] = True if request.form.get('site_status') == 'on' else False
        app_config['maintenance_msg'] = request.form.get('maintenance_msg', app_config['maintenance_msg'])
        app_config['popup_active'] = True if request.form.get('popup_active') == 'on' else False
        app_config['popup_show_button'] = True if request.form.get('popup_show_button') == 'on' else False
        app_config['popup_title'] = request.form.get('popup_title', app_config['popup_title'])
        app_config['popup_content'] = request.form.get('popup_content', app_config['popup_content'])
        app_config['popup_btn_text'] = request.form.get('popup_btn_text', app_config['popup_btn_text'])
        app_config['popup_btn_url'] = request.form.get('popup_btn_url', app_config['popup_btn_url'])
        saved = True

    return render_template_string(ADMIN_DASHBOARD_TEMPLATE, config=app_config, saved=saved)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged', None)
    return redirect(url_for('admin_login'))

@app.route('/api/process', methods=['POST'])
def api_process():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    format_type = data.get('format', 'video')
    
    if not url:
        return jsonify({'success': False, 'message': 'Please provide a valid URL.'})

    platform = detect_platform(url)
    success, file_path, unique_id, filesize = download_media(url, platform, format_type)
    
    if success and unique_id:
        download_files[unique_id] = file_path
        filename = os.path.basename(file_path)
        return jsonify({
            'success': True,
            'platform': platform,
            'format': format_type,
            'filename': filename,
            'filesize': filesize,
            'stream_url': f'/api/stream/{unique_id}',
            'download_url': f'/api/download/{unique_id}'
        })
    else:
        return jsonify({'success': False, 'message': file_path})

@app.route('/api/stream/<file_id>')
def stream_file_route(file_id):
    path = download_files.get(file_id)
    if path and os.path.exists(path):
        return send_file(path)
    return "Stream expired or not found!", 404

@app.route('/api/download/<file_id>')
def download_file_route(file_id):
    path = download_files.get(file_id)
    if path and os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "File expired or not found!", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

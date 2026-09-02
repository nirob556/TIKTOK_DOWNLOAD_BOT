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
    "site_status": True,
    "maintenance_msg": "Website is currently under maintenance by NIROB BBZ. Please check back later!",
    "popup_active": True,
    "popup_title": "🔥 SPEED_X VIP NOTICE 🔥",
    "popup_content": "Welcome to SPEED_X Ultimate Core System! Join our Telegram channels and enjoy VIP automated downloading & tools.",
    "popup_btn_text": "Join Telegram",
    "popup_btn_url": "https://t.me/SPEED_X_OFFICIAL1",
    "popup_show_button": True
}

ADMIN_CREDENTIALS = {
    "email": "admin@nirob.com",
    "password": "admin"
}

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
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: #070913; 
            color: #fff; 
            font-family: 'Poppins', sans-serif; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            height: 100vh; 
            margin: 0; 
            text-align: center;
            overflow: hidden;
        }
        .maintenance-wrapper {
            position: relative;
            width: 100%;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            background: radial-gradient(ellipse at center, #0a0f1a 0%, #070913 100%);
        }
        .maintenance-box {
            background: rgba(11, 15, 25, 0.85);
            padding: 50px 45px;
            border-radius: 25px;
            border: 1px solid rgba(0, 255, 200, 0.15);
            box-shadow: 0 0 60px rgba(0, 255, 200, 0.05), inset 0 0 60px rgba(0, 255, 200, 0.02);
            max-width: 500px;
            width: 90%;
            position: relative;
            z-index: 2;
            backdrop-filter: blur(20px);
            animation: floatIn 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        }
        .maintenance-box::before {
            content: '';
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            border-radius: 27px;
            background: linear-gradient(45deg, transparent, rgba(0, 255, 200, 0.1), transparent, rgba(0, 255, 200, 0.1));
            z-index: -1;
            background-size: 300% 300%;
            animation: borderGlow 4s ease-in-out infinite;
        }
        .mt-icon {
            font-size: 60px;
            margin-bottom: 20px;
            display: block;
            animation: pulseGlow 2s ease-in-out infinite;
        }
        h1 { 
            font-size: 28px; 
            font-weight: 800; 
            background: linear-gradient(135deg, #00ffc8, #00b894);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 12px;
            letter-spacing: 1px;
        }
        p { 
            color: #9ca3af; 
            line-height: 1.8; 
            font-size: 14px;
            -webkit-text-fill-color: #9ca3af;
        }
        .mt-status {
            margin-top: 25px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.05);
        }
        .mt-status span {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #ff4444;
            border-radius: 50%;
            margin-right: 10px;
            animation: blinkRed 1.2s ease-in-out infinite;
        }
        .credit { 
            margin-top: 25px; 
            font-size: 11px; 
            color: #4a5568; 
            text-transform: uppercase; 
            letter-spacing: 3px; 
            font-weight: 600;
        }
        .credit strong { color: #00ffc8; -webkit-text-fill-color: #00ffc8; }
        
        @keyframes floatIn {
            from { opacity: 0; transform: translateY(40px) scale(0.95); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes borderGlow {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        @keyframes pulseGlow {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.08); opacity: 0.8; }
        }
        @keyframes blinkRed {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.2; }
        }
    </style>
</head>
<body>
    <div class="maintenance-wrapper">
        <div class="maintenance-box">
            <span class="mt-icon">🔧</span>
            <h1>SYSTEM OFFLINE</h1>
            <p>{{ msg }}</p>
            <div class="mt-status">
                <span></span> Maintenance Mode Active
            </div>
            <div class="credit">VIP Software Engineered by <strong>NIROB BBZ</strong> © 2026</div>
        </div>
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
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            background: #070913; 
            color: #fff; 
            font-family: 'Poppins', sans-serif; 
            min-height: 100vh; 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            justify-content: center; 
            padding: 20px;
            background-image: 
                radial-gradient(ellipse at 20% 50%, rgba(0, 255, 200, 0.03) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 50%, rgba(0, 255, 200, 0.03) 0%, transparent 50%);
        }
        
        /* Animated Background Particles */
        .bg-particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
            overflow: hidden;
        }
        .particle {
            position: absolute;
            width: 3px;
            height: 3px;
            background: rgba(0, 255, 200, 0.2);
            border-radius: 50%;
            animation: particleFloat linear infinite;
        }
        @keyframes particleFloat {
            0% { transform: translateY(100vh) scale(0); opacity: 0; }
            10% { opacity: 1; }
            90% { opacity: 1; }
            100% { transform: translateY(-10vh) scale(1); opacity: 0; }
        }

        .container { 
            width: 100%; 
            max-width: 460px; 
            background: rgba(11, 15, 25, 0.85);
            border: 1px solid rgba(0, 255, 200, 0.12);
            border-radius: 28px; 
            padding: 30px 28px; 
            box-shadow: 0 25px 60px rgba(0,0,0,0.7), 0 0 40px rgba(0,255,200,0.03);
            position: relative;
            z-index: 1;
            backdrop-filter: blur(20px);
            animation: containerFloat 3s ease-in-out infinite;
        }
        .container::before {
            content: '';
            position: absolute;
            top: -1px;
            left: -1px;
            right: -1px;
            bottom: -1px;
            border-radius: 29px;
            background: linear-gradient(45deg, transparent, rgba(0,255,200,0.08), transparent, rgba(0,255,200,0.05));
            z-index: -1;
            background-size: 400% 400%;
            animation: borderRotate 6s linear infinite;
        }
        @keyframes borderRotate {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        @keyframes containerFloat {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }

        /* Header */
        .main-title { text-align: center; margin-bottom: 28px; }
        .main-title .logo-icon {
            display: inline-block;
            font-size: 38px;
            color: #00ffc8;
            margin-bottom: 6px;
            text-shadow: 0 0 40px rgba(0,255,200,0.4), 0 0 80px rgba(0,255,200,0.1);
            animation: logoPulse 2.5s ease-in-out infinite;
        }
        @keyframes logoPulse {
            0%, 100% { transform: scale(1) rotate(0deg); text-shadow: 0 0 40px rgba(0,255,200,0.4); }
            50% { transform: scale(1.05) rotate(5deg); text-shadow: 0 0 60px rgba(0,255,200,0.7), 0 0 100px rgba(0,255,200,0.2); }
        }
        .main-title h1 { 
            font-size: 22px; 
            font-weight: 800; 
            letter-spacing: 1.5px;
            background: linear-gradient(135deg, #00ffc8, #00d4a8, #00b894);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: none;
        }
        .main-title .sub-title {
            font-size: 10px;
            color: #4a5568;
            text-transform: uppercase;
            letter-spacing: 4px;
            margin-top: 4px;
            font-weight: 600;
        }
        .main-title .sub-title i { color: #00ffc8; margin: 0 4px; }

        /* Card */
        .card-box { 
            background: rgba(17, 24, 39, 0.6); 
            border: 1px solid rgba(0, 255, 200, 0.06); 
            border-radius: 18px; 
            padding: 18px; 
            margin-bottom: 16px; 
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        .card-box:hover { 
            border-color: rgba(0,255,200,0.15); 
            box-shadow: 0 0 30px rgba(0,255,200,0.02);
            transform: translateY(-2px);
        }
        
        .card-label { 
            font-size: 10px; 
            text-transform: uppercase; 
            color: #6b7280; 
            letter-spacing: 1.2px; 
            margin-bottom: 10px; 
            display: flex; 
            align-items: center; 
            gap: 8px; 
            font-weight: 600; 
        }
        .card-label i { color: #00ffc8; font-size: 12px; }

        .input-row { display: flex; gap: 8px; }
        input[type="text"] { 
            flex: 1; 
            padding: 12px 16px; 
            background: rgba(7, 9, 19, 0.9); 
            border: 1px solid #1f2937; 
            border-radius: 12px; 
            color: #fff; 
            font-size: 13px; 
            outline: none; 
            transition: all 0.3s ease;
            font-family: 'Poppins', sans-serif;
        }
        input[type="text"]:focus { 
            border-color: #00ffc8; 
            box-shadow: 0 0 20px rgba(0,255,200,0.08);
        }
        input[type="text"]::placeholder { color: #4a5568; }
        
        .action-btn { 
            background: linear-gradient(135deg, #00ffc8, #00b894); 
            color: #070913; 
            border: none; 
            border-radius: 12px; 
            padding: 0 18px; 
            font-weight: 700; 
            font-size: 11px; 
            cursor: pointer; 
            text-transform: uppercase; 
            transition: all 0.3s ease; 
            white-space: nowrap; 
            box-shadow: 0 4px 15px rgba(0,255,200,0.15);
            letter-spacing: 0.5px;
        }
        .action-btn:hover { 
            transform: scale(1.03); 
            box-shadow: 0 6px 25px rgba(0,255,200,0.25);
        }

        .paste-row-btn { 
            background: rgba(31, 41, 55, 0.6); 
            color: #d1d5db; 
            border: 1px solid #1f2937; 
            border-radius: 12px; 
            padding: 12px; 
            font-size: 12px; 
            cursor: pointer; 
            display: flex; 
            align-items: center; 
            gap: 10px; 
            justify-content: center; 
            width: 100%; 
            margin-bottom: 12px; 
            transition: all 0.3s ease;
            font-weight: 500;
            letter-spacing: 0.3px;
        }
        .paste-row-btn:hover { 
            background: rgba(31, 41, 55, 0.9); 
            color: #fff; 
            border-color: rgba(0,255,200,0.3);
            box-shadow: 0 0 25px rgba(0,255,200,0.05);
            transform: translateY(-1px);
        }
        .paste-row-btn i { color: #00ffc8; }

        /* Format Grid */
        .format-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
        .format-option { 
            background: rgba(7, 9, 19, 0.8); 
            border: 1px solid #1f2937; 
            border-radius: 14px; 
            padding: 14px 10px; 
            text-align: center; 
            cursor: pointer; 
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            gap: 6px; 
            font-size: 11px; 
            font-weight: 600; 
            color: #6b7280;
            position: relative;
            overflow: hidden;
        }
        .format-option i { font-size: 20px; color: #4a5568; transition: all 0.3s ease; }
        .format-option .badge {
            font-size: 8px;
            background: rgba(0,255,200,0.1);
            padding: 2px 8px;
            border-radius: 20px;
            color: #00ffc8;
            margin-top: 2px;
            opacity: 0;
            transition: all 0.3s ease;
        }
        .format-option.active .badge { opacity: 1; }
        .format-option::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(0,255,200,0.05), transparent);
            opacity: 0;
            transition: all 0.4s ease;
        }
        .format-option:hover::after { opacity: 1; }
        .format-option:hover { 
            border-color: rgba(0,255,200,0.2); 
            transform: translateY(-2px);
        }
        .format-option.active { 
            border-color: #00ffc8; 
            background: rgba(0,255,200,0.06); 
            color: #fff; 
            box-shadow: 0 0 25px rgba(0,255,200,0.06), inset 0 0 25px rgba(0,255,200,0.02);
            transform: translateY(-2px);
        }
        .format-option.active i { color: #00ffc8; }

        /* Extract Button */
        .extract-btn { 
            width: 100%; 
            padding: 16px; 
            background: linear-gradient(135deg, #00ffc8 0%, #00b894 50%, #009b7a 100%);
            color: #070913; 
            border: none; 
            border-radius: 14px; 
            font-weight: 700; 
            font-size: 13px; 
            text-transform: uppercase; 
            cursor: pointer; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            gap: 10px; 
            box-shadow: 0 6px 30px rgba(0,255,200,0.2); 
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            letter-spacing: 0.8px;
            position: relative;
            overflow: hidden;
        }
        .extract-btn::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
            opacity: 0;
            transition: all 0.5s ease;
        }
        .extract-btn:hover::before { opacity: 1; }
        .extract-btn:hover { 
            transform: translateY(-3px) scale(1.01); 
            box-shadow: 0 10px 40px rgba(0,255,200,0.35);
        }
        .extract-btn:active { transform: scale(0.98); }
        .extract-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none !important;
        }
        .extract-btn i { font-size: 16px; }

        /* Result Box */
        .result-box { 
            margin-top: 18px; 
            background: rgba(7, 9, 19, 0.9); 
            border: 1px solid rgba(0,255,200,0.2); 
            border-radius: 18px; 
            padding: 18px; 
            display: none; 
            animation: successPop 0.7s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; 
            box-shadow: 0 0 40px rgba(0,255,200,0.05);
            position: relative;
            overflow: hidden;
        }
        .result-box::before {
            content: '';
            position: absolute;
            top: -100%;
            left: -100%;
            width: 300%;
            height: 300%;
            background: radial-gradient(circle at 30% 50%, rgba(0,255,200,0.03) 0%, transparent 50%);
            animation: resultGlow 8s linear infinite;
            pointer-events: none;
        }
        @keyframes resultGlow {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .result-box .result-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
            position: relative;
            z-index: 1;
        }
        .result-box .result-header h3 { 
            font-size: 14px; 
            color: #00ffc8; 
            font-weight: 700; 
            text-shadow: 0 0 20px rgba(0,255,200,0.2);
        }
        .result-box .result-header .check-icon {
            display: inline-flex;
            width: 28px;
            height: 28px;
            background: rgba(0,255,200,0.1);
            border-radius: 50%;
            align-items: center;
            justify-content: center;
            color: #00ffc8;
            font-size: 14px;
            animation: bounceCheck 0.8s ease infinite alternate;
            border: 1px solid rgba(0,255,200,0.2);
        }
        @keyframes bounceCheck {
            from { transform: scale(1); }
            to { transform: scale(1.1); }
        }
        @keyframes successPop {
            0% { opacity: 0; transform: scale(0.9) translateY(20px); }
            100% { opacity: 1; transform: scale(1) translateY(0); }
        }

        .preview-container { 
            width: 100%; 
            border-radius: 12px; 
            overflow: hidden; 
            background: #000; 
            margin-bottom: 12px; 
            border: 1px solid rgba(0,255,200,0.08); 
            display: flex; 
            justify-content: center; 
            align-items: center;
            position: relative;
            z-index: 1;
            min-height: 100px;
        }
        .preview-container video, 
        .preview-container audio { 
            width: 100%; 
            max-height: 220px; 
            outline: none; 
            display: block;
        }
        
        .file-info { 
            font-size: 12px; 
            color: #9ca3af; 
            margin-bottom: 14px; 
            word-break: break-all; 
            line-height: 1.8; 
            background: rgba(0,0,0,0.2); 
            padding: 10px 14px; 
            border-radius: 10px;
            position: relative;
            z-index: 1;
            border: 1px solid rgba(255,255,255,0.02);
        }
        .file-info .label { color: #6b7280; font-weight: 500; }
        .file-info .value { color: #d1d5db; }
        
        .download-action-btn { 
            width: 100%; 
            padding: 14px; 
            background: linear-gradient(135deg, #2563eb, #1d4ed8); 
            color: #fff; 
            border-radius: 12px; 
            text-align: center; 
            text-decoration: none; 
            font-weight: 600; 
            font-size: 12px; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            gap: 10px; 
            box-shadow: 0 4px 20px rgba(37,99,235,0.2); 
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            position: relative;
            z-index: 1;
        }
        .download-action-btn:hover { 
            transform: translateY(-2px) scale(1.01); 
            box-shadow: 0 8px 30px rgba(37,99,235,0.4);
            background: linear-gradient(135deg, #1d4ed8, #1e40af);
        }

        /* Popup Styles */
        .modal-overlay { 
            position: fixed; 
            top: 0; 
            left: 0; 
            width: 100%; 
            height: 100%; 
            background: rgba(0,0,0,0.85); 
            backdrop-filter: blur(12px); 
            display: none; 
            justify-content: center; 
            align-items: center; 
            z-index: 9999; 
            padding: 20px; 
            animation: overlayFade 0.3s ease forwards;
        }
        @keyframes overlayFade {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        .modal-card { 
            background: rgba(11, 15, 25, 0.95); 
            border: 1px solid rgba(0,255,200,0.2); 
            border-radius: 24px; 
            width: 100%; 
            max-width: 380px; 
            padding: 30px 28px 28px; 
            text-align: center; 
            box-shadow: 0 30px 60px rgba(0,0,0,0.6), 0 0 40px rgba(0,255,200,0.05); 
            position: relative; 
            animation: scaleUp 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        }
        @keyframes scaleUp {
            from { transform: scale(0.85) translateY(20px); opacity: 0; }
            to { transform: scale(1) translateY(0); opacity: 1; }
        }
        .modal-icon { 
            width: 60px; 
            height: 60px; 
            background: rgba(0,255,200,0.08); 
            border-radius: 50%; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            margin: 0 auto 16px; 
            color: #00ffc8; 
            font-size: 26px; 
            border: 1px solid rgba(0,255,200,0.15);
            animation: modalIconPulse 2s ease-in-out infinite;
        }
        @keyframes modalIconPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); box-shadow: 0 0 30px rgba(0,255,200,0.1); }
        }
        .modal-card h2 { 
            font-size: 19px; 
            color: #fff; 
            margin-bottom: 8px; 
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .modal-card p { 
            color: #9ca3af; 
            font-size: 13px; 
            line-height: 1.7; 
            margin-bottom: 20px; 
        }
        .modal-btn { 
            display: block; 
            width: 100%; 
            padding: 14px; 
            background: linear-gradient(135deg, #00ffc8, #00b894); 
            color: #070913; 
            font-weight: 700; 
            border-radius: 12px; 
            text-decoration: none; 
            font-size: 13px; 
            box-shadow: 0 4px 20px rgba(0,255,200,0.2); 
            transition: all 0.3s ease;
            letter-spacing: 0.5px;
        }
        .modal-btn:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 8px 30px rgba(0,255,200,0.35);
        }
        .modal-close { 
            position: absolute; 
            top: 14px; 
            right: 18px; 
            background: none; 
            border: none; 
            color: #6b7280; 
            font-size: 22px; 
            cursor: pointer; 
            transition: all 0.3s ease;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
        }
        .modal-close:hover { 
            color: #fff; 
            background: rgba(255,255,255,0.05);
            transform: rotate(90deg);
        }

        .footer { 
            margin-top: 22px; 
            text-align: center; 
            font-size: 10px; 
            color: #374151; 
            letter-spacing: 1.5px; 
            text-transform: uppercase;
            font-weight: 600;
        }
        .footer span { 
            color: #00ffc8; 
            font-weight: 700; 
            -webkit-text-fill-color: #00ffc8;
            text-shadow: 0 0 20px rgba(0,255,200,0.1);
        }
        .footer i { color: #ff4444; margin: 0 4px; }

        /* Loading Spinner */
        .spinner {
            display: inline-block;
            width: 18px;
            height: 18px;
            border: 2px solid rgba(7, 9, 19, 0.2);
            border-top-color: #070913;
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Responsive */
        @media (max-width: 480px) {
            .container { padding: 20px 16px; }
            .main-title h1 { font-size: 18px; }
            .format-option { padding: 12px 8px; font-size: 10px; }
            .format-option i { font-size: 17px; }
            .extract-btn { font-size: 12px; padding: 14px; }
        }
    </style>
</head>
<body>

    <!-- Background Particles -->
    <div class="bg-particles" id="particles"></div>

    <!-- Popup Modal -->
    {% if config.popup_active %}
    <div class="modal-overlay" id="popupModal">
        <div class="modal-card">
            <button class="modal-close" onclick="closePopup()">&times;</button>
            <div class="modal-icon"><i class="fa-solid fa-bolt"></i></div>
            <h2>{{ config.popup_title }}</h2>
            <p>{{ config.popup_content }}</p>
            {% if config.popup_show_button %}
            <a href="{{ config.popup_btn_url }}" target="_blank" class="modal-btn">{{ config.popup_btn_text }} <i class="fa-solid fa-arrow-right"></i></a>
            {% endif %}
        </div>
    </div>
    <script>
        window.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => { 
                document.getElementById('popupModal').style.display = 'flex'; 
            }, 500);
        });
        function closePopup() { 
            document.getElementById('popupModal').style.display = 'none'; 
        }
    </script>
    {% endif %}

    <div class="container">
        <div class="main-title">
            <div class="logo-icon"><i class="fa-solid fa-bolt"></i></div>
            <h1>SPEED_X VIP DASHBOARD</h1>
            <div class="sub-title"><i class="fa-regular fa-circle"></i> ULTIMATE CORE SYSTEM <i class="fa-regular fa-circle"></i></div>
        </div>

        <!-- Telegram Signature ID Box -->
        <div class="card-box">
            <div class="card-label"><i class="fa-solid fa-fingerprint"></i> Telegram User Account Signature ID</div>
            <div class="input-row">
                <input type="text" id="tgId" placeholder="Enter Telegram ID..." value="7224513731">
                <button type="button" class="action-btn" onclick="saveTgId()"><i class="fa-regular fa-floppy-disk"></i> Save</button>
            </div>
        </div>

        <!-- Network Link Resource Box -->
        <div class="card-box">
            <div class="card-label"><i class="fa-solid fa-link"></i> Enter Media Link (TikTok / Facebook / Instagram)</div>
            
            <div class="input-row" style="margin-bottom: 10px;">
                <input type="text" id="mediaUrl" placeholder="Paste link here...">
            </div>
            <button type="button" class="paste-row-btn" id="pasteBtn"><i class="fa-solid fa-paste"></i> Paste Link from Clipboard</button>

            <!-- Format Selector -->
            <div class="format-grid">
                <div class="format-option active" id="optVideo" onclick="setFormat('video')">
                    <i class="fa-solid fa-video"></i>
                    MP4 Video
                    <span class="badge">HD</span>
                </div>
                <div class="format-option" id="optAudio" onclick="setFormat('audio')">
                    <i class="fa-solid fa-music"></i>
                    Audio MP3
                    <span class="badge">320kbps</span>
                </div>
            </div>

            <button type="button" class="extract-btn" id="submitBtn" onclick="processMedia()">
                <i class="fa-solid fa-atom"></i> Initiate Extract System
            </button>

            <!-- Success Box with Live Preview & Neon Animation -->
            <div class="result-box" id="resultBox">
                <div class="result-header">
                    <span class="check-icon"><i class="fa-solid fa-check"></i></span>
                    <h3>Extraction Successful!</h3>
                </div>
                <div class="preview-container" id="previewContainer"></div>
                <div class="file-info" id="fileInfo"></div>
                <a href="#" id="downloadLink" class="download-action-btn"><i class="fa-solid fa-download"></i> Download Processed File</a>
            </div>
        </div>

        <div class="footer"><i class="fa-regular fa-heart"></i> VIP Software Engineered by <span>NIROB BBZ</span> © 2026 <i class="fa-regular fa-heart"></i></div>
    </div>

    <script>
        // Generate Background Particles
        (function() {
            const container = document.getElementById('particles');
            for(let i = 0; i < 35; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                particle.style.left = Math.random() * 100 + '%';
                particle.style.width = (Math.random() * 4 + 1) + 'px';
                particle.style.height = particle.style.width;
                particle.style.animationDuration = (Math.random() * 20 + 15) + 's';
                particle.style.animationDelay = (Math.random() * 15) + 's';
                particle.style.opacity = Math.random() * 0.4 + 0.1;
                container.appendChild(particle);
            }
        })();

        let currentFormat = 'video';

        function setFormat(fmt) {
            currentFormat = fmt;
            const videoOpt = document.getElementById('optVideo');
            const audioOpt = document.getElementById('optAudio');
            if(fmt === 'video') {
                videoOpt.classList.add('active');
                audioOpt.classList.remove('active');
            } else {
                audioOpt.classList.add('active');
                videoOpt.classList.remove('active');
            }
        }

        function saveTgId() {
            const id = document.getElementById('tgId').value.trim();
            if(id) {
                alert('✅ Telegram Signature ID Saved Successfully: ' + id);
            } else {
                alert('⚠️ Please enter a valid ID.');
            }
        }

        document.getElementById('pasteBtn').addEventListener('click', async () => {
            try {
                const text = await navigator.clipboard.readText();
                document.getElementById('mediaUrl').value = text;
                // Visual feedback
                const btn = document.getElementById('pasteBtn');
                btn.innerHTML = '<i class="fa-solid fa-check"></i> Pasted!';
                btn.style.borderColor = '#00ffc8';
                setTimeout(() => {
                    btn.innerHTML = '<i class="fa-solid fa-paste"></i> Paste Link from Clipboard';
                    btn.style.borderColor = '#1f2937';
                }, 1500);
            } catch (err) {
                alert('⚠️ Clipboard access denied. Please paste manually.');
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
                alert('⚠️ Please enter or paste a valid link first.');
                return;
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner"></span> Extracting & Processing...';
            resultBox.style.display = 'none';

            try {
                const res = await fetch('/api/process', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ url: url, format: currentFormat })
                });
                const data = await res.json();

                if(data.success) {
                    const platformEmojis = {
                        'tiktok': '📱',
                        'facebook': '📘',
                        'instagram': '📸',
                        'unknown': '🔗'
                    };
                    const platformDisplay = data.platform.toUpperCase();
                    const emoji = platformEmojis[data.platform] || '🔗';
                    
                    fileInfo.innerHTML = `
                        <span class="label">${emoji} Platform:</span> <span class="value">${platformDisplay}</span> &nbsp;|&nbsp; 
                        <span class="label">📦 Size:</span> <span class="value">${data.filesize}</span> &nbsp;|&nbsp; 
                        <span class="label">📄 File:</span> <span class="value">${data.filename}</span>
                    `;
                    downloadLink.href = data.download_url;
                    
                    // Render Proper Preview
                    previewContainer.innerHTML = '';
                    if(data.format === 'audio') {
                        const audio = document.createElement('audio');
                        audio.controls = true;
                        audio.src = data.stream_url;
                        audio.style.width = '100%';
                        previewContainer.appendChild(audio);
                    } else {
                        const video = document.createElement('video');
                        video.controls = true;
                        video.autoplay = true;
                        video.muted = true;
                        video.src = data.stream_url;
                        video.style.width = '100%';
                        previewContainer.appendChild(video);
                    }

                    resultBox.style.display = 'block';
                    // Scroll to result
                    resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } else {
                    alert('❌ Error: ' + data.message);
                }
            } catch(e) {
                alert('⚠️ Network connection error. Please try again.');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fa-solid fa-atom"></i> Initiate Extract System';
            }
        }

        // Enter key support
        document.getElementById('mediaUrl').addEventListener('keypress', function(e) {
            if(e.key === 'Enter') {
                e.preventDefault();
                processMedia();
            }
        });
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
    <title>Admin Login - SPEED_X VIP</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: #070913; 
            color: #fff; 
            font-family: 'Poppins', sans-serif; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            height: 100vh; 
            margin: 0;
            background-image: radial-gradient(ellipse at center, #0a0f1a 0%, #070913 100%);
        }
        .login-wrapper {
            width: 100%;
            max-width: 400px;
            padding: 20px;
        }
        .login-card { 
            background: rgba(11, 15, 25, 0.9); 
            border: 1px solid rgba(0,255,200,0.12); 
            padding: 40px 35px; 
            border-radius: 24px; 
            box-shadow: 0 25px 60px rgba(0,0,0,0.5), 0 0 40px rgba(0,255,200,0.02);
            backdrop-filter: blur(20px);
            position: relative;
            overflow: hidden;
        }
        .login-card::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at 30% 40%, rgba(0,255,200,0.03) 0%, transparent 50%);
            animation: rotateBg 20s linear infinite;
            pointer-events: none;
        }
        @keyframes rotateBg {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .login-logo {
            text-align: center;
            margin-bottom: 25px;
            position: relative;
            z-index: 1;
        }
        .login-logo i {
            font-size: 40px;
            color: #00ffc8;
            text-shadow: 0 0 40px rgba(0,255,200,0.3);
        }
        .login-logo h2 { 
            color: #fff; 
            font-size: 20px; 
            font-weight: 700;
            margin-top: 6px;
        }
        .login-logo span {
            color: #6b7280;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        .input-group { 
            margin-bottom: 16px; 
            position: relative;
            z-index: 1;
        }
        label { 
            display: block; 
            font-size: 11px; 
            color: #9ca3af; 
            margin-bottom: 5px; 
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        input { 
            width: 100%; 
            padding: 12px 16px; 
            background: rgba(7, 9, 19, 0.8); 
            border: 1px solid #1f2937; 
            border-radius: 12px; 
            color: #fff; 
            outline: none; 
            font-size: 13px; 
            font-family: 'Poppins', sans-serif;
            transition: all 0.3s ease;
        }
        input:focus { 
            border-color: #00ffc8; 
            box-shadow: 0 0 20px rgba(0,255,200,0.05);
        }
        .btn { 
            width: 100%; 
            padding: 13px; 
            background: linear-gradient(135deg, #00ffc8, #00b894); 
            color: #070913; 
            border: none; 
            border-radius: 12px; 
            font-weight: 700; 
            font-size: 13px; 
            cursor: pointer; 
            margin-top: 6px; 
            text-transform: uppercase;
            letter-spacing: 0.8px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 20px rgba(0,255,200,0.15);
            position: relative;
            z-index: 1;
        }
        .btn:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 8px 30px rgba(0,255,200,0.25);
        }
        .error { 
            color: #ff6b6b; 
            font-size: 12px; 
            text-align: center; 
            margin-bottom: 14px; 
            background: rgba(255,0,0,0.05);
            padding: 10px;
            border-radius: 10px;
            border: 1px solid rgba(255,0,0,0.1);
            position: relative;
            z-index: 1;
        }
        .back-link { 
            display: block; 
            text-align: center; 
            margin-top: 16px; 
            color: #6b7280; 
            text-decoration: none; 
            font-size: 12px; 
            transition: all 0.3s ease;
            position: relative;
            z-index: 1;
        }
        .back-link:hover { color: #00ffc8; }
        .back-link i { margin-right: 6px; }
    </style>
</head>
<body>
    <div class="login-wrapper">
        <div class="login-card">
            <div class="login-logo">
                <i class="fa-solid fa-shield-halved"></i>
                <h2>ADMIN PORTAL</h2>
                <span>Secure Access Only</span>
            </div>
            {% if error %}
            <div class="error"><i class="fa-solid fa-triangle-exclamation"></i> {{ error }}</div>
            {% endif %}
            <form method="POST">
                <div class="input-group">
                    <label><i class="fa-regular fa-envelope"></i> Email Address</label>
                    <input type="email" name="email" value="admin@nirob.com" required>
                </div>
                <div class="input-group">
                    <label><i class="fa-solid fa-lock"></i> Password</label>
                    <input type="password" name="password" placeholder="Enter password..." required>
                </div>
                <button type="submit" class="btn"><i class="fa-solid fa-arrow-right-to-bracket"></i> Login Securely</button>
            </form>
            <a href="/" class="back-link"><i class="fa-solid fa-arrow-left"></i> Back to Home</a>
        </div>
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
    <title>Admin Dashboard - SPEED_X VIP</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: #070913; 
            color: #fff; 
            font-family: 'Poppins', sans-serif; 
            display: flex; 
            min-height: 100vh; 
        }
        .sidebar { 
            width: 240px; 
            background: rgba(11, 15, 25, 0.95); 
            border-right: 1px solid #1f2937; 
            padding: 28px 18px; 
            display: flex; 
            flex-direction: column; 
            justify-content: space-between;
            position: sticky;
            top: 0;
            height: 100vh;
        }
        .sidebar-brand h2 { 
            color: #00ffc8; 
            font-size: 17px; 
            font-weight: 800; 
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .sidebar-brand h2 i { font-size: 20px; }
        .sidebar-brand span {
            font-size: 9px;
            color: #4a5568;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-top: 2px;
            display: block;
        }
        .sidebar-nav { margin-top: 30px; }
        .sidebar-nav a { 
            display: flex; 
            align-items: center; 
            gap: 12px; 
            color: #9ca3af; 
            text-decoration: none; 
            padding: 10px 14px; 
            border-radius: 10px; 
            margin-bottom: 4px; 
            transition: all 0.3s ease; 
            font-size: 13px; 
            font-weight: 500;
        }
        .sidebar-nav a:hover, 
        .sidebar-nav a.active { 
            background: rgba(0,255,200,0.06); 
            color: #00ffc8; 
            border-left: 2px solid #00ffc8;
        }
        .sidebar-nav a i { width: 20px; text-align: center; }
        .sidebar-footer { 
            border-top: 1px solid #1f2937; 
            padding-top: 16px; 
        }
        .sidebar-footer a {
            display: flex;
            align-items: center;
            gap: 12px;
            color: #ef4444;
            text-decoration: none;
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        .sidebar-footer a:hover { background: rgba(239,68,68,0.05); }
        
        .main-content { 
            flex: 1; 
            padding: 35px 40px; 
            overflow-y: auto; 
            max-width: 1000px;
            margin: 0 auto;
        }
        .header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 30px; 
            border-bottom: 1px solid #1f2937; 
            padding-bottom: 18px; 
        }
        .header h1 { 
            font-size: 22px; 
            font-weight: 700; 
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .header h1 i { color: #00ffc8; }
        .header .user-info { 
            color: #6b7280; 
            font-size: 12px; 
            background: rgba(255,255,255,0.03);
            padding: 8px 16px;
            border-radius: 20px;
            border: 1px solid #1f2937;
        }
        .header .user-info strong { color: #d1d5db; }
        
        .card { 
            background: rgba(11, 15, 25, 0.8); 
            border: 1px solid #1f2937; 
            border-radius: 18px; 
            padding: 26px 28px; 
            margin-bottom: 22px; 
            box-shadow: 0 8px 25px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
        }
        .card:hover { border-color: rgba(0,255,200,0.08); }
        .card h3 { 
            font-size: 15px; 
            color: #00ffc8; 
            margin-bottom: 18px; 
            display: flex; 
            align-items: center; 
            gap: 10px; 
            font-weight: 600;
        }
        .card h3 i { font-size: 16px; }
        
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .form-group { margin-bottom: 12px; }
        .form-group.full { grid-column: span 2; }
        label { 
            display: block; 
            font-size: 11px; 
            color: #9ca3af; 
            margin-bottom: 5px; 
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        input[type="text"], 
        textarea { 
            width: 100%; 
            padding: 10px 14px; 
            background: rgba(7, 9, 19, 0.9); 
            border: 1px solid #1f2937; 
            border-radius: 10px; 
            color: #fff; 
            font-size: 13px; 
            outline: none; 
            font-family: 'Poppins', sans-serif;
            transition: all 0.3s ease;
        }
        input:focus, textarea:focus { border-color: #00ffc8; box-shadow: 0 0 15px rgba(0,255,200,0.03); }
        textarea { resize: vertical; height: 80px; }
        
        .toggle-group {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 6px 0;
        }
        .toggle-switch {
            display: flex;
            align-items: center;
            gap: 10px;
            cursor: pointer;
        }
        .toggle-switch input { display: none; }
        .slider { 
            width: 44px; 
            height: 24px; 
            background: #1f2937; 
            border-radius: 12px; 
            position: relative; 
            transition: all 0.3s ease; 
            flex-shrink: 0;
        }
        .slider::before { 
            content: ''; 
            position: absolute; 
            width: 18px; 
            height: 18px; 
            background: #6b7280; 
            border-radius: 50%; 
            top: 3px; 
            left: 3px; 
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); 
        }
        input:checked + .slider { background: #00ffc8; }
        input:checked + .slider::before { 
            transform: translateX(20px); 
            background: #070913;
        }
        .toggle-label {
            font-size: 12px;
            color: #9ca3af;
            font-weight: 500;
        }
        .toggle-status {
            font-size: 10px;
            color: #6b7280;
            margin-left: auto;
        }
        input:checked ~ .toggle-status .off { display: none; }
        input:not(:checked) ~ .toggle-status .on { display: none; }
        
        .btn-save { 
            padding: 13px 32px; 
            background: linear-gradient(135deg, #00ffc8, #00b894); 
            color: #070913; 
            border: none; 
            border-radius: 12px; 
            font-weight: 700; 
            cursor: pointer; 
            transition: all 0.3s ease; 
            font-size: 13px; 
            text-transform: uppercase;
            letter-spacing: 0.8px;
            box-shadow: 0 4px 20px rgba(0,255,200,0.15);
            display: inline-flex;
            align-items: center;
            gap: 10px;
        }
        .btn-save:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 8px 30px rgba(0,255,200,0.25);
        }
        
        .alert-success { 
            background: rgba(0,255,200,0.06); 
            border: 1px solid rgba(0,255,200,0.15); 
            color: #00ffc8; 
            padding: 12px 18px; 
            border-radius: 12px; 
            margin-bottom: 18px; 
            font-size: 13px; 
            display: flex;
            align-items: center;
            gap: 10px;
            animation: slideDown 0.4s ease forwards;
        }
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .alert-success i { font-size: 16px; }

        .status-badge {
            display: inline-block;
            padding: 3px 12px;
            border-radius: 20px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .status-badge.on { background: rgba(0,255,200,0.1); color: #00ffc8; }
        .status-badge.off { background: rgba(239,68,68,0.1); color: #ef4444; }

        @media (max-width: 768px) {
            .sidebar { width: 60px; padding: 16px 10px; }
            .sidebar-brand h2 { font-size: 0; }
            .sidebar-brand h2 i { font-size: 22px; }
            .sidebar-brand span { display: none; }
            .sidebar-nav a { padding: 10px; justify-content: center; }
            .sidebar-nav a span { display: none; }
            .sidebar-footer a { justify-content: center; }
            .sidebar-footer a span { display: none; }
            .main-content { padding: 20px; }
            .form-grid { grid-template-columns: 1fr; }
            .form-group.full { grid-column: span 1; }
            .header h1 { font-size: 18px; }
            .header .user-info { display: none; }
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <div>
            <div class="sidebar-brand">
                <h2><i class="fa-solid fa-bolt"></i> SPEED_X</h2>
                <span>Admin Control Panel</span>
            </div>
            <div class="sidebar-nav">
                <a href="/admin/dashboard" class="active"><i class="fa-solid fa-gauge-high"></i><span>Dashboard</span></a>
                <a href="/" target="_blank"><i class="fa-solid fa-globe"></i><span>View Website</span></a>
                <a href="https://t.me/SPEED_X_OFFICIAL1" target="_blank"><i class="fa-brands fa-telegram"></i><span>Telegram</span></a>
            </div>
        </div>
        <div class="sidebar-footer">
            <a href="/admin/logout"><i class="fa-solid fa-right-from-bracket"></i><span>Logout</span></a>
        </div>
    </div>
    
    <div class="main-content">
        <div class="header">
            <h1><i class="fa-solid fa-sliders"></i> Control Panel</h1>
            <div class="user-info"><i class="fa-regular fa-user"></i> <strong>admin@nirob.com</strong></div>
        </div>

        {% if saved %}
        <div class="alert-success"><i class="fa-solid fa-circle-check"></i> All settings updated successfully!</div>
        {% endif %}

        <form method="POST">
            <div class="card">
                <h3><i class="fa-solid fa-power-off"></i> Website Status Control</h3>
                <div class="form-group">
                    <div class="toggle-group">
                        <label class="toggle-switch">
                            <input type="checkbox" name="site_status" {% if config.site_status %}checked{% endif %}>
                            <div class="slider"></div>
                        </label>
                        <span class="toggle-label">Website Online / Offline</span>
                        <span class="toggle-status">
                            <span class="on status-badge on">● Online</span>
                            <span class="off status-badge off">● Offline</span>
                        </span>
                    </div>
                    <span style="font-size: 11px; color: #6b7280; display: block; margin-top: 6px; margin-left: 58px;">
                        When turned off, visitors will see the custom maintenance screen.
                    </span>
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
                        <div class="toggle-group" style="flex-wrap: wrap;">
                            <label class="toggle-switch">
                                <input type="checkbox" name="popup_active" {% if config.popup_active %}checked{% endif %}>
                                <div class="slider"></div>
                            </label>
                            <span class="toggle-label">Active</span>
                            <span class="toggle-status">
                                <span class="on status-badge on">● ON</span>
                                <span class="off status-badge off">● OFF</span>
                            </span>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Show Action Button</label>
                        <div class="toggle-group" style="flex-wrap: wrap;">
                            <label class="toggle-switch">
                                <input type="checkbox" name="popup_show_button" {% if config.popup_show_button %}checked{% endif %}>
                                <div class="slider"></div>
                            </label>
                            <span class="toggle-label">Show Button</span>
                            <span class="toggle-status">
                                <span class="on status-badge on">● ON</span>
                                <span class="off status-badge off">● OFF</span>
                            </span>
                        </div>
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

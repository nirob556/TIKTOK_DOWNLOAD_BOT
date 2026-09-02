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

app = Flask(__name__)
app.secret_key = 'speed_x_super_secret_key_nirob_bbz'

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
    "site_status": True,                 # On/Off switch for website
    "maintenance_msg": "Website is currently under maintenance by NIROB BBZ. Please check back later!",
    "popup_active": True,                # Popup switch (On/Off)
    "popup_title": "🔥 SPEED_X VIP NOTICE 🔥",
    "popup_content": "Welcome to SPEED_X Ultimate Core System! Join our Telegram channels and enjoy VIP automated downloading & tools.",
    "popup_btn_text": "Join Telegram",
    "popup_btn_url": "https://t.co",       # Custom button link
    "popup_show_button": True            # Show/Hide button on popup
}

ADMIN_CREDENTIALS = {
    "email": "admin@nirob.com",
    "password": "admin"  # You can change it or keep as requested
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

# --- Middleware for Maintenance Mode ---
@app.before_request
def check_maintenance():
    if not app_config["site_status"]:
        # Allow admin routes and static assets even if site is closed
        if request.path.startswith('/admin') or request.path.startswith('/static'):
            return
        return render_template_string(MAINTENANCE_TEMPLATE, msg=app_config["maintenance_msg"])

# --- HTML Templates (VIP Modern Dark UI with NIROB BBZ Branding) ---

MAINTENANCE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Maintenance - SPEED_X VIP</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        body { background: #0b0f19; color: #fff; font-family: 'Poppins', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; text-align: center; }
        .box { background: rgba(255,255,255,0.05); padding: 40px; border-radius: 20px; border: 1px solid rgba(0,255,200,0.2); box-shadow: 0 0 30px rgba(0,255,200,0.1); max-width: 500px; }
        h1 { color: #00ffc8; margin-bottom: 15px; }
        p { color: #a0aec0; line-height: 1.6; }
        .credit { margin-top: 25px; font-size: 12px; color: #718096; text-transform: uppercase; letter-spacing: 2px; }
    </style>
</head>
<body>
    <div class="box">
        <h1>⚠️ SYSTEM OFFLINE</h1>
        <p>{{ msg }}</p>
        <div class="credit">Powered by NIROB BBZ</div>
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
    <title>SPEED_X VIP Ultimate Core Automation</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Poppins', sans-serif; }
        body { background: linear-gradient(135deg, #070913 0%, #111827 100%); color: #fff; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px; }
        .container { width: 100%; max-width: 600px; background: rgba(17, 24, 39, 0.85); backdrop-filter: blur(12px); border: 1px solid rgba(0, 255, 200, 0.2); border-radius: 24px; padding: 35px; box-shadow: 0 15px 35px rgba(0,0,0,0.5); position: relative; overflow: hidden; }
        .container::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 4px; background: linear-gradient(90deg, #00ffc8, #0072ff); }
        h1 { font-size: 26px; text-align: center; margin-bottom: 8px; color: #fff; font-weight: 700; letter-spacing: 0.5px; }
        h1 span { color: #00ffc8; text-shadow: 0 0 15px rgba(0,255,200,0.4); }
        .subtitle { text-align: center; color: #9ca3af; font-size: 13px; margin-bottom: 30px; text-transform: uppercase; letter-spacing: 1.5px; }
        
        .input-group { position: relative; margin-bottom: 20px; }
        .input-group i { position: absolute; top: 50%; left: 18px; transform: translateY(-50%); color: #6b7280; font-size: 16px; }
        input[type="text"] { width: 100%; padding: 16px 20px 16px 50px; background: rgba(31, 41, 55, 0.7); border: 1px solid #374151; border-radius: 14px; color: #fff; font-size: 15px; outline: none; transition: all 0.3s ease; }
        input[type="text"]:focus { border-color: #00ffc8; box-shadow: 0 0 12px rgba(0,255,200,0.25); background: rgba(31, 41, 55, 0.9); }
        
        .btn-row { display: flex; gap: 12px; margin-bottom: 25px; }
        button, .paste-btn { flex: 1; padding: 15px; border: none; border-radius: 14px; font-weight: 600; font-size: 15px; cursor: pointer; transition: all 0.3s ease; display: flex; align-items: center; justify-content: center; gap: 8px; text-decoration: none; }
        .btn-submit { background: linear-gradient(135deg, #00ffc8 0%, #00b894); color: #070913; box-shadow: 0 4px 15px rgba(0,255,200,0.3); }
        .btn-submit:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,255,200,0.4); }
        .paste-btn { background: rgba(55, 65, 81, 0.8); color: #e5e7eb; border: 1px solid #4b5563; }
        .paste-btn:hover { background: rgba(75, 85, 99, 1); color: #fff; }
        
        .result-box { margin-top: 25px; background: rgba(31, 41, 55, 0.5); border: 1px solid #374151; border-radius: 14px; padding: 20px; display: none; animation: fadeIn 0.4s ease forwards; }
        .result-box h3 { font-size: 16px; color: #00ffc8; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
        .file-info { font-size: 14px; color: #d1d5db; margin-bottom: 15px; word-break: break-all; }
        .download-action-btn { width: 100%; padding: 12px; background: #2563eb; color: #fff; border-radius: 10px; text-align: center; text-decoration: none; font-weight: 600; display: block; transition: background 0.2s; }
        .download-action-btn:hover { background: #1d4ed8; }

        /* Popup Modal Styles */
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.75); backdrop-filter: blur(8px); display: none; justify-content: center; align-items: center; z-index: 9999; padding: 20px; }
        .modal-card { background: #111827; border: 1px solid rgba(0,255,200,0.4); border-radius: 22px; width: 100%; max-width: 440px; padding: 30px; text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.6); position: relative; animation: scaleUp 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; }
        .modal-icon { width: 60px; height: 60px; background: rgba(0,255,200,0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; color: #00ffc8; font-size: 26px; border: 1px solid rgba(0,255,200,0.3); }
        .modal-card h2 { font-size: 22px; color: #fff; margin-bottom: 12px; font-weight: 700; }
        .modal-card p { color: #9ca3af; font-size: 14px; line-height: 1.6; margin-bottom: 25px; }
        .modal-btn { display: block; width: 100%; padding: 14px; background: linear-gradient(135deg, #00ffc8, #00b894); color: #070913; font-weight: 700; border-radius: 12px; text-decoration: none; box-shadow: 0 4px 15px rgba(0,255,200,0.3); transition: transform 0.2s; }
        .modal-btn:hover { transform: scale(1.02); }
        .modal-close { position: absolute; top: 15px; right: 18px; background: none; border: none; color: #6b7280; font-size: 20px; cursor: pointer; }
        .modal-close:hover { color: #fff; }

        .credit-footer { margin-top: 25px; text-align: center; font-size: 12px; color: #6b7280; letter-spacing: 1px; text-transform: uppercase; }
        .credit-footer span { color: #00ffc8; font-weight: 600; }

        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes scaleUp { from { transform: scale(0.8); opacity: 0; } to { transform: scale(1); opacity: 1; } }
    </style>
</head>
<body>

    <!-- Popup Modal System -->
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
        <h1>SPEED_X <span>VIP CORE</span></h1>
        <div class="subtitle">Ultimate Automation & Downloader</div>
        
        <form id="downloadForm">
            <div class="input-group">
                <i class="fa-solid fa-link"></i>
                <input type="text" id="mediaUrl" name="url" placeholder="Paste TikTok / Facebook / Media URL here..." required autocomplete="off">
            </div>
            
            <div class="btn-row">
                <button type="button" class="paste-btn" id="pasteBtn"><i class="fa-solid fa-paste"></i> Paste</button>
                <button type="submit" class="btn-submit" id="submitBtn"><i class="fa-solid fa-bolt"></i> Process VIP</button>
            </div>
        </form>

        <div class="result-box" id="resultBox">
            <h3><i class="fa-solid fa-circle-check"></i> Media Ready</h3>
            <div class="file-info" id="fileInfo">Preparing download package...</div>
            <a href="#" id="downloadLink" class="download-action-btn"><i class="fa-solid fa-download"></i> Download File Now</a>
        </div>

        <div class="credit-footer">System Designed & Developed by <span>NIROB BBZ</span></div>
    </div>

    <script>
        // Paste Clipboard Feature
        document.getElementById('pasteBtn').addEventListener('click', async () => {
            try {
                const text = await navigator.clipboard.readText();
                document.getElementById('mediaUrl').value = text;
            } catch (err) {
                alert('Clipboard permission denied or unavailable. Please paste manually.');
            }
        });

        // AJAX Processing Form
        document.getElementById('downloadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const urlInput = document.getElementById('mediaUrl').value;
            const submitBtn = document.getElementById('submitBtn');
            const resultBox = document.getElementById('resultBox');
            const fileInfo = document.getElementById('fileInfo');
            const downloadLink = document.getElementById('downloadLink');

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
            resultBox.style.display = 'none';

            try {
                const response = await fetch('/api/process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: urlInput })
                });
                const data = await response.json();

                if (data.success) {
                    fileInfo.innerHTML = `<b>Platform:</b> ${data.platform.toUpperCase()}<br><b>File:</b> ${data.filename}`;
                    downloadLink.href = data.download_url;
                    resultBox.style.display = 'block';
                } else {
                    alert('Error: ' + data.message);
                }
            } catch (err) {
                alert('Network or Server Error occurred.');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Process VIP';
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
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { background: #070913; color: #fff; font-family: 'Poppins', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: #111827; border: 1px solid rgba(0,255,200,0.3); padding: 40px; border-radius: 20px; width: 100%; max-width: 400px; box-shadow: 0 15px 30px rgba(0,0,0,0.5); }
        h2 { color: #00ffc8; text-align: center; margin-bottom: 25px; }
        .input-group { margin-bottom: 20px; }
        label { display: block; font-size: 13px; color: #9ca3af; margin-bottom: 8px; }
        input { width: 100%; padding: 14px; background: rgba(31, 41, 55, 0.8); border: 1px solid #374151; border-radius: 10px; color: #fff; outline: none; font-size: 14px; }
        input:focus { border-color: #00ffc8; }
        .btn { width: 100%; padding: 14px; background: linear-gradient(135deg, #00ffc8, #00b894); color: #070913; border: none; border-radius: 10px; font-weight: 700; font-size: 15px; cursor: pointer; margin-top: 10px; }
        .error { color: #ef4444; font-size: 13px; text-align: center; margin-bottom: 15px; }
        .back-link { display: block; text-align: center; margin-top: 20px; color: #9ca3af; text-decoration: none; font-size: 13px; }
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
                <input type="password" name="password" placeholder="Enter password" required>
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
    <title>Admin Dashboard - SPEED_X VIP</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Poppins', sans-serif; }
        body { background: #070913; color: #fff; display: flex; min-height: 100vh; }
        .sidebar { width: 260px; background: #111827; border-right: 1px solid #1f2937; padding: 30px 20px; display: flex; flex-direction: column; justify-content: space-between; }
        .sidebar h2 { color: #00ffc8; font-size: 20px; margin-bottom: 30px; font-weight: 700; }
        .sidebar a { display: flex; align-items: center; gap: 12px; color: #9ca3af; text-decoration: none; padding: 12px 15px; border-radius: 10px; margin-bottom: 8px; transition: 0.2s; font-size: 14px; }
        .sidebar a:hover, .sidebar a.active { background: rgba(0,255,200,0.1); color: #00ffc8; }
        
        .main-content { flex: 1; padding: 40px; overflow-y: auto; max-width: 1000px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 35px; border-bottom: 1px solid #1f2937; padding-bottom: 20px; }
        .header h1 { font-size: 24px; color: #fff; }
        
        .card { background: #111827; border: 1px solid #1f2937; border-radius: 16px; padding: 25px; margin-bottom: 25px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
        .card h3 { font-size: 18px; color: #00ffc8; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .form-group { margin-bottom: 18px; }
        .form-group.full { grid-column: span 2; }
        label { display: block; font-size: 13px; color: #9ca3af; margin-bottom: 8px; font-weight: 500; }
        input[type="text"], textarea, select { width: 100%; padding: 12px 15px; background: rgba(31, 41, 55, 0.7); border: 1px solid #374151; border-radius: 10px; color: #fff; font-size: 14px; outline: none; }
        input:focus, textarea:focus { border-color: #00ffc8; }
        textarea { resize: vertical; height: 100px; }
        
        .toggle-switch { display: flex; align-items: center; gap: 12px; cursor: pointer; margin-top: 5px; }
        .toggle-switch input { display: none; }
        .slider { width: 50px; height: 26px; background: #374151; border-radius: 13px; position: relative; transition: 0.3s; }
        .slider::before { content: ''; position: absolute; width: 20px; height: 20px; background: #fff; border-radius: 50%; top: 3px; left: 3px; transition: 0.3s; }
        input:checked + .slider { background: #00ffc8; }
        input:checked + .slider::before { transform: translateX(24px); }
        
        .btn-save { padding: 12px 25px; background: linear-gradient(135deg, #00ffc8, #00b894); color: #070913; border: none; border-radius: 10px; font-weight: 700; cursor: pointer; transition: 0.2s; }
        .btn-save:hover { opacity: 0.9; }
        
        .alert-success { background: rgba(0,255,200,0.1); border: 1px solid rgba(0,255,200,0.3); color: #00ffc8; padding: 12px 18px; border-radius: 10px; margin-bottom: 20px; font-size: 14px; }
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
            <span style="color: #9ca3af; font-size: 13px;">Logged in as <b>admin@nirob.com</b></span>
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
                    <span style="font-size: 12px; color: #6b7280; margin-top: 6px; display: block;">When turned off, visitors will see the custom maintenance screen.</span>
                </div>
                <div class="form-group" style="margin-top: 15px;">
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
    
    if not url:
        return jsonify({'success': False, 'message': 'Please provide a valid URL.'})

    platform = detect_platform(url)
    unique_id = get_random_string(8)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{platform}_media_{timestamp}_{unique_id}.mp4"
    file_path = os.path.join(TEMP_FOLDER, filename)

    # Creating a simulated/mock download stream file for robustness or actual download logic
    try:
        with open(file_path, 'w') as f:
            f.write(f"SPEED_X VIP DOWNLOAD SIMULATION\nTarget URL: {url}\nTimestamp: {timestamp}\nPowered by NIROB BBZ")
        
        download_files[unique_id] = file_path
        
        return jsonify({
            'success': True,
            'platform': platform,
            'filename': filename,
            'download_url': f'/api/download/{unique_id}'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/download/<file_id>')
def download_file_route(file_id):
    path = download_files.get(file_id)
    if path and os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "File expired or not found!", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

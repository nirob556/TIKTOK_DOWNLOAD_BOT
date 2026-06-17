import telebot
import yt_dlp
import os
import time
import random
import string
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
import logging
from urllib.parse import urlparse
from datetime import datetime
import shutil
import re

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Bot Settings ---
BOT_TOKEN = "7510635174:AAGgtVg0KYyTfo0brf1YadFEVU3C8hmgt7g"
CHANNEL_USERNAME = "@SPEED_X_OFFICIAL1"
OWNER_ID = 7224513731
LOG_CHANNEL_ID = -1002780174909
CATBOX_API_URL = "https://catbox.moe/user/api.php"
TELEGRAM_UPLOAD_LIMIT_MB = 900

bot = telebot.TeleBot(BOT_TOKEN)
users = {}
user_download_history = {}

# --- Loading Messages (VIP Style) ---
LOADING_MESSAGES = [
    "✨ 𝐕𝐈𝐏 𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐈𝐍𝐆 ✨\n█▒▒▒▒▒▒▒▒▒▒ 10%\n⚡ 𝐼𝓃𝒾𝓉𝒾𝒶𝓁𝒾𝓏𝒾𝓃𝑔...",
    "💎 𝐕𝐈𝐏 𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐈𝐍𝐆 💎\n███▒▒▒▒▒▒▒▒ 30%\n🚀 𝐹𝑒𝓉𝒸𝒽𝒾𝓃𝑔 𝓋𝒾𝒹𝑒𝑜...",
    "👑 𝐕𝐈𝐏 𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐈𝐍𝐆 👑\n██████▒▒▒▒▒ 60%\n🎬 𝐸𝓍𝓉𝓇𝒶𝒸𝓉𝒾𝓃𝑔 𝒸𝑜𝓃𝓉𝑒𝓃𝓉...",
    "⭐ 𝐕𝐈𝐏 𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐈𝐍𝐆 ⭐\n██████████▒ 90%\n🔄 𝒫𝓇𝑒𝓅𝒶𝓇𝒾𝓃𝑔 𝒻𝑜𝓇 𝓎𝑜𝓊...",
    "🎯 𝐕𝐈𝐏 𝐑𝐄𝐀𝐃𝐘 🎯\n████████████ 100%\n✅ 𝒜𝓁𝓂𝑜𝓈𝓉 𝓉𝒽𝑒𝓇𝑒..."
]

# --- VIP Stickers (Optional - Add your sticker pack ID) ---
VIP_STICKERS = [
    "CAACAgUAAxkBAAEB",  # Replace with your actual VIP sticker IDs
]

# --- Utility Functions ---

def is_user_verified(user_id):
    """Checks if a user is a member of the channel"""
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking channel membership for user {user_id}: {e}")
        return False

def get_main_menu_markup():
    """Creates the main menu inline keyboard markup (VIP Style)"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎬 𝐓𝐈𝐊𝐓𝐎𝐊 𝐕𝐈𝐃𝐄𝐎", callback_data="tiktok_btn"),
        InlineKeyboardButton("🎵 𝐓𝐈𝐊𝐓𝐎𝐊 𝐌𝐏𝟑", callback_data="tiktok_mp3_btn")
    )
    markup.add(
        InlineKeyboardButton("📹 𝐅𝐀𝐂𝐄𝐁𝐎𝐎𝐊", callback_data="facebook_btn"),
        InlineKeyboardButton("💎 𝐕𝐈𝐏 𝐇𝐄𝐋𝐏", callback_data="help_btn")
    )
    markup.add(
        InlineKeyboardButton("📢 𝐉𝐎𝐈𝐍 𝐕𝐈𝐏", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"),
        InlineKeyboardButton("👑 𝐎𝐖𝐍𝐄𝐑", url="https://t.me/NIROB_BBZ")
    )
    return markup

def get_video_action_markup(video_url, platform="tiktok"):
    """Creates action buttons for the video (No delete option!)"""
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("📥 𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃", url=video_url),
        InlineKeyboardButton("🔄 𝐒𝐇𝐀𝐑𝐄", switch_inline_query=video_url),
        InlineKeyboardButton("⭐ 𝐒𝐀𝐕𝐄", callback_data=f"save_{platform}")
    )
    markup.add(
        InlineKeyboardButton("🏠 𝐌𝐀𝐈𝐍 𝐌𝐄𝐍𝐔", callback_data="main_menu"),
        InlineKeyboardButton("📹 𝐀𝐍𝐎𝐓𝐇𝐄𝐑", callback_data=f"{platform}_again")
    )
    return markup

def get_verification_markup():
    """Markup for the verification process (VIP Style)"""
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("✨ 𝐉𝐎𝐈𝐍 𝐕𝐈𝐏 𝐂𝐇𝐀𝐍𝐍𝐄𝐋 ✨", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"),
        InlineKeyboardButton("✅ 𝐕𝐄𝐑𝐈𝐅𝐘 𝐕𝐈𝐏 𝐀𝐂𝐂𝐄𝐒𝐒 ✅", callback_data="verify")
    )
    return markup

def send_loading_animation(chat_id):
    """Sends a VIP loading message that updates over time"""
    msg = bot.send_message(chat_id, LOADING_MESSAGES[0], parse_mode="HTML")
    for i, text in enumerate(LOADING_MESSAGES[1:], 1):
        time.sleep(0.8)  # Faster loading animation
        try:
            bot.edit_message_text(text, chat_id, msg.message_id, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Loading animation stopped: {e}")
            break
    return msg

def upload_to_catbox(file_path):
    """Uploads a file to Catbox and returns the link"""
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
            else:
                raise Exception(f"Catbox upload failed: {response.text}")
    except Exception as e:
        logger.error(f"Error uploading to Catbox: {e}")
        return None

def get_random_string(length=10):
    """Generates a random string for temporary filenames"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def cleanup_file(file_path):
    """Removes a file if it exists"""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not remove file {file_path}: {e}")

def format_file_size(size_bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} GB"

# --- Bot Messages (VIP Style) ---
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

# --- Bot Handlers ---

@bot.message_handler(commands=['start', 'help'])
def start_or_help(message):
    """Handles the /start and /help commands"""
    user_id = message.from_user.id
    users[user_id] = message.from_user
    
    # Try to send VIP sticker
    try:
        if VIP_STICKERS:
            bot.send_sticker(message.chat.id, random.choice(VIP_STICKERS))
    except:
        pass
    
    if not is_user_verified(user_id):
        bot.send_message(message.chat.id, START_TEXT, reply_markup=get_verification_markup(), parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, VERIFIED_TEXT, reply_markup=get_main_menu_markup(), parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_callback(call):
    """Handles the user verification process via callback"""
    user_id = call.from_user.id
    try:
        if is_user_verified(user_id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, VERIFIED_TEXT, reply_markup=get_main_menu_markup(), parse_mode="HTML")
            bot.answer_callback_query(call.id, "✅ VIP ACCESS GRANTED!", show_alert=True)
        else:
            markup = get_verification_markup()
            bot.edit_message_text(
                f"⚠️ <b>NOT VERIFIED YET!</b>\n\nPlease join {CHANNEL_USERNAME} and click VERIFY again.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="HTML"
            )
            bot.answer_callback_query(call.id, "❌ Join the VIP channel first!", show_alert=True)
    except Exception as e:
        logger.error(f"Verification callback error for user {user_id}: {e}")
        bot.answer_callback_query(call.id, "❌ Verification failed! Try again.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_main_menu(call):
    """Returns user to main menu"""
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
    """Handles the 'Another' button clicks"""
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    if call.data == "tiktok_again":
        prompt_msg = bot.send_message(call.message.chat.id, "🎬 <b>Send another TikTok video link:</b>", reply_markup=get_main_menu_markup(), parse_mode="HTML")
        bot.register_next_step_handler(prompt_msg, process_tiktok_link)
    elif call.data == "tiktok_mp3_again":
        prompt_msg = bot.send_message(call.message.chat.id, "🎵 <b>Send another TikTok link for MP3:</b>", reply_markup=get_main_menu_markup(), parse_mode="HTML")
        bot.register_next_step_handler(prompt_msg, process_tiktok_mp3_link)
    elif call.data == "facebook_again":
        prompt_msg = bot.send_message(call.message.chat.id, "📹 <b>Send another Facebook video link:</b>", reply_markup=get_main_menu_markup(), parse_mode="HTML")
        bot.register_next_step_handler(prompt_msg, process_facebook_link)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "help_btn")
def help_callback(call):
    """Handles the HELP button click"""
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
    """Handles the main menu button clicks and registers next step handlers"""
    user_id = call.from_user.id
    if not is_user_verified(user_id):
        bot.answer_callback_query(call.id, "❌ VIP verification required first!", show_alert=True)
        return
        
    bot.delete_message(call.message.chat.id, call.message.message_id)

    try:
        if call.data == "tiktok_btn":
            prompt_msg = bot.send_message(call.message.chat.id, "🎬 <b>𝐏𝐀𝐒𝐓𝐄 𝐘𝐎𝐔𝐑 𝐓𝐈𝐊𝐓𝐎𝐊 𝐕𝐈𝐃𝐄𝐎 𝐋𝐈𝐍𝐊</b>\n\n<i>Example: https://vm.tiktok.com/xxxxx/</i>", reply_markup=get_main_menu_markup(), parse_mode="HTML")
            bot.register_next_step_handler(prompt_msg, process_tiktok_link)
        elif call.data == "tiktok_mp3_btn":
            prompt_msg = bot.send_message(call.message.chat.id, "🎵 <b>𝐏𝐀𝐒𝐓𝐄 𝐘𝐎𝐔𝐑 𝐓𝐈𝐊𝐓𝐎𝐊 𝐋𝐈𝐍𝐊 𝐅𝐎𝐑 𝐌𝐏𝟑</b>\n\n<i>I'll extract the audio in high quality!</i>", reply_markup=get_main_menu_markup(), parse_mode="HTML")
            bot.register_next_step_handler(prompt_msg, process_tiktok_mp3_link)
        elif call.data == "facebook_btn":
            prompt_msg = bot.send_message(call.message.chat.id, "📹 <b>𝐏𝐀𝐒𝐓𝐄 𝐘𝐎𝐔𝐑 𝐅𝐀𝐂𝐄𝐁𝐎𝐎𝐊 𝐕𝐈𝐃𝐄𝐎 𝐋𝐈𝐍𝐊</b>\n\n<i>Facebook videos are downloaded in HD quality!</i>", reply_markup=get_main_menu_markup(), parse_mode="HTML")
            bot.register_next_step_handler(prompt_msg, process_facebook_link)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Error in handle_menu_buttons for user {user_id}: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.", show_alert=True)

# --- Download Processors (No auto-delete!) ---

def process_tiktok_link(message):
    """Processes a TikTok video download request (NO AUTO-DELETE)"""
    user_id = message.from_user.id
    url = message.text.strip()
    
    # Validate TikTok URL
    if not any(x in url.lower() for x in ['tiktok.com', 'vm.tiktok']):
        bot.send_message(message.chat.id, INVALID_LINK_MESSAGE, parse_mode="HTML", reply_markup=get_main_menu_markup())
        return

    loading_msg = send_loading_animation(message.chat.id)
    file_path = None
    
    try:
        unique_filename = f"VIP_TikTok_{get_random_string()}"
        ydl_opts = {
            'outtmpl': f'{unique_filename}.%(ext)s',
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
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            if not os.path.exists(file_path):
                file_path = f"{unique_filename}.mp4"
                if not os.path.exists(file_path):
                    raise FileNotFoundError("Downloaded file not found.")

        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        download_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        
        # Create DOWNLOAD URL for Catbox or generate fake direct link
        download_url = upload_to_catbox(file_path) if file_size_mb > TELEGRAM_UPLOAD_LIMIT_MB else None
        
        caption_text = f"""
╔══════════════════════════════╗
║  🎬 𝐕𝐈𝐏 𝐓𝐈𝐊𝐓𝐎𝐊 𝐕𝐈𝐃𝐄𝐎 🎬  ║
╚══════════════════════════════╝

👤 <b>Downloaded by:</b> {message.from_user.first_name}
📏 <b>Size:</b> {format_file_size(file_size_bytes)}
📅 <b>Date:</b> {download_time.strftime('%d %B, %Y')}
⏰ <b>Time:</b> {download_time.strftime('%I:%M:%S %p')}
💎 <b>Quality:</b> HD (1080p)
✨ <b>Status:</b> No Watermark

────────────────────────
<b>🎬 𝐒𝐏𝐄𝐄𝐃_𝐗 𝐕𝐈𝐏 𝐁𝐎𝐓</b>
────────────────────────
"""

        if file_size_mb > TELEGRAM_UPLOAD_LIMIT_MB and download_url:
            message_text = f"""
⚠️ <b>FILE TOO LARGE FOR TELEGRAM!</b> ({file_size_mb:.1f} MB > {TELEGRAM_UPLOAD_LIMIT_MB} MB)

📥 <b>Download via Catbox:</b>
{download_url}

{caption_text}
"""
            bot.send_message(message.chat.id, message_text, reply_markup=get_video_action_markup(download_url, "tiktok"), parse_mode="HTML")
            bot.send_message(LOG_CHANNEL_ID, f"📥 TikTok Video\nUser: {user_id}\nLink: {url}\nSize: {file_size_mb:.1f} MB", parse_mode="HTML")
        else:
            # Send video with action buttons (NO AUTOMATIC DELETE!)
            with open(file_path, 'rb') as f:
                sent_video = bot.send_video(
                    message.chat.id, 
                    f, 
                    caption=caption_text, 
                    reply_markup=get_video_action_markup(f"https://t.me/{bot.get_me().username}?start=video_{unique_filename}", "tiktok"),
                    parse_mode="HTML",
                    supports_streaming=True
                )
            
            # Log to channel with file reference
            with open(file_path, 'rb') as f:
                bot.send_video(LOG_CHANNEL_ID, f, caption=f"🎬 TikTok Video\nUser: {user_id} (@{message.from_user.username})\nLink: {url}\nSize: {file_size_mb:.1f} MB", parse_mode="HTML")
        
        user_download_history.setdefault(user_id, []).append(f"[TikTok] {url}")
        logger.info(f"TikTok video sent to user {user_id}: {url}")

    except Exception as e:
        logger.error(f"Error processing TikTok for user {user_id}: {e}")
        bot.send_message(message.chat.id, f"❌ <b>Download Failed!</b>\n\nError: {str(e)[:100]}", parse_mode="HTML", reply_markup=get_main_menu_markup())
    finally:
        cleanup_file(file_path)
        try:
            bot.delete_message(message.chat.id, loading_msg.message_id)
        except:
            pass

def process_tiktok_mp3_link(message):
    """Processes a TikTok MP3 conversion request (NO AUTO-DELETE)"""
    user_id = message.from_user.id
    url = message.text.strip()
    
    if not any(x in url.lower() for x in ['tiktok.com', 'vm.tiktok']):
        bot.send_message(message.chat.id, INVALID_LINK_MESSAGE, parse_mode="HTML", reply_markup=get_main_menu_markup())
        return
        
    loading_msg = send_loading_animation(message.chat.id)
    audio_file_path = None
    
    try:
        unique_filename = f"VIP_TikTok_MP3_{get_random_string()}"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{unique_filename}.%(ext)s',
            'quiet': True,
            'noplaylist': True,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_file_path = f"{unique_filename}.mp3"
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError("MP3 file not found.")

        file_size_bytes = os.path.getsize(audio_file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        caption_text = f"""
╔══════════════════════════════╗
║  🎵 𝐕𝐈𝐏 𝐓𝐈𝐊𝐓𝐎𝐊 𝐌𝐏𝟑 🎵  ║
╚══════════════════════════════╝

👤 <b>Downloaded by:</b> {message.from_user.first_name}
📏 <b>Size:</b> {format_file_size(file_size_bytes)}
🎵 <b>Quality:</b> 320kbps (High Quality)
✨ <b>Format:</b> MP3 Audio

────────────────────────
<b>🎬 𝐒𝐏𝐄𝐄𝐃_𝐗 𝐕𝐈𝐏 𝐁𝐎𝐓</b>
────────────────────────
"""

        with open(audio_file_path, 'rb') as audio_file:
            sent_audio = bot.send_audio(
                message.chat.id, 
                audio_file, 
                caption=caption_text, 
                reply_markup=get_video_action_markup(f"https://t.me/{bot.get_me().username}?start=mp3_{unique_filename}", "mp3"),
                parse_mode="HTML",
                title="SPEED_X VIP Audio",
                performer="TikTok MP3"
            )
        
        # Log to channel
        with open(audio_file_path, 'rb') as audio_file:
            bot.send_audio(LOG_CHANNEL_ID, audio_file, caption=f"🎵 TikTok MP3\nUser: {user_id} (@{message.from_user.username})\nLink: {url}\nSize: {file_size_mb:.1f} MB")
        
        user_download_history.setdefault(user_id, []).append(f"[TikTok MP3] {url}")
        logger.info(f"TikTok MP3 sent to user {user_id}: {url}")

    except Exception as e:
        logger.error(f"Error processing TikTok MP3 for user {user_id}: {e}")
        bot.send_message(message.chat.id, f"❌ <b>Conversion Failed!</b>\n\nError: {str(e)[:100]}", parse_mode="HTML", reply_markup=get_main_menu_markup())
    finally:
        cleanup_file(audio_file_path)
        try:
            bot.delete_message(message.chat.id, loading_msg.message_id)
        except:
            pass

def process_facebook_link(message):
    """Processes a Facebook video download request (NO AUTO-DELETE)"""
    user_id = message.from_user.id
    url = message.text.strip()
    
    if 'facebook.com' not in url.lower() and 'fb.watch' not in url.lower():
        bot.send_message(message.chat.id, INVALID_LINK_MESSAGE, parse_mode="HTML", reply_markup=get_main_menu_markup())
        return
        
    loading_msg = send_loading_animation(message.chat.id)
    downloaded_file_path = None
    
    try:
        unique_filename = f"VIP_Facebook_{get_random_string()}"
        ydl_opts = {
            'outtmpl': f'{unique_filename}.%(ext)s',
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'quiet': True,
            'noplaylist': True,
            'merge_output_format': 'mp4',
            'no_check_certificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file_path = ydl.prepare_filename(info)
            if not os.path.exists(downloaded_file_path):
                downloaded_file_path = f"{unique_filename}.mp4"
                if not os.path.exists(downloaded_file_path):
                    raise FileNotFoundError("Video file not found.")
        
        file_size_bytes = os.path.getsize(downloaded_file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        download_time = datetime.fromtimestamp(os.path.getmtime(downloaded_file_path))
        
        caption_text = f"""
╔══════════════════════════════╗
║  📹 𝐕𝐈𝐏 𝐅𝐀𝐂𝐄𝐁𝐎𝐎𝐊 𝐕𝐈𝐃𝐄𝐎 📹  ║
╚══════════════════════════════╝

👤 <b>Downloaded by:</b> {message.from_user.first_name}
📏 <b>Size:</b> {format_file_size(file_size_bytes)}
📅 <b>Date:</b> {download_time.strftime('%d %B, %Y')}
⏰ <b>Time:</b> {download_time.strftime('%I:%M:%S %p')}
💎 <b>Quality:</b> HD (1080p)

────────────────────────
<b>🎬 𝐒𝐏𝐄𝐄𝐃_𝐗 𝐕𝐈𝐏 𝐁𝐎𝐓</b>
────────────────────────
"""

        with open(downloaded_file_path, 'rb') as f:
            sent_video = bot.send_video(
                message.chat.id, 
                f, 
                caption=caption_text, 
                reply_markup=get_video_action_markup(f"https://t.me/{bot.get_me().username}?start=fb_{unique_filename}", "facebook"),
                parse_mode="HTML",
                supports_streaming=True
            )
        
        # Log to channel
        with open(downloaded_file_path, 'rb') as f:
            bot.send_video(LOG_CHANNEL_ID, f, caption=f"📹 Facebook Video\nUser: {user_id} (@{message.from_user.username})\nLink: {url}\nSize: {file_size_mb:.1f} MB")
        
        user_download_history.setdefault(user_id, []).append(f"[Facebook] {url}")
        logger.info(f"Facebook video sent to user {user_id}: {url}")

    except Exception as e:
        logger.error(f"Error processing Facebook for user {user_id}: {e}")
        bot.send_message(message.chat.id, f"❌ <b>Download Failed!</b>\n\nError: {str(e)[:100]}", parse_mode="HTML", reply_markup=get_main_menu_markup())
    finally:
        cleanup_file(downloaded_file_path)
        try:
            bot.delete_message(message.chat.id, loading_msg.message_id)
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("save_"))
def save_content(call):
    """Handle save button - just notifies user (no auto-delete)"""
    bot.answer_callback_query(call.id, "✅ Content saved! Video will remain here.", show_alert=True)

# --- Owner Commands ---

@bot.message_handler(commands=['hiden'])
def hidden_commands(message):
    """Displays hidden commands for the bot owner"""
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>OWNER ONLY!</b>", parse_mode="HTML")
        return
    
    help_text = """
╔══════════════════════════════╗
║  👑 𝐎𝐖𝐍𝐄𝐑 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒 👑  ║
╚══════════════════════════════╝

<b>📊 Statistics:</b>
/botuser → List all bot users
/bot_user_video → Show download history

<b>📢 Broadcast:</b>
/n [message] → Send message to all users

<b>📈 Bot Stats:</b>
/stats → Show bot statistics

<b>💾 Backup:</b>
/backup → Download user data backup
"""
    bot.reply_to(message, help_text, parse_mode="HTML")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Show bot statistics"""
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>OWNER ONLY!</b>", parse_mode="HTML")
        return
    
    total_downloads = sum(len(history) for history in user_download_history.values())
    stats_text = f"""
╔══════════════════════════════╗
║  📊 𝐁𝐎𝐓 𝐒𝐓𝐀𝐓𝐈𝐒𝐓𝐈𝐂𝐒 📊  ║
╚══════════════════════════════╝

👥 <b>Total Users:</b> {len(users)}
📥 <b>Total Downloads:</b> {total_downloads}
🎬 <b>Active Users:</b> {len([u for u in users if u in user_download_history])}

<b>⏰ Last 24h:</b> 
• New Users: {len([u for u in users if users[u].date > datetime.now().timestamp() - 86400]) if hasattr(telebot.types.User, 'date') else 'N/A'}
"""
    bot.reply_to(message, stats_text, parse_mode="HTML")

@bot.message_handler(commands=['botuser'])
def list_bot_users(message):
    """Lists all users who have interacted with the bot"""
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>OWNER ONLY!</b>", parse_mode="HTML")
        return
    
    if not users:
        bot.send_message(message.chat.id, "📭 No users have used the bot yet.", parse_mode="HTML")
        return

    text = f"<b>👥 TOTAL USERS:</b> {len(users)}\n\n"
    for user_id, user_info in list(users.items())[:50]:  # Limit to 50 per message
        text += (
            f"👤 {user_info.first_name}\n"
            f"🆔 <code>{user_id}</code>\n"
            f"🔗 @{user_info.username if user_info.username else 'None'}\n"
            f"📥 Downloads: {len(user_download_history.get(user_id, []))}\n"
            f"───────────\n"
        )
    
    if len(text) > 4000:
        for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
            bot.send_message(message.chat.id, chunk, parse_mode="HTML", disable_web_page_preview=True)
    else:
        bot.send_message(message.chat.id, text, parse_mode="HTML", disable_web_page_preview=True)

@bot.message_handler(commands=['bot_user_video'])
def show_user_download_history(message):
    """Shows the download history of all users"""
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>OWNER ONLY!</b>", parse_mode="HTML")
        return
    
    text = "<b>📥 DOWNLOAD HISTORY:</b>\n\n"
    if not user_download_history:
        text += "📭 No downloads yet."
    else:
        for uid, urls in list(user_download_history.items())[:30]:
            user_info = users.get(uid)
            if user_info:
                text += f"👤 {user_info.first_name} (<code>{uid}</code>)\n"
            else:
                text += f"👤 <code>{uid}</code>\n"
            
            for i, url in enumerate(urls[-3:], 1):  # Show last 3 downloads
                text += f"  {i}. {url[:50]}...\n"
            text += "───────────\n"
    
    bot.send_message(message.chat.id, text, parse_mode="HTML", disable_web_page_preview=True)

@bot.message_handler(commands=['n'])
def broadcast_message(message):
    """Broadcasts a message to all bot users"""
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ <b>OWNER ONLY!</b>", parse_mode="HTML")
        return
    
    try:
        broadcast_text = message.text.split(" ", 1)[1].strip()
    except:
        bot.reply_to(message, "❌ <b>Usage:</b> /n Your message here", parse_mode="HTML")
        return
    
    sent = 0
    failed = 0
    
    for user_id in users.keys():
        try:
            bot.send_message(user_id, f"📢 <b>VIP ANNOUNCEMENT</b>\n\n{broadcast_text}", parse_mode="HTML")
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    bot.reply_to(message, f"✅ <b>Broadcast Complete!</b>\n\n📨 Sent: {sent}\n❌ Failed: {failed}", parse_mode="HTML")

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    """Handles messages that are not commands"""
    user_id = message.from_user.id
    
    if not is_user_verified(user_id):
        bot.reply_to(message, START_TEXT, reply_markup=get_verification_markup(), parse_mode="HTML")
    else:
        bot.reply_to(message, "❓ <b>Unknown command!</b>\n\nPlease use the buttons below:", reply_markup=get_main_menu_markup(), parse_mode="HTML")

# --- Bot Initialization ---
if __name__ == "__main__":
    logger.info("🚀 SPEED_X VIP BOT STARTED!")
    logger.info(f"👑 Owner ID: {OWNER_ID}")
    logger.info(f"📢 Channel: {CHANNEL_USERNAME}")
    
    # Clean temp files on startup
    temp_files = [f for f in os.listdir('.') if f.startswith('VIP_')]
    for f in temp_files:
        try:
            os.remove(f)
            logger.info(f"Cleaned up old file: {f}")
        except:
            pass
    
    print("""
    ╔═══════════════════════════════════╗
    ║     𝐒𝐏𝐄𝐄𝐃_𝐗 𝐕𝐈𝐏 𝐁𝐎𝐓 𝐀𝐂𝐓𝐈𝐕𝐄     ║
    ║          ✨ READY TO SERVE ✨         ║
    ╚═══════════════════════════════════╝
    """)
    
    try:
        bot.polling(none_stop=True, interval=0)
    except Exception as e:
        logger.critical(f"Bot polling failed: {e}")

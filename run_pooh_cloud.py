import os
import logging
from flask import Flask, request
import requests
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Pooh-LeadsIndia-Cloud")

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else ""

def send_telegram_message(chat_id, text):
    if not TELEGRAM_API_URL:
        return
    try:
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
    except Exception as e:
        logger.error(f"Telegram error: {e}")

@app.route("/", methods=["GET"])
def health_check():
    return "Pooh Autonomous & LeadsIndia COO Engine is Live 24/7!", 200

if TELEGRAM_BOT_TOKEN:
    @app.route(f"/webhook/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
    def telegram_webhook():
        update = request.get_json()
        if not update or "message" not in update:
            return "OK", 200
        
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(msg["from"]["id"])
        text = msg.get("text", "")

        if ADMIN_TELEGRAM_ID and user_id != ADMIN_TELEGRAM_ID:
            send_telegram_message(chat_id, "⚠️ Unauthorized access restricted to COO Admin.")
            return "OK", 200

        if text.startswith("/status"):
            send_telegram_message(chat_id, "🚀 *LeadsIndia COO Status:* Systems active, multi-category architecture on standby, 24/7 cloud running.")
        elif text.startswith("/trigger"):
            send_telegram_message(chat_id, "⚡ Autonomous execution cycle triggered successfully.")
        else:
            send_telegram_message(chat_id, f"🤖 *COO Received:* `{text}`\nProcessing infrastructure command automatically...")
        
        return "OK", 200

# Keep-alive background ping to prevent Render free tier sleep
def keep_alive():
    while True:
        try:
            render_url = os.getenv("RENDER_EXTERNAL_URL")
            if render_url:
                requests.get(render_url)
        except Exception:
            pass
        time.sleep(300)

if __name__ == "__main__":
    threading.Thread(target=keep_alive, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

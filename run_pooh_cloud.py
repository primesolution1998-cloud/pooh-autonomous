import os
import logging
import threading
import time
import requests
from flask import Flask, request
from core.command_processor import process_command, approve_task
from core.task_store import list_tasks, get_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Pooh-LeadsIndia-Cloud")

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
POOH_API_KEY = os.getenv("POOH_API_KEY", "")
POOH_PRIMARY = os.getenv("POOH_PRIMARY", "false").lower() == "true"
REGISTER_TELEGRAM_WEBHOOK = os.getenv("REGISTER_TELEGRAM_WEBHOOK", "false").lower() == "true"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else ""


def _api_authorized():
    return bool(POOH_API_KEY) and request.headers.get("X-POOH-Key") == POOH_API_KEY


def send_telegram_message(chat_id, text):
    if not TELEGRAM_API_URL:
        return
    try:
        requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as exc:
        logger.error("Telegram error: %s", exc)


def register_telegram_webhook():
    if not (POOH_PRIMARY and REGISTER_TELEGRAM_WEBHOOK and TELEGRAM_API_URL and TELEGRAM_WEBHOOK_SECRET):
        return
    render_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not render_url:
        logger.warning("Telegram webhook not registered: RENDER_EXTERNAL_URL missing")
        return
    webhook_url = f"{render_url}/webhook/telegram"
    try:
        response = requests.post(
            f"{TELEGRAM_API_URL}/setWebhook",
            json={
                "url": webhook_url,
                "secret_token": TELEGRAM_WEBHOOK_SECRET,
                "drop_pending_updates": True,
            },
            timeout=15,
        )
        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        if response.ok and payload.get("ok"):
            logger.info("Telegram webhook registered at /webhook/telegram")
        else:
            logger.error("Telegram webhook registration failed: status=%s description=%s", response.status_code, payload.get("description", "unknown"))
    except Exception as exc:
        logger.error("Telegram webhook registration error: %s", exc)


@app.route("/", methods=["GET"])
def health_check():
    return {
        "service": "pooh-autonomous",
        "status": "ok",
        "primary": POOH_PRIMARY,
        "telegram_webhook_owner": bool(POOH_PRIMARY and REGISTER_TELEGRAM_WEBHOOK),
    }, 200


@app.route("/api/command", methods=["POST"])
def api_command():
    if not _api_authorized():
        return {"error": "unauthorized"}, 401
    data = request.get_json(silent=True) or {}
    text = str(data.get("command", "")).strip()
    if not text:
        return {"error": "command required"}, 400
    return {"response": process_command(text)}, 200


@app.route("/api/tasks", methods=["GET"])
def api_tasks():
    if not _api_authorized():
        return {"error": "unauthorized"}, 401
    status = request.args.get("status") or None
    limit = request.args.get("limit", "50")
    try:
        limit = int(limit)
    except ValueError:
        return {"error": "invalid limit"}, 400
    return {"tasks": list_tasks(limit=limit, status=status)}, 200


@app.route("/api/tasks/<task_id>", methods=["GET"])
def api_task(task_id):
    if not _api_authorized():
        return {"error": "unauthorized"}, 401
    task = get_task(task_id)
    if not task:
        return {"error": "not_found"}, 404
    return {"task": task}, 200


@app.route("/api/tasks/<task_id>/approve", methods=["POST"])
def api_approve(task_id):
    if not _api_authorized():
        return {"error": "unauthorized"}, 401
    result = approve_task(task_id)
    return result, 200 if result.get("ok") else 409 if result.get("error") == "task_not_awaiting_approval" else 404


if TELEGRAM_BOT_TOKEN:
    @app.route("/webhook/telegram", methods=["POST"])
    def telegram_webhook():
        if not POOH_PRIMARY:
            return "Not primary", 503
        if not ADMIN_TELEGRAM_ID or not TELEGRAM_WEBHOOK_SECRET:
            return "Unauthorized", 403
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != TELEGRAM_WEBHOOK_SECRET:
            return "Unauthorized", 403
        update = request.get_json(silent=True) or {}
        msg = update.get("message")
        if not msg:
            return "OK", 200
        chat_id = msg.get("chat", {}).get("id")
        user_id = str(msg.get("from", {}).get("id", ""))
        text = str(msg.get("text", "")).strip()
        if user_id != ADMIN_TELEGRAM_ID:
            return "Unauthorized", 403

        if text == "/status":
            awaiting = len(list_tasks(limit=100, status="AWAITING_APPROVAL"))
            send_telegram_message(chat_id, f"🚀 *POOH Status*\nService: active\nAwaiting approval: {awaiting}")
        elif text.startswith("/approve "):
            task_id = text.split(maxsplit=1)[1].strip()
            result = approve_task(task_id)
            send_telegram_message(chat_id, f"Approval result: `{result}`")
        elif text == "/tasks":
            tasks = list_tasks(limit=10)
            lines = [f"{t.get('id')} — {t.get('status')} — {t.get('command','')[:45]}" for t in tasks]
            send_telegram_message(chat_id, "*Latest Tasks*\n" + ("\n".join(lines) if lines else "No tasks"))
        else:
            send_telegram_message(chat_id, process_command(text))
        return "OK", 200


def keep_alive():
    while True:
        try:
            render_url = os.getenv("RENDER_EXTERNAL_URL")
            if render_url:
                requests.get(render_url, timeout=10)
        except Exception:
            pass
        time.sleep(300)


if __name__ == "__main__":
    register_telegram_webhook()
    threading.Thread(target=keep_alive, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

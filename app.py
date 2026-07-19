import os
import requests
from flask import Flask, send_from_directory, request, jsonify, redirect

app = Flask(__name__, static_folder=".", static_url_path="")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("ADMIN_CHAT_ID", "6080897180")

OLD_HOST = "granat-site-granatgold999.amvera.io"
NEW_DOMAIN = "https://granat-kmv.ru"


@app.before_request
def redirect_old_domain():
    if request.host.lower() == OLD_HOST:
        return redirect(NEW_DOMAIN + request.full_path.rstrip("?"), code=301)


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/privacy.html")
def privacy():
    return send_from_directory(".", "privacy.html")


@app.route("/api/order", methods=["POST"])
def order():
    data = request.get_json(silent=True) or request.form or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(ok=False, error="Укажите имя"), 400

    phone = (data.get("phone") or "").strip()
    service = (data.get("service") or "").strip()
    notes = (data.get("notes") or "").strip()

    lines = ["🔔 НОВАЯ ЗАЯВКА С САЙТА", "", f"👤 Имя: {name}"]
    if phone:
        lines.append(f"📞 Телефон/Telegram: {phone}")
    if service:
        lines.append(f"🛍 Услуга: {service}")
    if notes:
        lines.append(f"📝 Пожелания: {notes}")
    text = "\n".join(lines)

    if not TOKEN:
        return jsonify(ok=False, error="Сервер не настроен"), 500

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text},
            timeout=15,
        )
        if r.status_code != 200:
            return jsonify(ok=False, error="Telegram error"), 502
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)

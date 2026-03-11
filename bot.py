import os
import json
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Store chat histories in memory (resets on restart)
chat_histories = {}

SYSTEM_PROMPT = """РўС‹ Р»РёС‡РЅС‹Р№ С€РѕРїРїРёРЅРі-Р°СЃСЃРёСЃС‚РµРЅС‚ ShopBot рџ›Ќ РџРѕРјРѕРіР°РµС€СЊ Р»СЋРґСЏРј РЅР°Р№С‚Рё С‚РѕРІР°СЂС‹ РЅР° СЂРѕСЃСЃРёР№СЃРєРёС… РјР°СЂРєРµС‚РїР»РµР№СЃР°С….

РџР РђР’РР›Рђ:
1. Р•СЃР»Рё Р·Р°РїСЂРѕСЃ СЂР°СЃРїР»С‹РІС‡Р°С‚С‹Р№ вЂ” Р·Р°РґР°РІР°Р№ СѓС‚РѕС‡РЅСЏСЋС‰РёРµ РІРѕРїСЂРѕСЃС‹ (Р±СЋРґР¶РµС‚, С†РІРµС‚, СЂР°Р·РјРµСЂ, РґР»СЏ РєРѕРіРѕ)
2. РљРѕРіРґР° РґРѕСЃС‚Р°С‚РѕС‡РЅРѕ РёРЅС„РѕСЂРјР°С†РёРё вЂ” РґР°РІР°Р№ 3-4 РєРѕРЅРєСЂРµС‚РЅС‹С… СЂРµРєРѕРјРµРЅРґР°С†РёРё
3. Р”Р»СЏ РєР°Р¶РґРѕРіРѕ С‚РѕРІР°СЂР° СѓРєР°Р·С‹РІР°Р№ РЅР°Р·РІР°РЅРёРµ, РѕРїРёСЃР°РЅРёРµ Рё РїСЂРёРјРµСЂРЅСѓСЋ С†РµРЅСѓ
4. РџРѕСЃР»Рµ РєР°Р¶РґРѕРіРѕ С‚РѕРІР°СЂР° СЃСЂР°Р·Сѓ РґР°РІР°Р№ СЃСЃС‹Р»РєРё РґР»СЏ РїРѕРёСЃРєР° РЅР° РјР°СЂРєРµС‚РїР»РµР№СЃР°С…
5. Р‘СѓРґСЊ РґСЂСѓР¶РµР»СЋР±РЅС‹Рј, РёСЃРїРѕР»СЊР·СѓР№ СЌРјРѕРґР·Рё, РѕС‚РІРµС‡Р°Р№ РїРѕ-СЂСѓСЃСЃРєРё
6. РџРѕРјРЅРё РєРѕРЅС‚РµРєСЃС‚ РїСЂРµРґС‹РґСѓС‰РёС… СЃРѕРѕР±С‰РµРЅРёР№ РІ РґРёР°Р»РѕРіРµ

Р¤РћР РњРђРў РўРћР’РђР Рђ:
рџ›’ *РќР°Р·РІР°РЅРёРµ С‚РѕРІР°СЂР°*
рџ“ќ РљСЂР°С‚РєРѕРµ РѕРїРёСЃР°РЅРёРµ
рџ’° РѕС‚ XXX СЂСѓР±.
рџ”Ќ РќР°Р№С‚Рё: [Ozon](СЃСЃС‹Р»РєР°) | [Wildberries](СЃСЃС‹Р»РєР°) | [РЇРЅРґРµРєСЃ](СЃСЃС‹Р»РєР°) | [AliExpress](СЃСЃС‹Р»РєР°)
"""

def build_search_links(query):
    enc = requests.utils.quote(query)
    return (
        f"[Ozon](https://www.ozon.ru/search/?text={enc}) | "
        f"[WB](https://www.wildberries.ru/catalog/0/search.aspx?search={enc}) | "
        f"[РЇРњ](https://market.yandex.ru/search?text={enc}) | "
        f"[Ali](https://www.aliexpress.ru/wholesale?SearchText={enc})"
    )

def send_message(chat_id, text, parse_mode="Markdown"):
    """Send message to Telegram"""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Send error: {e}")

def send_typing(chat_id):
    """Show typing indicator"""
    try:
        requests.post(f"{TELEGRAM_API}/sendChatAction",
                      json={"chat_id": chat_id, "action": "typing"}, timeout=5)
    except:
        pass

def ask_ai(chat_id, user_message):
    """Send message to OpenRouter AI and get response"""
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []

    chat_histories[chat_id].append({"role": "user", "content": user_message})

    # Keep last 10 messages for context
    history = chat_histories[chat_id][-10:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://shopbot.app",
                "X-Title": "ShopBot"
            },
            json={
                "model": "anthropic/claude-haiku-4-5-20251001",
                "max_tokens": 1000,
                "messages": messages
            },
            timeout=30
        )
        print(f"OpenRouter status: {res.status_code}")
        print(f"OpenRouter response: {res.text[:500]}")

        if res.status_code != 200:
            return f"РћС€РёР±РєР° API ({res.status_code}) рџ” РџРѕРїСЂРѕР±СѓР№ РїРѕР·Р¶Рµ."

        data = res.json()

        if "choices" not in data or not data["choices"]:
            print(f"Unexpected response: {data}")
            return "РќРµ РїРѕР»СѓС‡РёР» РѕС‚РІРµС‚ РѕС‚ AI рџ” РџРѕРїСЂРѕР±СѓР№ РµС‰С‘ СЂР°Р·."

        reply = data["choices"][0]["message"]["content"]
        chat_histories[chat_id].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        print(f"AI error: {type(e).__name__}: {e}")
        return "РР·РІРёРЅРё, РїСЂРѕРёР·РѕС€Р»Р° РѕС€РёР±РєР° рџ” РџРѕРїСЂРѕР±СѓР№ РµС‰С‘ СЂР°Р·."

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    first_name = message.get("from", {}).get("first_name", "")

    # Commands
    if text == "/start":
        chat_histories[chat_id] = []  # Reset history
        welcome = (
            f"РџСЂРёРІРµС‚, {first_name}! рџ‘‹\n\n"
            "РЇ *ShopBot* вЂ” С‚РІРѕР№ Р»РёС‡РЅС‹Р№ С€РѕРїРїРёРЅРі-Р°СЃСЃРёСЃС‚РµРЅС‚ рџ›Ќ\n\n"
            "РћРїРёС€Рё С‡С‚Рѕ РёС‰РµС€СЊ, Рё СЏ РїРѕРјРѕРіСѓ РЅР°Р№С‚Рё Р»СѓС‡С€РёРµ РІР°СЂРёР°РЅС‚С‹ РЅР°:\n"
            "вЂў Ozon\nвЂў Wildberries\nвЂў РЇРЅРґРµРєСЃ РњР°СЂРєРµС‚\nвЂў AliExpress\n\n"
            "РџСЂРѕСЃС‚Рѕ РЅР°РїРёС€Рё С‡С‚Рѕ С‚РµР±Рµ РЅСѓР¶РЅРѕ! РќР°РїСЂРёРјРµСЂ:\n"
            "_В«РёС‰Сѓ РЅР°СѓС€РЅРёРєРё РґРѕ 3000 СЂСѓР±Р»РµР№В»_\n"
            "_В«РЅСѓР¶РµРЅ РїРѕРґР°СЂРѕРє РјР°РјРµ РЅР° РґРµРЅСЊ СЂРѕР¶РґРµРЅРёСЏВ»_"
        )
        send_message(chat_id, welcome)
        return

    if text == "/help":
        help_text = (
            "рџ† *РљР°Рє РїРѕР»СЊР·РѕРІР°С‚СЊСЃСЏ ShopBot:*\n\n"
            "РџСЂРѕСЃС‚Рѕ РѕРїРёС€Рё С‡С‚Рѕ РёС‰РµС€СЊ вЂ” СЏ Р·Р°РґР°Рј СѓС‚РѕС‡РЅСЏСЋС‰РёРµ РІРѕРїСЂРѕСЃС‹ "
            "Рё РґР°Рј РєРѕРЅРєСЂРµС‚РЅС‹Рµ СЂРµРєРѕРјРµРЅРґР°С†РёРё СЃ СЃСЃС‹Р»РєР°РјРё.\n\n"
            "*РљРѕРјР°РЅРґС‹:*\n"
            "/start вЂ” РЅР°С‡Р°С‚СЊ Р·Р°РЅРѕРІРѕ\n"
            "/clear вЂ” РѕС‡РёСЃС‚РёС‚СЊ РёСЃС‚РѕСЂРёСЋ\n"
            "/help вЂ” СЌС‚Р° СЃРїСЂР°РІРєР°"
        )
        send_message(chat_id, help_text)
        return

    if text == "/clear":
        chat_histories[chat_id] = []
        send_message(chat_id, "РСЃС‚РѕСЂРёСЏ РѕС‡РёС‰РµРЅР°! РќР°С‡РЅС‘Рј СЃРЅР°С‡Р°Р»Р° рџ›Ќ Р§С‚Рѕ РёС‰РµС€СЊ?")
        return

    if not text:
        send_message(chat_id, "РќР°РїРёС€Рё С‡С‚Рѕ РёС‰РµС€СЊ вЂ” Рё СЏ РїРѕРјРѕРіСѓ РЅР°Р№С‚Рё! рџ›Ќ")
        return

    # Show typing and get AI response
    send_typing(chat_id)
    reply = ask_ai(chat_id, text)
    send_message(chat_id, reply)

@app.route(f"/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data:
        handle_message(data["message"])
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "ShopBot is running! рџ›Ќ", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

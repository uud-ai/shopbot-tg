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

SYSTEM_PROMPT = """Ты личный шоппинг-ассистент ShopBot 🛍 Помогаешь людям найти товары на российских маркетплейсах.

ПРАВИЛА:
1. Если запрос расплывчатый — задавай уточняющие вопросы (бюджет, цвет, размер, для кого)
2. Когда достаточно информации — давай 3-4 конкретных рекомендации
3. Для каждого товара указывай название, описание и примерную цену
4. После каждого товара сразу давай ссылки для поиска на маркетплейсах
5. Будь дружелюбным, используй эмодзи, отвечай по-русски
6. Помни контекст предыдущих сообщений в диалоге

ФОРМАТ ТОВАРА:
🛒 *Название товара*
📝 Краткое описание
💰 от XXX руб.
🔍 Найти: [Ozon](ссылка) | [Wildberries](ссылка) | [Яндекс](ссылка) | [AliExpress](ссылка)
"""

def build_search_links(query):
    enc = requests.utils.quote(query)
    return (
        f"[Ozon](https://www.ozon.ru/search/?text={enc}) | "
        f"[WB](https://www.wildberries.ru/catalog/0/search.aspx?search={enc}) | "
        f"[ЯМ](https://market.yandex.ru/search?text={enc}) | "
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
            return f"Ошибка API ({res.status_code}) 😔 Попробуй позже."

        data = res.json()

        if "choices" not in data or not data["choices"]:
            print(f"Unexpected response: {data}")
            return "Не получил ответ от AI 😔 Попробуй ещё раз."

        reply = data["choices"][0]["message"]["content"]
        chat_histories[chat_id].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        print(f"AI error: {type(e).__name__}: {e}")
        return "Извини, произошла ошибка 😔 Попробуй ещё раз."

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    first_name = message.get("from", {}).get("first_name", "")

    # Commands
    if text == "/start":
        chat_histories[chat_id] = []  # Reset history
        welcome = (
            f"Привет, {first_name}! 👋\n\n"
            "Я *ShopBot* — твой личный шоппинг-ассистент 🛍\n\n"
            "Опиши что ищешь, и я помогу найти лучшие варианты на:\n"
            "• Ozon\n• Wildberries\n• Яндекс Маркет\n• AliExpress\n\n"
            "Просто напиши что тебе нужно! Например:\n"
            "_«ищу наушники до 3000 рублей»_\n"
            "_«нужен подарок маме на день рождения»_"
        )
        send_message(chat_id, welcome)
        return

    if text == "/help":
        help_text = (
            "🆘 *Как пользоваться ShopBot:*\n\n"
            "Просто опиши что ищешь — я задам уточняющие вопросы "
            "и дам конкретные рекомендации с ссылками.\n\n"
            "*Команды:*\n"
            "/start — начать заново\n"
            "/clear — очистить историю\n"
            "/help — эта справка"
        )
        send_message(chat_id, help_text)
        return

    if text == "/clear":
        chat_histories[chat_id] = []
        send_message(chat_id, "История очищена! Начнём сначала 🛍 Что ищешь?")
        return

    if not text:
        send_message(chat_id, "Напиши что ищешь — и я помогу найти! 🛍")
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
    return "ShopBot is running! 🛍", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

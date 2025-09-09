import requests
import json
from bs4 import BeautifulSoup
from telegram import Bot, Update
from telegram.ext import CommandHandler, CallbackContext, Updater
from apscheduler.schedulers.background import BackgroundScheduler

# --- Config ---
BOT_TOKEN = "8104734743:AAGgw7h_Lb_Cdu_zQW9JV8uaAKb6TW7Z1DA"
bot = Bot(token=BOT_TOKEN)
updater = Updater(token=BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# File to store registered channels + posted news
CHANNEL_FILE = "channels.json"
POSTED_FILE = "posted.json"

def load_json(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except:
        return []

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)

# --- Register Command ---
def register(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    channels = load_json(CHANNEL_FILE)
    if chat_id not in channels:
        channels.append(chat_id)
        save_json(CHANNEL_FILE, channels)
        update.message.reply_text("✅ This channel has been registered for news updates!")
    else:
        update.message.reply_text("⚡ Already registered!")

dispatcher.add_handler(CommandHandler("register", register))

# --- Fetch News ---
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc?query=diplomatic&sourcelang:english&mode=artlist&maxrecords=5&format=json"

def get_media(url):
    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]
    except:
        pass
    return None

def fetch_and_send_news():
    try:
        response = requests.get(GDELT_URL, timeout=10)
        data = response.json()
        channels = load_json(CHANNEL_FILE)
        posted_urls = load_json(POSTED_FILE)

        if "articles" in data:
            for article in data["articles"][:5]:
                title = article.get("title", "No Title")
                url = article.get("url", "")
                source = article.get("sourceCountry", "Unknown")

                # Skip already posted
                if url in posted_urls:
                    continue
                posted_urls.append(url)
                save_json(POSTED_FILE, posted_urls)

                image = get_media(url)
                caption = f"🌍 *{title}*\n📌 Source: {source}\n🔗 {url}"

                for chat_id in channels:
                    try:
                        if image:
                            bot.send_photo(chat_id=chat_id, photo=image, caption=caption, parse_mode="Markdown")
                        else:
                            bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")
                    except Exception as e:
                        print(f"Error sending to {chat_id}: {e}")

    except Exception as e:
        print("Error fetching news:", e)

# --- Scheduler ---
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_and_send_news, "interval", minutes=15)
scheduler.start()

# --- Run Bot ---
updater.start_polling()
updater.idle()

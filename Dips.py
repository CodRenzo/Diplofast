import logging
import requests
from telegram import Update, ChatMember
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    ChatMemberHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================== CONFIG ==================
BOT_TOKEN = "8104734743:AAGgw7h_Lb_Cdu_zQW9JV8uaAKb6TW7Z1DA"

# GDELT API for diplomacy-related articles (English only)
GDELT_URL = (
    "https://api.gdeltproject.org/api/v2/doc/doc"
    "?query=diplomacy&mode=ArtList&format=json&maxrecords=10&timespan=15m"
)

# Store subscribed channels/groups dynamically
SUBSCRIBED_CHATS = set()

# =============== LOGGING ===================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("DiploFast")

# =============== FUNCTIONS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command, activates posting in this chat"""
    chat_id = update.effective_chat.id
    SUBSCRIBED_CHATS.add(chat_id)
    await update.message.reply_text(
        "✅ DiploFast Bot activated!\n\n"
        "I'll send the latest diplomatic news here automatically."
    )
    logger.info("Bot manually started in chat: %s", chat_id)

def fetch_gdelt_news():
    """Fetch diplomatic news from GDELT API"""
    try:
        response = requests.get(GDELT_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        articles = []

        if "articles" in data:
            for art in data["articles"]:
                title = art.get("title", "No Title")
                url = art.get("url", "")
                source = art.get("domain", "Unknown")
                # Only keep if there’s a proper link
                if url:
                    articles.append({
                        "title": title,
                        "url": url,
                        "source": source
                    })
        return articles
    except Exception as e:
        logger.error("❌ Failed to fetch GDELT news: %s", str(e))
        return []

async def post_news(context: ContextTypes.DEFAULT_TYPE):
    """Send news to all subscribed chats"""
    articles = fetch_gdelt_news()
    if not articles:
        logger.info("No new diplomatic articles found.")
        return

    sent_titles = set()  # avoid duplicate messages in one batch

    for chat_id in list(SUBSCRIBED_CHATS):
        for article in articles[:5]:  # send only top 5
            if article["title"] in sent_titles:
                continue
            sent_titles.add(article["title"])

            message = (
                f"🌍 *{article['title']}*\n"
                f"_Source: {article['source']}_\n\n"
                f"[Read more]({article['url']})"
            )
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="Markdown",
                    disable_web_page_preview=False
                )
                logger.info("Posted news to %s: %s", chat_id, article["title"])
            except Exception as e:
                logger.error("⚠️ Failed to post to %s: %s", chat_id, str(e))

async def track_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detect when bot is added/removed"""
    result = update.my_chat_member
    chat = result.chat
    new_status = result.new_chat_member.status

    if new_status in [ChatMember.ADMINISTRATOR, ChatMember.MEMBER]:
        SUBSCRIBED_CHATS.add(chat.id)
        logger.info("✅ Bot added to: %s (%s)", chat.title, chat.id)
    elif new_status == ChatMember.LEFT:
        SUBSCRIBED_CHATS.discard(chat.id)
        logger.info("❌ Bot removed from: %s (%s)", chat.title, chat.id)

# =============== MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatMemberHandler(track_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    # Scheduler: fetch and post every 30 minutes
    scheduler = AsyncIOScheduler()
    scheduler.add_job(post_news, "interval", minutes=30, args=[app])
    scheduler.start()

    logger.info("🤖 DiploFast Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

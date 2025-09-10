import asyncio
from telegram import Bot
from telegram.error import TelegramError
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- CONFIG ---
BOT_TOKEN = "8104734743:AAGgw7h_Lb_Cdu_zQW9JV8uaAKb6TW7Z1DA"
GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc?query=diplomatic&mode=ArtList&format=json&maxrecords=5"
CHANNEL_ID = "@GeoDiplomacyy"

bot = Bot(token=BOT_TOKEN)

async def fetch_latest_news():
    """Fetch latest diplomatic news from GDELT"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(GDELT_API_URL)
            resp.raise_for_status()
            data = resp.json()
            articles = data.get("articles", [])
            
            if not articles:
                return "No latest diplomatic news found."
            
            news_list = []
            for art in articles[:5]:
                title = art.get("title", "No Title").strip()
                url = art.get("url", "").strip()
                if title and url:
                    news_list.append(f"📰 {title}\n🔗 {url}")
            
            return "\n\n".join(news_list) if news_list else "No valid news articles found."
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching news: {e}")
            return f"HTTP error fetching news: {e}"
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return f"Error fetching news: {e}"

async def send_news():
    """Send news to the specified channel"""
    try:
        news = await fetch_latest_news()
        await bot.send_message(chat_id=CHANNEL_ID, text=news)
        logger.info(f"✅ News sent successfully to {CHANNEL_ID}")
    except TelegramError as e:
        logger.error(f"❌ Failed to send message to {CHANNEL_ID}: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")

async def main():
    """Main function to start the scheduler"""
    logger.info("🚀 Starting Diplomacy News Bot...")
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_news, "interval", hours=1)
    scheduler.start()
    
    logger.info(f"✅ Scheduler started. Bot will post to {CHANNEL_ID} every hour.")
    
    # Send initial message
    await send_news()
    
    # Keep the script running
    try:
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Shutting down scheduler...")
        scheduler.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")

import asyncio
from telegram import Bot
from telegram.error import TelegramError
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
            return f"HTTP error fetching news: {e}"
        except Exception as e:
            return f"Error fetching news: {e}"

async def send_news():
    """Send news to the specified channel"""
    news = await fetch_latest_news()
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=news)
        print(f"✅ News sent successfully to {CHANNEL_ID}")
    except TelegramError as e:
        print(f"❌ Failed to send message to {CHANNEL_ID}: {e}")

async def main():
    """Main function to start the scheduler"""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_news, "interval", hours=1)
    scheduler.start()
    print(f"🚀 Scheduler started. Bot will post to {CHANNEL_ID} every hour.")
    
    # Send initial message
    await send_news()
    
    # Keep the script running
    try:
        await asyncio.Future()
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Scheduler stopped.")
        scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

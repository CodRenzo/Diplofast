import asyncio
import logging
from telegram import Bot, InputMediaPhoto
from telegram.error import TelegramError
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DiplomacyBot:
    def __init__(self):
        self.BOT_TOKEN = "8104734743:AAGgw7h_Lb_Cdu_zQW9JV8uaAKb6TW7Z1DA"
        self.NEWS_API_KEY = "ef68ac134f8d4c8988a7e9e16b5e984c"  # Your NewsAPI key
        self.CHANNEL_ID = "@GeoDiplomacyy"
        self.bot = Bot(token=self.BOT_TOKEN)
        self.scheduler = AsyncIOScheduler()

    async def fetch_english_news(self):
        """Fetch English diplomatic news with images from NewsAPI"""
        try:
            # Get news from last 24 hours
            from_date = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d')
            
            news_api_url = f"https://newsapi.org/v2/everything?q=diplomacy+OR+foreign+affairs+OR+international+relations&language=en&from={from_date}&sortBy=publishedAt&pageSize=5&apiKey={self.NEWS_API_KEY}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("Fetching news from NewsAPI...")
                headers = {'User-Agent': 'DiplomacyBot/1.0'}
                resp = await client.get(news_api_url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                
                articles = data.get("articles", [])
                
                if not articles:
                    logger.warning("No articles found in NewsAPI response")
                    # Fallback to GDELT
                    return await self.fetch_gdelt_news()
                
                news_items = []
                for art in articles[:3]:  # Get top 3 articles with images
                    title = art.get("title", "").strip()
                    description = art.get("description", "").strip()
                    url = art.get("url", "").strip()
                    image_url = art.get("urlToImage", "").strip()
                    source = art.get("source", {}).get("name", "Unknown")
                    
                    if title and url:
                        news_item = {
                            'title': title,
                            'description': description,
                            'url': url,
                            'image_url': image_url,
                            'source': source
                        }
                        news_items.append(news_item)
                
                logger.info(f"Fetched {len(news_items)} news articles with media")
                return news_items
                    
        except Exception as e:
            logger.error(f"Error fetching from NewsAPI: {e}")
            # Fallback to GDELT
            return await self.fetch_gdelt_news()

    async def fetch_gdelt_news(self):
        """Fallback to GDELT if NewsAPI fails"""
        try:
            gdelt_url = "https://api.gdeltproject.org/api/v2/doc/doc?query=diplomacy&mode=ArtList&format=json&maxrecords=3"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(gdelt_url)
                resp.raise_for_status()
                data = resp.json()
                articles = data.get("articles", [])
                
                news_items = []
                for art in articles:
                    title = art.get("title", "").strip()
                    url = art.get("url", "").strip()
                    
                    if title and url:
                        news_items.append({
                            'title': title,
                            'description': "",
                            'url': url,
                            'image_url': "",
                            'source': "GDELT"
                        })
                
                return news_items
                
        except Exception as e:
            logger.error(f"Error fetching from GDELT: {e}")
            return []

    async def send_news_with_media(self):
        """Send news with images/videos to channel"""
        try:
            logger.info("Fetching news with media...")
            news_items = await self.fetch_english_news()
            
            if not news_items:
                logger.warning("No news items to send")
                # Send a fallback message
                await self.bot.send_message(
                    chat_id=self.CHANNEL_ID,
                    text="🌍 No new diplomatic news found in the last 24 hours. Check back later!",
                    parse_mode='Markdown'
                )
                return
            
            for news in news_items:
                try:
                    # Create caption
                    caption = f"📰 *{news['title']}*\n\n"
                    if news['description']:
                        caption += f"{news['description']}\n\n"
                    caption += f"🔗 [Read more]({news['url']})\n"
                    caption += f"📚 Source: {news['source']}"
                    
                    # Send message with media if available
                    if news['image_url'] and news['image_url'].startswith('http'):
                        try:
                            await self.bot.send_photo(
                                chat_id=self.CHANNEL_ID,
                                photo=news['image_url'],
                                caption=caption,
                                parse_mode='Markdown'
                            )
                            logger.info(f"✅ Sent news with image: {news['title'][:50]}...")
                        except Exception as e:
                            logger.warning(f"Couldn't send image, sending text only: {e}")
                            await self.bot.send_message(
                                chat_id=self.CHANNEL_ID,
                                text=caption,
                                parse_mode='Markdown',
                                disable_web_page_preview=False
                            )
                    else:
                        await self.bot.send_message(
                            chat_id=self.CHANNEL_ID,
                            text=caption,
                            parse_mode='Markdown',
                            disable_web_page_preview=False
                        )
                        logger.info(f"✅ Sent text news: {news['title'][:50]}...")
                    
                    # Wait 2 seconds between messages to avoid rate limiting
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error sending news item: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Error in send_news_with_media: {e}")

    async def run(self):
        """Main function to start the bot"""
        try:
            logger.info("🚀 Starting Enhanced Diplomacy News Bot...")
            
            # Test connection
            try:
                me = await self.bot.get_me()
                logger.info(f"Bot connected: @{me.username}")
            except Exception as e:
                logger.error(f"Bot connection failed: {e}")
                return

            # Setup scheduler - run every 3 hours to avoid spam
            self.scheduler.add_job(self.send_news_with_media, "interval", hours=3, misfire_grace_time=60)
            self.scheduler.start()
            
            logger.info("✅ Scheduler started. Bot will post every 3 hours.")
            
            # Send initial message
            await self.send_news_with_media()
            
            # Keep the bot running
            while True:
                await asyncio.sleep(10800)  # Sleep for 3 hours
                
        except (KeyboardInterrupt, SystemExit):
            logger.info("🛑 Shutting down...")
            self.scheduler.shutdown()
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
            self.scheduler.shutdown()

async def main():
    bot = DiplomacyBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())

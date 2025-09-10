import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
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
        self.NEWS_API_KEY = "ef68ac134f8d4c8988a7e9e16b5e984c"
        self.CHANNEL_ID = "@GeoDiplomacyy"
        self.bot = Bot(token=self.BOT_TOKEN)
        self.scheduler = AsyncIOScheduler()

    async def fetch_global_diplomatic_news(self):
        """Fetch global English diplomatic news from reputable sources"""
        try:
            # Get news from last 24 hours from top international sources
            from_date = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d')
            
            # Focus on major global news sources and specific diplomatic terms
            news_api_url = f"https://newsapi.org/v2/everything?q=diplomacy OR \"foreign affairs\" OR \"state department\" OR \"foreign minister\" OR \"international relations\" OR \"peace talks\"&language=en&sortBy=publishedAt&pageSize=3&apiKey={self.NEWS_API_KEY}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("Fetching global diplomatic news from NewsAPI...")
                headers = {'User-Agent': 'GlobalDiplomacyBot/1.0'}
                resp = await client.get(news_api_url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                
                articles = data.get("articles", [])
                
                if not articles:
                    logger.warning("No diplomatic articles found")
                    return []
                
                # Filter for reputable international sources
                reputable_sources = ['reuters', 'ap', 'bbc', 'bloomberg', 'the-wall-street-journal', 
                                   'the-new-york-times', 'washington-post', 'foreign-policy', 'politico']
                
                filtered_articles = []
                for art in articles:
                    source_id = art.get('source', {}).get('id', '').lower()
                    source_name = art.get('source', {}).get('name', '').lower()
                    
                    # Check if from reputable source or has diplomatic relevance
                    if (any(src in source_id for src in reputable_sources) or 
                        any(src in source_name for src in reputable_sources) or
                        any(keyword in art.get('title', '').lower() for keyword in 
                            ['diplomacy', 'foreign affairs', 'state department', 'foreign minister'])):
                        
                        title = art.get("title", "").strip()
                        description = art.get("description", "").strip()
                        url = art.get("url", "").strip()
                        image_url = art.get("urlToImage", "").strip()
                        source = art.get("source", {}).get("name", "Unknown")
                        
                        if title and url and self.is_english(title):
                            filtered_articles.append({
                                'title': title,
                                'description': description,
                                'url': url,
                                'image_url': image_url,
                                'source': source
                            })
                
                logger.info(f"Found {len(filtered_articles)} global diplomatic news articles")
                return filtered_articles[:2]  # Return only top 2 articles
                    
        except Exception as e:
            logger.error(f"Error fetching diplomatic news: {e}")
            return []

    def is_english(self, text):
        """Check if text is primarily English"""
        try:
            # Simple check - most English text will have primarily ASCII characters
            english_chars = sum(1 for c in text if ord(c) < 128)
            return english_chars / len(text) > 0.7 if text else False
        except:
            return False

    async def send_quality_news(self):
        """Send high-quality global diplomatic news"""
        try:
            logger.info("Fetching quality diplomatic news...")
            news_items = await self.fetch_global_diplomatic_news()
            
            if not news_items:
                logger.info("No quality diplomatic news found")
                return
            
            # Send only 1-2 best articles
            for news in news_items[:2]:
                try:
                    # Create professional caption
                    caption = f"🌍 **Global Diplomacy Update**\n\n"
                    caption += f"📰 *{news['title']}*\n\n"
                    
                    if news['description'] and len(news['description']) > 20:
                        caption += f"{news['description']}\n\n"
                    
                    caption += f"🔗 [Read Full Article]({news['url']})\n"
                    caption += f"🏛️ Source: {news['source']}\n"
                    caption += f"🕒 #Diplomacy #GlobalAffairs"
                    
                    # Send with image if available
                    if news['image_url'] and news['image_url'].startswith('http'):
                        try:
                            await self.bot.send_photo(
                                chat_id=self.CHANNEL_ID,
                                photo=news['image_url'],
                                caption=caption,
                                parse_mode='Markdown'
                            )
                            logger.info(f"✅ Sent quality news: {news['title'][:50]}...")
                        except Exception as e:
                            logger.warning(f"Image failed, sending text: {e}")
                            await self.send_text_news(news, caption)
                    else:
                        await self.send_text_news(news, caption)
                    
                    # Wait between posts
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Error sending news item: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Error in send_quality_news: {e}")

    async def send_text_news(self, news, caption):
        """Send news as text message"""
        await self.bot.send_message(
            chat_id=self.CHANNEL_ID,
            text=caption,
            parse_mode='Markdown',
            disable_web_page_preview=False
        )
        logger.info(f"✅ Sent text news: {news['title'][:50]}...")

    async def run(self):
        """Main function to start the bot"""
        try:
            logger.info("🚀 Starting Global Diplomacy News Bot...")
            
            # Test connection
            try:
                me = await self.bot.get_me()
                logger.info(f"Bot connected: @{me.username}")
            except Exception as e:
                logger.error(f"Bot connection failed: {e}")
                return

            # Setup scheduler - run every 6 hours for quality content
            self.scheduler.add_job(self.send_quality_news, "interval", hours=6, misfire_grace_time=60)
            self.scheduler.start()
            
            logger.info("✅ Scheduler started. Bot will post quality news every 6 hours.")
            
            # Send initial message
            await self.send_quality_news()
            
            # Keep the bot running
            while True:
                await asyncio.sleep(21600)  # Sleep for 6 hours
                
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

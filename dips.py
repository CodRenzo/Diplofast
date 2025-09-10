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
        """Fetch global English diplomatic news from NewsAPI"""
        try:
            # Get news from last 24 hours
            from_date = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d')
            
            # Specific query for diplomatic news
            query = "diplomacy OR \"foreign affairs\" OR \"state department\" OR \"foreign minister\" OR \"international relations\" OR \"peace talks\" OR \"diplomatic relations\" OR embassy OR ambassador"
            news_api_url = f"https://newsapi.org/v2/everything?q={query}&language=en&from={from_date}&sortBy=publishedAt&pageSize=15&apiKey={self.NEWS_API_KEY}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("Fetching global diplomatic news from NewsAPI...")
                headers = {'User-Agent': 'GlobalDiplomacyBot/1.0'}
                resp = await client.get(news_api_url, headers=headers)
                
                if resp.status_code != 200:
                    logger.error(f"NewsAPI error: {resp.status_code}")
                    return []
                
                data = resp.json()
                
                if data.get('status') != 'ok':
                    logger.error(f"NewsAPI status not ok: {data.get('status')}")
                    return []
                
                articles = data.get("articles", [])
                logger.info(f"Raw API returned {len(articles)} articles")
                
                # Filter for quality diplomatic news
                filtered_articles = []
                for art in articles:
                    try:
                        source = art.get('source', {})
                        source_name = source.get('name', 'Unknown')
                        
                        title = art.get("title", "").strip()
                        description = art.get("description", "").strip()
                        url = art.get("url", "").strip()
                        image_url = art.get("urlToImage", "").strip()
                        
                        # Skip if missing essential fields
                        if not title or not url:
                            continue
                            
                        # Check if it's actually about diplomacy (case-insensitive)
                        title_lower = title.lower()
                        desc_lower = (description or "").lower()
                        
                        diplomatic_keywords = [
                            'diplomacy', 'diplomatic', 'foreign affairs', 'state department',
                            'foreign minister', 'international relations', 'peace talks',
                            'embassy', 'ambassador', 'treaty', 'negotiation', 'summit',
                            'foreign policy', 'state visit', 'diplomat'
                        ]
                        
                        has_diplomatic_content = any(keyword in title_lower for keyword in diplomatic_keywords)
                        has_diplomatic_content |= any(keyword in desc_lower for keyword in diplomatic_keywords)
                        
                        if has_diplomatic_content:
                            filtered_articles.append({
                                'title': title,
                                'description': description,
                                'url': url,
                                'image_url': image_url,
                                'source': source_name
                            })
                            
                    except Exception as e:
                        logger.warning(f"Error processing article: {e}")
                        continue
                
                logger.info(f"Filtered to {len(filtered_articles)} diplomatic articles")
                return filtered_articles[:3]  # Return only top 3 articles
                    
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []

    async def send_quality_news(self):
        """Send high-quality global diplomatic news"""
        try:
            logger.info("Fetching quality diplomatic news...")
            news_items = await self.fetch_global_diplomatic_news()
            
            if not news_items:
                logger.info("No quality diplomatic news found")
                return
            
            # Send only the best articles
            for news in news_items:
                try:
                    # Create professional caption
                    caption = f"🌍 **Global Diplomacy Update**\n\n"
                    caption += f"📰 *{news['title']}*\n\n"
                    
                    if news['description'] and len(news['description']) > 20:
                        caption += f"{news['description']}\n\n"
                    
                    caption += f"🔗 [Read Full Article]({news['url']})\n"
                    caption += f"🏛️ Source: {news['source']}\n"
                    caption += f"#Diplomacy #GlobalAffairs"
                    
                    # Send with image if available
                    if news['image_url'] and news['image_url'].startswith('http'):
                        try:
                            await self.bot.send_photo(
                                chat_id=self.CHANNEL_ID,
                                photo=news['image_url'],
                                caption=caption,
                                parse_mode='Markdown'
                            )
                            logger.info(f"✅ Sent news with image from {news['source']}")
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
            logger.error(f"Error in send_quality_news: {e}")

    async def send_text_news(self, news, caption):
        """Send news as text message"""
        await self.bot.send_message(
            chat_id=self.CHANNEL_ID,
            text=caption,
            parse_mode='Markdown',
            disable_web_page_preview=False
        )
        logger.info(f"✅ Sent text news from {news['source']}")

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

            # Setup scheduler - run every 4 hours
            self.scheduler.add_job(self.send_quality_news, "interval", hours=4, misfire_grace_time=60)
            self.scheduler.start()
            
            logger.info("✅ Scheduler started. Bot will post quality news every 4 hours.")
            
            # Send initial message
            await self.send_quality_news()
            
            # Keep the bot running
            while True:
                await asyncio.sleep(14400)  # Sleep for 4 hours
                
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

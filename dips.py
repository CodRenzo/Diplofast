import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import json
import hashlib
import os

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
        self.sent_articles = set()
        self.sent_articles_file = "sent_articles.json"
        
        # Load previously sent articles
        self.load_sent_articles()

    def load_sent_articles(self):
        """Load previously sent articles from file"""
        try:
            if os.path.exists(self.sent_articles_file):
                with open(self.sent_articles_file, 'r') as f:
                    self.sent_articles = set(json.load(f))
                logger.info(f"Loaded {len(self.sent_articles)} previously sent articles")
            else:
                self.sent_articles = set()
        except Exception as e:
            logger.error(f"Error loading sent articles: {e}")
            self.sent_articles = set()

    def save_sent_articles(self):
        """Save sent articles to file"""
        try:
            with open(self.sent_articles_file, 'w') as f:
                json.dump(list(self.sent_articles), f)
        except Exception as e:
            logger.error(f"Error saving sent articles: {e}")

    def get_article_hash(self, article):
        """Generate unique hash for article to detect duplicates"""
        content = f"{article.get('title', '')}{article.get('url', '')}"
        return hashlib.md5(content.encode()).hexdigest()

    async def fetch_news(self):
        """Fetch all kinds of news - simplified approach"""
        try:
            # Get news from last 24 hours
            from_date = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d')
            
            # Very broad query to get all types of news
            query = "politics OR economy OR technology OR sports OR entertainment OR business OR health OR science"
            
            news_api_url = f"https://newsapi.org/v2/everything?q={query}&language=en&from={from_date}&sortBy=publishedAt&pageSize=10&apiKey={self.NEWS_API_KEY}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("Fetching news...")
                headers = {'User-Agent': 'NewsBot/1.0'}
                resp = await client.get(news_api_url, headers=headers)
                
                if resp.status_code != 200:
                    logger.error(f"NewsAPI error: {resp.status_code}")
                    # Fallback to top headlines if everything endpoint fails
                    return await self.fetch_top_headlines()
                
                data = resp.json()
                
                if data.get('status') != 'ok':
                    logger.error(f"NewsAPI status not ok: {data.get('status')}")
                    return await self.fetch_top_headlines()
                
                articles = data.get("articles", [])
                logger.info(f"API returned {len(articles)} articles")
                
                # Process articles and remove duplicates
                filtered_articles = []
                for art in articles:
                    try:
                        source = art.get('source', {})
                        source_name = source.get('name', 'Unknown')
                        
                        title = str(art.get("title", "")).strip()
                        description = str(art.get("description", "")).strip()
                        url = str(art.get("url", "")).strip()
                        image_url = str(art.get("urlToImage", "")).strip()
                        
                        # Skip if missing essential fields
                        if not title or not url:
                            continue
                            
                        # Generate unique hash for duplicate detection
                        article_hash = self.get_article_hash(art)
                        if article_hash in self.sent_articles:
                            continue
                            
                        filtered_articles.append({
                            'title': title,
                            'description': description,
                            'url': url,
                            'image_url': image_url,
                            'source': source_name,
                            'hash': article_hash
                        })
                            
                    except Exception as e:
                        logger.warning(f"Error processing article: {e}")
                        continue
                
                logger.info(f"Found {len(filtered_articles)} new articles")
                return filtered_articles[:3]  # Return top 3 articles
                    
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return await self.fetch_top_headlines()

    async def fetch_top_headlines(self):
        """Fallback method to fetch top headlines if everything endpoint fails"""
        try:
            news_api_url = f"https://newsapi.org/v2/top-headlines?country=us&pageSize=5&apiKey={self.NEWS_API_KEY}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("Fetching top headlines as fallback...")
                headers = {'User-Agent': 'NewsBot/1.0'}
                resp = await client.get(news_api_url, headers=headers)
                
                if resp.status_code != 200:
                    return []
                
                data = resp.json()
                
                if data.get('status') != 'ok':
                    return []
                
                articles = data.get("articles", [])
                logger.info(f"Top headlines returned {len(articles)} articles")
                
                filtered_articles = []
                for art in articles:
                    try:
                        source = art.get('source', {})
                        source_name = source.get('name', 'Unknown')
                        
                        title = str(art.get("title", "")).strip()
                        description = str(art.get("description", "")).strip()
                        url = str(art.get("url", "")).strip()
                        image_url = str(art.get("urlToImage", "")).strip()
                        
                        if not title or not url:
                            continue
                            
                        article_hash = self.get_article_hash(art)
                        if article_hash in self.sent_articles:
                            continue
                            
                        filtered_articles.append({
                            'title': title,
                            'description': description,
                            'url': url,
                            'image_url': image_url,
                            'source': source_name,
                            'hash': article_hash
                        })
                            
                    except Exception as e:
                        continue
                
                return filtered_articles[:2]  # Return top 2 headlines
                    
        except Exception as e:
            logger.error(f"Error fetching top headlines: {e}")
            return []

    async def send_news_update(self):
        """Send news update to channel"""
        try:
            logger.info("Fetching news update...")
            news_items = await self.fetch_news()
            
            if not news_items:
                logger.info("No new news found")
                return
            
            # Send articles
            for news in news_items:
                try:
                    # Create caption
                    caption = f"📰 **News Update**\n\n"
                    caption += f"*{news['title']}*\n\n"
                    
                    if news['description'] and len(news['description']) > 20:
                        caption += f"{news['description']}\n\n"
                    
                    caption += f"🔗 [Read Full Article]({news['url']})\n"
                    caption += f"📊 Source: {news['source']}\n"
                    caption += f"#News #Update"
                    
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
                    
                    # Mark as sent and save
                    self.sent_articles.add(news['hash'])
                    self.save_sent_articles()
                    
                    # Wait between posts to avoid rate limiting
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error sending news item: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in send_news_update: {e}")

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
            logger.info("🚀 Starting News Bot (30-min updates)...")
            
            # Test connection
            try:
                me = await self.bot.get_me()
                logger.info(f"Bot connected: @{me.username}")
            except Exception as e:
                logger.error(f"Bot connection failed: {e}")
                return

            # Setup scheduler - run every 30 minutes
            self.scheduler.add_job(self.send_news_update, "interval", minutes=30, misfire_grace_time=60)
            self.scheduler.start()
            
            logger.info("✅ Scheduler started. Bot will post every 30 minutes.")
            
            # Send initial message
            await self.send_news_update()
            
            # Keep the bot running
            while True:
                await asyncio.sleep(1800)  # Sleep for 30 minutes
                
        except (KeyboardInterrupt, SystemExit):
            logger.info("🛑 Shutting down...")
            self.scheduler.shutdown()
            self.save_sent_articles()
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
            self.scheduler.shutdown()
            self.save_sent_articles()

async def main():
    bot = DiplomacyBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())

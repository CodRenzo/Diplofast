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

    async def fetch_diplomatic_news(self):
        """Fetch diplomatic news with multiple query approaches"""
        try:
            # Try different diplomatic news queries
            queries = [
                # Broad diplomatic terms
                "diplomacy OR \"foreign affairs\" OR \"foreign minister\" OR \"international relations\"",
                # Specific diplomatic events and organizations
                "\"peace talks\" OR embassy OR ambassador OR \"state department\" OR \"diplomatic relations\"",
                # International organizations
                "UN OR \"United Nations\" OR NATO OR EU OR \"European Union\"",
                # Bilateral relations between major countries
                "\"US China\" OR \"India Pakistan\" OR \"Russia Ukraine\" OR \"Israel Palestine\""
            ]
            
            articles = []
            
            for query in queries:
                try:
                    # Get news from last 48 hours for better coverage
                    from_date = (datetime.now() - timedelta(hours=48)).strftime('%Y-%m-%d')
                    
                    news_api_url = f"https://newsapi.org/v2/everything?q={query}&language=en&from={from_date}&sortBy=publishedAt&pageSize=10&apiKey={self.NEWS_API_KEY}"
                    
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        logger.info(f"Fetching news with query: {query}")
                        headers = {'User-Agent': 'DiplomacyBot/1.0'}
                        resp = await client.get(news_api_url, headers=headers)
                        
                        if resp.status_code != 200:
                            continue
                        
                        data = resp.json()
                        
                        if data.get('status') != 'ok':
                            continue
                        
                        new_articles = data.get("articles", [])
                        articles.extend(new_articles)
                        logger.info(f"Query '{query}' returned {len(new_articles)} articles")
                        
                        # If we got enough articles, break early
                        if len(articles) >= 15:
                            break
                            
                except Exception as e:
                    logger.warning(f"Error with query '{query}': {e}")
                    continue
            
            logger.info(f"Total articles from all queries: {len(articles)}")
            
            # If no articles from everything endpoint, try top headlines
            if not articles:
                return await self.fetch_diplomatic_headlines()
            
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
                        
                    # Ensure it's actually diplomatic content
                    title_lower = title.lower()
                    desc_lower = (description or "").lower()
                    
                    diplomatic_terms = [
                        'diplomacy', 'diplomatic', 'foreign affairs', 'foreign minister',
                        'international relations', 'peace talks', 'embassy', 'ambassador',
                        'treaty', 'negotiation', 'summit', 'foreign policy', 'state visit',
                        'un', 'nato', 'eu', 'united nations', 'state department'
                    ]
                    
                    is_diplomatic = any(term in title_lower for term in diplomatic_terms)
                    is_diplomatic |= any(term in desc_lower for term in diplomatic_terms)
                    
                    if is_diplomatic:
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
            
            logger.info(f"Filtered to {len(filtered_articles)} diplomatic articles")
            return filtered_articles[:3]  # Return top 3 articles
                
        except Exception as e:
            logger.error(f"Error fetching diplomatic news: {e}")
            return await self.fetch_diplomatic_headlines()

    async def fetch_diplomatic_headlines(self):
        """Fallback to diplomatic headlines"""
        try:
            # Try different countries for headlines
            countries = ['us', 'gb', 'in', 'cn', 'ru']  # US, UK, India, China, Russia
            
            for country in countries:
                try:
                    news_api_url = f"https://newsapi.org/v2/top-headlines?country={country}&category=general&pageSize=10&apiKey={self.NEWS_API_KEY}"
                    
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        logger.info(f"Fetching headlines from {country}...")
                        headers = {'User-Agent': 'DiplomacyBot/1.0'}
                        resp = await client.get(news_api_url, headers=headers)
                        
                        if resp.status_code != 200:
                            continue
                        
                        data = resp.json()
                        
                        if data.get('status') != 'ok':
                            continue
                        
                        articles = data.get("articles", [])
                        logger.info(f"Headlines from {country}: {len(articles)} articles")
                        
                        # Filter for diplomatic content
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
                                    
                                # Check for diplomatic content
                                title_lower = title.lower()
                                diplomatic_terms = [
                                    'diplomacy', 'foreign', 'international', 'embassy',
                                    'ambassador', 'summit', 'treaty', 'negotiation'
                                ]
                                
                                is_diplomatic = any(term in title_lower for term in diplomatic_terms)
                                
                                if is_diplomatic:
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
                        
                        if filtered_articles:
                            return filtered_articles[:2]
                            
                except Exception as e:
                    continue
            
            return []
                    
        except Exception as e:
            logger.error(f"Error fetching diplomatic headlines: {e}")
            return []

    async def send_news_update(self):
        """Send diplomatic news update to channel"""
        try:
            logger.info("Fetching diplomatic news update...")
            news_items = await self.fetch_diplomatic_news()
            
            if not news_items:
                logger.info("No diplomatic news found")
                return
            
            # Send articles
            for news in news_items:
                try:
                    # Create caption
                    caption = f"🌍 **Diplomatic News Update**\n\n"
                    caption += f"📰 *{news['title']}*\n\n"
                    
                    if news['description'] and len(news['description']) > 20:
                        caption += f"{news['description']}\n\n"
                    
                    caption += f"🔗 [Read Full Article]({news['url']})\n"
                    caption += f"📊 Source: {news['source']}\n"
                    caption += f"#Diplomacy #InternationalRelations"
                    
                    # Send with image if available
                    if news['image_url'] and news['image_url'].startswith('http'):
                        try:
                            await self.bot.send_photo(
                                chat_id=self.CHANNEL_ID,
                                photo=news['image_url'],
                                caption=caption,
                                parse_mode='Markdown'
                            )
                            logger.info(f"✅ Sent diplomatic news from {news['source']}")
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
            logger.info("🚀 Starting Diplomatic News Bot (30-min updates)...")
            
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

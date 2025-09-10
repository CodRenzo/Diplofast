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
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dips.log'),
        logging.StreamHandler()
    ]
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
        
        self.load_sent_articles()

    def load_sent_articles(self):
        try:
            if os.path.exists(self.sent_articles_file):
                with open(self.sent_articles_file, 'r') as f:
                    self.sent_articles = set(json.load(f))
                logger.info(f"Loaded {len(self.sent_articles)} sent articles")
            else:
                self.sent_articles = set()
        except Exception as e:
            logger.error(f"Error loading sent articles: {e}")
            self.sent_articles = set()

    def save_sent_articles(self):
        try:
            with open(self.sent_articles_file, 'w') as f:
                json.dump(list(self.sent_articles), f)
        except Exception as e:
            logger.error(f"Error saving sent articles: {e}")

    def get_article_hash(self, article):
        content = f"{article.get('title', '')}{article.get('url', '')}"
        return hashlib.md5(content.encode()).hexdigest()

    async def fetch_newsapi_news(self):
        """Fetch from NewsAPI"""
        try:
            countries = ["Nepal", "India", "Pakistan", "China", "USA", "Russia", "UK", "Germany", "France", "Japan"]
            country = random.choice(countries)
            
            from_date = (datetime.now() - timedelta(hours=72)).strftime('%Y-%m-%d')
            news_api_url = f"https://newsapi.org/v2/everything?q={country}&language=en&from={from_date}&sortBy=publishedAt&pageSize=5&apiKey={self.NEWS_API_KEY}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Fetching NewsAPI news about {country}...")
                headers = {'User-Agent': 'NewsBot/1.0'}
                resp = await client.get(news_api_url, headers=headers)
                
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('status') == 'ok':
                        return data.get("articles", [])
            return []
        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
            return []

    async def fetch_gdelt_news(self):
        """Fetch from GDELT Project (Public API)"""
        try:
            gdelt_url = "https://api.gdeltproject.org/api/v2/doc/doc?query=sourcecountry:*&mode=ArtList&format=json&maxrecords=10"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("Fetching GDELT news...")
                resp = await client.get(gdelt_url)
                resp.raise_for_status()
                data = resp.json()
                return data.get("articles", [])
        except Exception as e:
            logger.error(f"GDELT error: {e}")
            return []

    async def fetch_rss_news(self):
        """Fetch from public RSS feeds"""
        try:
            # Comprehensive list of public RSS feeds
            rss_feeds = [
                # International News
                "https://rss.cnn.com/rss/edition_world.rss",
                "https://feeds.bbci.co.uk/news/world/rss.xml",
                "https://www.aljazeera.com/xml/rss/all.xml",
                "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best",
                
                # Asian News Sources
                "https://feeds.feedburner.com/ndtvnews-world-news",
                "https://www.thehindu.com/news/international/feeder/default.rss",
                "https://www.dawn.com/feeds/rss/international",
                "https://www.kathmandupost.com/rss",
                
                # US News
                "https://www.npr.org/rss/rss.php?id=1004",
                "https://www.nytimes.com/services/xml/rss/nyt/World.xml",
                "https://www.washingtonpost.com/rss/world/",
                
                # European News
                "https://www.bbc.com/news/world/rss.xml",
                "https://www.theguardian.com/world/rss",
                "https://www.dw.com/rss/rss-en-world-1",
                
                # News Aggregators
                "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
                "https://feeds.feedburner.com/DrudgeReportFeed",
                
                # Diplomatic/Government
                "https://www.state.gov/rss-feed/press-releases/feed/",
                "https://www.un.org/rss/un_news_feeds.xml"
            ]
            
            feed_url = random.choice(rss_feeds)
            # Use RSS to JSON proxy service (public)
            rss_proxy_url = f"https://api.rss2json.com/v1/api.json?rss_url={feed_url}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Fetching RSS news from {feed_url}...")
                resp = await client.get(rss_proxy_url)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("items", [])
            return []
        except Exception as e:
            logger.error(f"RSS fetch error: {e}")
            return []

    async def fetch_public_apis(self):
        """Fetch from other public APIs"""
        try:
            # Public Hacker News API
            hn_url = "https://hacker-news.firebaseio.com/v0/topstories.json?print=pretty"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("Fetching from public APIs...")
                resp = await client.get(hn_url)
                if resp.status_code == 200:
                    story_ids = resp.json()[:5]  # Get top 5 stories
                    stories = []
                    for story_id in story_ids:
                        story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                        story_resp = await client.get(story_url)
                        if story_resp.status_code == 200:
                            story_data = story_resp.json()
                            if story_data.get('url') and story_data.get('title'):
                                stories.append({
                                    'title': story_data['title'],
                                    'url': story_data['url'],
                                    'source': 'Hacker News'
                                })
                    return stories
            return []
        except Exception as e:
            logger.error(f"Public API error: {e}")
            return []

    async def fetch_reddit_news(self):
        """Fetch from public Reddit RSS"""
        try:
            reddit_feeds = [
                "https://www.reddit.com/r/worldnews/.rss",
                "https://www.reddit.com/r/news/.rss",
                "https://www.reddit.com/r/internationalpolitics/.rss",
                "https://www.reddit.com/r/geopolitics/.rss"
            ]
            
            feed_url = random.choice(reddit_feeds)
            rss_proxy_url = f"https://api.rss2json.com/v1/api.json?rss_url={feed_url}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Fetching Reddit news from {feed_url}...")
                resp = await client.get(rss_proxy_url)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("items", [])
            return []
        except Exception as e:
            logger.error(f"Reddit RSS error: {e}")
            return []

    async def fetch_country_news(self):
        """Fetch from all available public APIs"""
        all_articles = []
        
        # Try all public APIs in sequence
        apis = [
            self.fetch_newsapi_news,
            self.fetch_gdelt_news,
            self.fetch_rss_news,
            self.fetch_reddit_news,
            self.fetch_public_apis
        ]
        
        for api_func in apis:
            try:
                articles = await api_func()
                if articles:
                    all_articles.extend(articles)
                    logger.info(f"API returned {len(articles)} articles")
                    if len(all_articles) >= 15:  # Stop if we have enough
                        break
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"API function error: {e}")
                continue
        
        logger.info(f"Total articles from all APIs: {len(all_articles)}")
        
        # Process articles
        filtered_articles = []
        for art in all_articles:
            try:
                title = str(art.get("title") or art.get("headline") or "").strip()
                description = str(art.get("description") or art.get("summary") or art.get("content") or "").strip()
                url = str(art.get("url") or art.get("link") or art.get("guid") or "").strip()
                
                # Get image from various possible fields
                image_url = str(art.get("urlToImage") or art.get("image") or 
                               art.get("thumbnail") or art.get("enclosure") or "").strip()
                
                source = art.get('source', {})
                source_name = ""
                if isinstance(source, dict):
                    source_name = source.get('name', 'Unknown')
                else:
                    source_name = str(source) or art.get("author") or "Unknown"
                
                if not title or not url:
                    continue
                    
                article_hash = self.get_article_hash(art)
                if article_hash in self.sent_articles:
                    continue
                
                filtered_articles.append({
                    'title': title[:300],  # Limit title length
                    'description': description[:500] if description else "",
                    'url': url,
                    'image_url': image_url,
                    'source': source_name[:50],
                    'hash': article_hash
                })
                
            except Exception as e:
                continue
        
        logger.info(f"Final filtered articles: {len(filtered_articles)}")
        return filtered_articles[:5]  # Return top 5 articles

    async def send_news_update(self):
        """Send news update to channel"""
        try:
            logger.info("Fetching news from all public APIs...")
            news_items = await self.fetch_country_news()
            
            if not news_items:
                logger.info("No news found from any API")
                return
            
            for news in news_items:
                try:
                    caption = f"🌍 **Global News Update**\n\n"
                    caption += f"📰 *{news['title']}*\n\n"
                    
                    if news['description'] and len(news['description']) > 20:
                        caption += f"{news['description']}\n\n"
                    
                    caption += f"🔗 [Read Full Article]({news['url']})\n"
                    caption += f"📊 Source: {news['source']}\n"
                    caption += f"#News #GlobalUpdate"
                    
                    if news['image_url'] and news['image_url'].startswith('http'):
                        try:
                            await self.bot.send_photo(
                                chat_id=self.CHANNEL_ID,
                                photo=news['image_url'],
                                caption=caption,
                                parse_mode='Markdown'
                            )
                            logger.info(f"✅ Sent news from {news['source']}")
                        except Exception as e:
                            await self.send_text_news(news, caption)
                    else:
                        await self.send_text_news(news, caption)
                    
                    self.sent_articles.add(news['hash'])
                    self.save_sent_articles()
                    
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error sending news item: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in send_news_update: {e}")

    async def send_text_news(self, news, caption):
        await self.bot.send_message(
            chat_id=self.CHANNEL_ID,
            text=caption,
            parse_mode='Markdown',
            disable_web_page_preview=False
        )
        logger.info(f"✅ Sent text news from {news['source']}")

    async def run(self):
        try:
            logger.info("🚀 Starting Public API News Bot (30-min updates)...")
            
            try:
                me = await self.bot.get_me()
                logger.info(f"Bot connected: @{me.username}")
            except Exception as e:
                logger.error(f"Bot connection failed: {e}")
                return

            self.scheduler.add_job(self.send_news_update, "interval", minutes=30, misfire_grace_time=60)
            self.scheduler.start()
            
            logger.info("✅ Scheduler started. Bot will post every 30 minutes.")
            
            await self.send_news_update()
            
            while True:
                await asyncio.sleep(1800)
                
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

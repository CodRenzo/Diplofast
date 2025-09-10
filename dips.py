import asyncio
import httpx
import json
from datetime import datetime, timedelta

async def debug_newsapi():
    NEWS_API_KEY = "ef68ac134f8d4c8988a7e9e16b5e984c"
    from_date = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d')
    
    query = "diplomacy OR \"foreign affairs\" OR \"state department\" OR \"foreign minister\" OR \"international relations\" OR \"peace talks\" OR \"diplomatic relations\""
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&from={from_date}&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}"
    
    print(f"Request URL: {url}")
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers={'User-Agent': 'DebugBot/1.0'})
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"Total results: {data.get('totalResults', 0)}")
            print(f"Status: {data.get('status')}")
            
            articles = data.get('articles', [])
            print(f"Number of articles: {len(articles)}")
            
            for i, art in enumerate(articles):
                print(f"\n=== Article {i+1} ===")
                print(f"Title: {art.get('title')}")
                print(f"Source: {art.get('source')}")
                print(f"Description: {art.get('description')}")
                print(f"URL: {art.get('url')}")
                print(f"Image: {art.get('urlToImage')}")
        else:
            print(f"Error: {resp.text}")

asyncio.run(debug_newsapi())

import re
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from reppy.robots import Robots
from fastapi.concurrency import run_in_threadpool

# Email regex pattern to match standard email formats
EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

async def get_emails_from_text(text: str) -> list[str]:
    """Extract emails from text using regex."""
    return re.findall(EMAIL_REGEX, text)

async def scrape_with_beautifulsoup(url: str) -> list[str]:
    """Scrape emails from a static webpage using BeautifulSoup."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract emails from mailto links
            mailto_links = [a['href'][7:] for a in soup.find_all('a', href=True) 
                          if a['href'].startswith('mailto:')]
            
            # Extract emails from page text
            text_emails = await get_emails_from_text(soup.get_text())
            
            # Combine and deduplicate emails
            return list(set(mailto_links + text_emails))
    except Exception:
        return []

async def scrape_with_playwright(url: str) -> list[str]:
    """Scrape emails from a JS-rendered webpage using Playwright."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, timeout=30000)  # 30-second timeout
            await page.wait_for_load_state('networkidle')
            content = await page.content()
            
            soup = BeautifulSoup(content, 'html.parser')
            mailto_links = [a['href'][7:] for a in soup.find_all('a', href=True) 
                          if a['href'].startswith('mailto:')]
            text_emails = await get_emails_from_text(soup.get_text())
            
            await browser.close()
            return list(set(mailto_links + text_emails))
    except Exception:
        return []

def is_scraping_allowed(url: str) -> bool:
    """Check if scraping is allowed by robots.txt."""
    try:
        robots_url = f"{url.rstrip('/')}/robots.txt"
        robots = Robots.fetch(robots_url)
        return robots.allowed(url, '*')
    except Exception:
        return True  # Assume allowed if robots.txt is unavailable

async def scrape_emails(url: str) -> dict:
    """Main function to scrape emails from a URL."""
    # Check robots.txt in a thread pool to avoid blocking the event loop
    allowed = await run_in_threadpool(is_scraping_allowed, url)
    if not allowed:
        return {"error": "Scraping not allowed by robots.txt"}
    
    # Try BeautifulSoup first
    emails = await scrape_with_beautifulsoup(url)
    
    # Fallback to Playwright if no emails found
    if not emails:
        emails = await scrape_with_playwright(url)
    
    return {"emails": emails}

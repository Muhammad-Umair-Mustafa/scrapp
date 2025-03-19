import re
from bs4 import BeautifulSoup
import httpx
from playwright.async_api import async_playwright
from urllib.robotparser import RobotFileParser
from fastapi.concurrency import run_in_threadpool

# Regular expression to match email addresses
EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

async def get_emails_from_html(html: str) -> list[str]:
    """Extract emails from HTML content using regex and mailto links."""
    soup = BeautifulSoup(html, 'html.parser')
    # Find mailto links
    mailto_links = [a['href'][7:] for a in soup.find_all('a', href=True) if a['href'].startswith('mailto:')]
    # Find emails in text
    text_emails = re.findall(EMAIL_REGEX, soup.get_text())
    # Combine and deduplicate
    emails = list(set(mailto_links + text_emails))
    return emails

async def scrape_with_beautifulsoup(url: str) -> list[str]:
    """Scrape emails from a static webpage using BeautifulSoup."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            html = response.text
            emails = await get_emails_from_html(html)
            return emails
    except Exception as e:
        print(f"Error in BeautifulSoup scraper: {e}")
        return []

async def scrape_with_playwright(url: str) -> list[str]:
    """Scrape emails from a JS-rendered webpage using Playwright."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state('networkidle')
            html = await page.content()
            emails = await get_emails_from_html(html)
            await browser.close()
            return emails
    except Exception as e:
        print(f"Error in Playwright scraper: {e}")
        return []

def is_scraping_allowed(url: str) -> bool:
    """Check if scraping is allowed by robots.txt."""
    rp = RobotFileParser()
    robots_url = f"{url.rstrip('/')}/robots.txt"
    rp.set_url(robots_url)
    try:
        rp.read()
        return rp.can_fetch('*', url)
    except Exception as e:
        print(f"Error fetching robots.txt: {e}")
        return True  # Assume allowed if robots.txt is unavailable

async def scrape_emails(url: str) -> dict:
    """Main function to scrape emails from a URL."""
    # Check robots.txt in a thread pool to avoid blocking async operations
    allowed = await run_in_threadpool(is_scraping_allowed, url)
    if not allowed:
        return {"error": "Scraping not allowed by robots.txt"}
    
    # Try BeautifulSoup first (faster for static content)
    emails = await scrape_with_beautifulsoup(url)
    if emails:
        return {"emails": emails}
    
    # Fallback to Playwright (handles dynamic content)
    emails = await scrape_with_playwright(url)
    return {"emails": emails}

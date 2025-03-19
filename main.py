from fastapi import FastAPI, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from scraper import scrape_emails
from urllib.parse import urlparse

app = FastAPI(
    title="Email Scraper API",
    description="An API to scrape email addresses from websites."
)

# Rate limiting: 10 requests per minute per IP
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/scrape")
@limiter.limit("10/minute")
async def scrape(url: str):
    """Scrape emails from the provided URL."""
    # Validate URL scheme
    parsed = urlparse(url)
    if parsed.scheme not in ['http', 'https']:
        raise HTTPException(status_code=400, detail="Invalid URL scheme. Use http or https.")
    
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    result = await scrape_emails(url)
    if "error" in result:
        raise HTTPException(status_code=403, detail=result["error"])
    
    return result

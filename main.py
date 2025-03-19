from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from scraper import scrape_emails

# Initialize FastAPI app
app = FastAPI(
    title="Email Scraper API",
    description="An API to scrape email addresses from websites."
)

# Set up rate limiter: 10 requests per minute per IP
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Define request model
class ScrapeRequest(BaseModel):
    url: str

@app.post("/scrape")
@limiter.limit("10/minute")
async def scrape(request: ScrapeRequest):
    """Scrape emails from the provided URL."""
    # Basic URL validation
    if not request.url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    # Call the scraping function
    result = await scrape_emails(request.url)
    if "error" in result:
        raise HTTPException(status_code=403, detail=result["error"])
    
    return result

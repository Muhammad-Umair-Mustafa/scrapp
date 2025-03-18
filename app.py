from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time
import random
import os
import logging

app = Flask(__name__)
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["10 per minute"])

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_google_maps(keyword):
    try:
        with sync_playwright() as p:
            proxy = os.getenv("PROXY")
            browser_args = {
                "headless": True,
                "args": ["--disable-gpu", "--no-sandbox"]
            }
            if proxy:
                browser_args["proxy"] = {"server": proxy}
                logger.info(f"Using proxy: {proxy}")
            else:
                logger.warning("No proxy set, Google may block this request")

            logger.info("Launching browser")
            browser = p.chromium.launch(**browser_args)
            page = browser.new_page()

            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            page.set_viewport_size({"width": 1280, "height": 720})

            logger.info("Navigating to Google Maps")
            try:
                response = page.goto("https://www.google.com/maps", timeout=90000)  # 90s timeout
                if response.status >= 400:
                    logger.error(f"HTTP error: {response.status}")
                    browser.close()
                    return {"error": f"HTTP error {response.status} - possible block or CAPTCHA"}
            except Exception as e:
                logger.error(f"Failed to load Google Maps: {str(e)}")
                browser.close()
                return {"error": f"Failed to load Google Maps: {str(e)}"}

            logger.info("Waiting for network idle")
            page.wait_for_load_state("networkidle", timeout=90000)

            # Check for CAPTCHA or block page
            if "sorry" in page.url.lower() or "captcha" in page.url.lower():
                logger.error("Google CAPTCHA or block detected")
                browser.close()
                return {"error": "Google CAPTCHA or block detected"}

            logger.info("Searching for keyword")
            search_box = page.query_selector('input#searchboxinput')
            if not search_box:
                logger.error("Search box not found")
                browser.close()
                return {"error": "Search box not found on Google Maps"}
            search_box.type(keyword)
            page.query_selector('button#searchbox-searchbutton').click()

            logger.info("Waiting for results")
            page.wait_for_selector('.section-result', timeout=90000)

            businesses = []
            scroll_attempts = 0
            for _ in range(scroll_attempts + 1):
                results = page.query_selector_all('.section-result')
                logger.info(f"Found {len(results)} results")
                for result in results:
                    try:
                        result.click()
                        page.wait_for_timeout(300)

                        name = page.query_selector('.x3AX1-LfntMc-header-title-text') or "N/A"
                        address = page.query_selector('.Io6YTe') or "N/A"
                        phone = page.query_selector('.Io6YTe[href^="tel:"]') or "N/A"
                        website = page.query_selector('.Io6YTe[href^="http"]') or "N/A"

                        businesses.append({
                            "name": name.inner_text() if name != "N/A" else "N/A",
                            "address": address.inner_text() if address != "N/A" else "N/A",
                            "phone": phone.inner_text() if phone != "N/A" else "N/A",
                            "website": website.inner_text() if website != "N/A" else "N/A"
                        })
                    except Exception as e:
                        logger.error(f"Error scraping business: {e}")

                if scroll_attempts > 0:
                    page.evaluate("document.querySelector('.section-layout').scrollTop += 1000")
                    time.sleep(random.uniform(1, 2))

            browser.close()
            logger.info(f"Scraped {len(businesses)} businesses")
            return {"businesses": businesses}
    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
        return {"error": f"Scraping failed: {str(e)}"}

@app.route('/scrape', methods=['GET'])
@limiter.limit("10 per minute")
def scrape_businesses():
    keyword = request.args.get('keyword')
    if not keyword:
        return jsonify({"error": "Keyword is required"}), 400

    data = scrape_google_maps(keyword)
    return jsonify(data)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

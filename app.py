from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time
import random
import os

app = Flask(__name__)
limiter = Limiter(app=app, key_func=get_remote_address)

def scrape_google_maps(keyword):
    try:
        with sync_playwright() as p:
            proxy = os.getenv("PROXY")
            browser_args = {"headless": True}
            if proxy:
                browser_args["proxy"] = {"server": proxy}

            browser = p.chromium.launch(**browser_args)
            page = browser.new_page()

            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            })

            page.goto("https://www.google.com/maps", timeout=60000)
            page.wait_for_load_state("networkidle")

            search_box = page.query_selector('input#searchboxinput')
            if not search_box:
                browser.close()
                return {"error": "Search box not found on Google Maps"}
            search_box.type(keyword)
            page.query_selector('button#searchbox-searchbutton').click()

            page.wait_for_selector('.section-result', timeout=15000)

            businesses = []
            scroll_attempts = 3
            for _ in range(scroll_attempts):
                results = page.query_selector_all('.section-result')
                for result in results:
                    try:
                        result.click()
                        page.wait_for_timeout(1000)

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
                        print(f"Error scraping business: {e}")

                page.evaluate("document.querySelector('.section-layout').scrollTop += 1000")
                time.sleep(random.uniform(2, 4))

            browser.close()
            return {"businesses": businesses}
    except Exception as e:
        return {"error": f"Scraping failed: {str(e)}"}

@app.route('/scrape', methods=['GET'])
@limiter.limit("10 per minute")
def scrape_businesses():
    keyword = request.args.get('keyword')
    if not keyword:
        return jsonify({"error": "Keyword is required"}), 400

    data = scrape_google_maps(keyword)
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

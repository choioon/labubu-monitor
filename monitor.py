import asyncio
from playwright.async_api import async_playwright
from discord_webhook import DiscordWebhook
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

POP_MART_URL = "https://www.popmart.com/gb/products/641/THE-MONSTERS---Exciting-Macaron-Vinyl-Face-Blind-Box"
ALIEXPRESS_URL = "https://www.aliexpress.com/item/1005007966229736.html"

# ---------- Utility ----------

def now():
    return datetime.utcnow().strftime("[%Y-%m-%d %H:%M:%S UTC]")

async def send_discord_alert(message):
    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL, content=message)
    webhook.execute()

async def save_debug_html(page, filename):
    html = await page.content()
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

async def reliable_check(fn, retries=3):
    for attempt in range(retries):
        try:
            return await fn()
        except Exception as e:
            print(now(), f"Attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(3)
    return False

# ---------- Site-Specific Checks (using SELECTORS) ----------

async def is_popmart_in_stock(page):
    await page.goto(POP_MART_URL, timeout=60000)
    try:
        # If the out-of-stock button is present, it's sold out
        await page.wait_for_selector("div.index_btn__w5nKF", timeout=5000)
        print(now(), "Pop Mart: Out-of-stock button detected.")
        return False
    except:
        print(now(), "Pop Mart: Out-of-stock element NOT found — might be in stock!")
        return True

async def is_aliexpress_in_stock(page):
    await page.goto(ALIEXPRESS_URL, timeout=60000)
    try:
        # If the "Find similar items" button is present, it's sold out
        await page.wait_for_selector("button.find-similar--findsimilar--dgsA7rv", timeout=5000)
        print(now(), "AliExpress: 'Find similar items' button detected.")
        return False
    except:
        print(now(), "AliExpress: Button not found — might be in stock!")
        return True

# ---------- Main Monitor ----------

async def monitor():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # --- Pop Mart ---
        print(now(), "Checking Pop Mart...")
        in_stock_popmart = await reliable_check(lambda: is_popmart_in_stock(page))
        if in_stock_popmart:
            await send_discord_alert(f"🔔 Pop Mart restock detected!\n{POP_MART_URL}")
        else:
            print(now(), "Pop Mart: Still sold out.")
            await save_debug_html(page, "popmart_debug.html")

        # --- AliExpress ---
        print(now(), "Checking AliExpress...")
        in_stock_ali = await reliable_check(lambda: is_aliexpress_in_stock(page))
        if in_stock_ali:
            await send_discord_alert(f"🔔 AliExpress restock detected!\n{ALIEXPRESS_URL}")
        else:
            print(now(), "AliExpress: Still sold out.")
            await save_debug_html(page, "aliexpress_debug.html")

        await browser.close()

# ---------- Entry Point ----------

if __name__ == "__main__":
    asyncio.run(monitor())

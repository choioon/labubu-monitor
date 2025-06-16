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
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

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
        # Wait up to 10s for the "Notify me" div to appear
        await page.wait_for_selector("div.index_btn__w5nKF.index_black__RgEgP.index_btnFull__F7k90", timeout=10000)
        text = await page.inner_text("div.index_btn__w5nKF.index_black__RgEgP.index_btnFull__F7k90")
        if "NOTIFY ME WHEN AVAILABLE" in text.upper():
            print(now(), "Pop Mart: Found 'Notify me' — sold out.")
            return False
        else:
            print(now(), "Pop Mart: 'Notify me' text NOT found — assuming in stock.")
            return True
    except Exception:
        # If selector didn't appear, probably button is replaced by Add to Cart, so in stock
        print(now(), "Pop Mart: 'Notify me' div NOT found — assuming in stock.")
        return True




async def is_aliexpress_in_stock(page):
    await page.goto(ALIEXPRESS_URL, timeout=60000)
    try:
        # Wait for the "Find similar items" button or span
        await page.wait_for_selector("button.find-similar--findsimilar--dgsA7rv, span", timeout=10000)
        elements = await page.query_selector_all("button.find-similar--findsimilar--dgsA7rv, span")
        for el in elements:
            text = (await el.inner_text()).strip().lower()
            if text == "find similar items":
                print(now(), "AliExpress: Found 'Find similar items' — sold out.")
                return False
        print(now(), "AliExpress: 'Find similar items' NOT found — assuming in stock.")
        return True
    except Exception:
        # If selector didn't appear, probably "Add to Cart" shows up => in stock
        print(now(), "AliExpress: 'Find similar items' NOT found — assuming in stock.")
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

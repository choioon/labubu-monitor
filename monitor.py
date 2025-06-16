import asyncio
from playwright.async_api import async_playwright
from discord_webhook import DiscordWebhook
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

POP_MART_URL = "https://www.popmart.com/gb/products/641/THE-MONSTERS---Exciting-Macaron-Vinyl-Face-Blind-Box"
ALIEXPRESS_URL = "https://www.aliexpress.com/item/1005008943281649.html?spm=a2g0o.tm1000009216.d0.1.2bf7474cAnXru3&sourceType=562&pvid=90ef70cd-fee7-4341-9da2-40c5a0884771&pdp_ext_f=%7B%22ship_from%22:%22CN%22,%22sku_id%22:%2212000047298030275%22%7D&scm=1007.28480.422277.0&scm-url=1007.28480.422277.0&scm_id=1007.28480.422277.0&pdp_npi=4%40dis%21GBP%21%EF%BF%A135.41%21%EF%BF%A116.29%21%21%21334.69%21153.97%21%40210385a817501013273496253ed012%2112000047298030275%21gsd%21UK%216277881189%21X&channel=sd&aecmd=true"

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
        await page.locator("text=NOTIFY ME WHEN AVAILABLE").first.wait_for(timeout=5000)
        print(now(), "Pop Mart: Out-of-stock text found.")
        return False
    except:
        print(now(), "Pop Mart: Text not found — might be in stock!")
        return True

async def is_aliexpress_in_stock(page):
    await page.goto(ALIEXPRESS_URL, timeout=60000)
    try:
        await page.locator("text=Find similar items").first.wait_for(timeout=5000)
        print(now(), "AliExpress: Out-of-stock text found.")
        return False
    except:
        print(now(), "AliExpress: Text not found — might be in stock!")
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

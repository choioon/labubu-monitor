import asyncio
from playwright.async_api import async_playwright
from discord_webhook import DiscordWebhook
from dotenv import load_dotenv
load_dotenv()
import os

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

POP_MART_URL = "https://www.popmart.com/gb/products/641/THE-MONSTERS---Exciting-Macaron-Vinyl-Face-Blind-Box"
ALIEXPRESS_URL = "https://www.aliexpress.com/item/1005007966229736.html"

async def check_stock(page, url, check_text):
    await page.goto(url, timeout=60000)
    content = await page.content()
    return check_text.lower() not in content.lower()

async def send_discord_alert(message):
    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL, content=message)
    webhook.execute()

async def monitor():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Checking Pop Mart...")
        in_stock_popmart = await check_stock(page, POP_MART_URL, "NOTIFY ME WHEN AVAILABLE")
        if in_stock_popmart:
            await send_discord_alert(f"🔔 Pop Mart restock detected!\n{POP_MART_URL}")
        else:
            print("Pop Mart: Still sold out.")

        print("Checking AliExpress...")
        in_stock_ali = await check_stock(page, ALIEXPRESS_URL, "Find similar items")
        if in_stock_ali:
            await send_discord_alert(f"🔔 AliExpress restock detected!\n{ALIEXPRESS_URL}")
        else:
            print("AliExpress: Still sold out.")

        await browser.close()

async def loop_monitor():
    while True:
        await monitor()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(loop_monitor())

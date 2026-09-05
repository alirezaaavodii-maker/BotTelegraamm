import asyncio, logging
from playwright.async_api import async_playwright
import config as C
from tg import TG
from player import play_run

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)-4s | %(levelname)-7s | %(message)s")
log = logging.getLogger("MAIN")

async def main():
    tg = TG(); await tg.start(); await tg.ensure_joined()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True,
            args=["--no-sandbox","--disable-dev-shm-usage","--disable-gpu"])
        total = 0
        while total < C.TARGET_SCORE:
            try:
                msg, btn = await tg.find_game_message()
                log.info("✅ game message id=%s", msg.id)
                url = await tg.get_webview_url(msg, btn)
                total += await play_run(browser, url)
                log.info("session total=%s", total)
            except Exception as e:
                log.exception("loop error: %s", e)
            await asyncio.sleep(C.RUN_PAUSE)
        await browser.close()
    await tg.client.send_message("me", f"🎯 LumberJack finished: {total}")
    log.info("🎯 target reached (%s). staying alive…", total)
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())

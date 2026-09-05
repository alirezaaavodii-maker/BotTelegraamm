import asyncio
import logging
from playwright.async_api import async_playwright
import config as C
from tg import TG
from player import play_run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-4s | %(levelname)-7s | %(message)s",
)
log = logging.getLogger("MAIN")


async def main():
    tg = TG()
    
    # تلاش برای اتصال با retry
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await tg.start()
            break
        except RuntimeError as e:
            if "SESSION_INVALID" in str(e):
                log.error("❌ Session باطل است. برنامه متوقف می‌شود.")
                log.error("❌ یک Session جدید بساز و در Railway Variables بذار")
                log.error("❌ سپس Railway را Redeploy کن")
                return
            elif "2FA_REQUIRED" in str(e):
                log.error("❌ اکانت شما Two-Factor Authentication دارد")
                return
            else:
                log.warning("⚠️ تلاش %d/%d برای اتصال...", attempt + 1, max_retries)
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(5)
    
    await tg.ensure_joined()

    total = 0
    async with async_playwright() as pw:
        while total < C.TARGET_SCORE:
            browser = None
            try:
                msg, btn = await tg.find_game_message()
                log.info("✅ game message id=%s", msg.id)

                url = await tg.get_webview_url(msg, btn)

                browser = await pw.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                )
                log.info("✅ browser launched")

                got = await play_run(browser, url, client=tg.client)
                total += got
                log.info("🏁 run=%s | total=%s / %s", got, total, C.TARGET_SCORE)

                if got == 0:
                    log.warning("⚠️ score=0 — retry in %ss", C.ERROR_PAUSE)
                    await asyncio.sleep(C.ERROR_PAUSE)
                else:
                    await asyncio.sleep(C.RUN_PAUSE)

            except Exception as e:
                log.exception("loop error: %s", e)
                await asyncio.sleep(C.ERROR_PAUSE)
            finally:
                if browser:
                    try:
                        await browser.close()
                    except Exception:
                        pass

    try:
        await tg.client.send_message("me", f"🎯 LumberJack finished: {total}")
    except Exception as e:
        log.warning("notify failed: %s", e)

    log.info("🎯 target reached (%s). staying alive…", total)
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())

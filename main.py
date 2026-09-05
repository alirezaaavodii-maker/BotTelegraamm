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

ERROR_PAUSE = getattr(C, "ERROR_PAUSE", 20)


async def main():
    tg = TG()
    await tg.start()
    await tg.ensure_joined()

    total = 0
    async with async_playwright() as pw:
        while total < C.TARGET_SCORE:
            browser = None
            try:
                # ۱) پیدا کردن پیام بازی (از طریق پیام پین‌شده)
                msg, btn = await tg.find_game_message()
                log.info("✅ game message id=%s", msg.id)

                # ۲) کلیک روی دکمه شیشه‌ای و گرفتن URL رسمی Mini App
                url = await tg.get_webview_url(msg, btn)

                # ۳) باز کردن مرورگر هدلس و اجرای خودکار بازی
                browser = await pw.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                )
                log.info("✅ browser launched")

                got = await play_run(browser, url)
                total += got
                log.info("🏁 run=%s | total=%s / %s", got, total, C.TARGET_SCORE)

                if got == 0:
                    log.warning("⚠️ score=0 — retry in %ss", ERROR_PAUSE)
                    await asyncio.sleep(ERROR_PAUSE)
                else:
                    await asyncio.sleep(C.RUN_PAUSE)

            except Exception as e:
                log.exception("loop error: %s", e)
                await asyncio.sleep(ERROR_PAUSE)
            finally:
                if browser:
                    try:
                        await browser.close()
                    except Exception:
                        pass

    # اطلاع‌رسانی پایان کار به Saved Messages خودت
    try:
        await tg.client.send_message("me", f"🎯 LumberJack finished: {total}")
    except Exception as e:
        log.warning("notify failed: %s", e)

    log.info("🎯 target reached (%s). staying alive…", total)
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import io
import logging
import random
import numpy as np
from PIL import Image
import config as C
from perception import analyze, play_screen
from strategy import decide

log = logging.getLogger("GAME")

UA = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")

MOCK_JS = """
if (!window.Telegram) {
  const q = new URLSearchParams(location.search);
  window.Telegram = {
    WebApp: {
      initData: decodeURIComponent(q.get('tgWebAppData') || ''),
      initDataUnsafe: {},
      platform: 'android',
      version: '7.2',
      colorScheme: 'light',
      isExpanded: true,
      viewportStableHeight: innerHeight,
      ready() {},
      expand() {},
      close() { console.log('[MOCK] close() called'); },
      sendData(data) { console.log('[MOCK] sendData:', data); },
      MainButton: { show() {}, hide() {}, onClick() {}, offClick() {} },
      BackButton: { show() {}, hide() {}, onClick() {}, offClick() {} },
      HapticFeedback: { impactOccurred() {}, notificationOccurred() {} },
      onEvent() {},
      offEvent() {}
    }
  };
}
"""


async def _send_shot(client, a, score):
    """ارسال اسکرین‌شات به Saved Messages"""
    if not C.SHOT_UPLOAD or client is None:
        return
    try:
        img = Image.fromarray(a)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=70)
        buf.seek(0)
        buf.name = f"lj_{score}.jpg"
        await client.send_file("me", buf, caption=f"LumberJack @ {score}")
        log.info("📸 shot sent for score=%s", score)
    except Exception as e:
        log.warning("shot send failed: %s", e)


async def play_run(browser, url, client=None):
    page = await browser.new_page(viewport={"width": C.VIEW_W, "height": C.VIEW_H}, user_agent=UA)

    def on_request(req):
        if "tbot.xyz" in req.url or "api" in req.url.lower():
            log.info(" REQUEST %s %s", req.method, req.url)

    def on_response(resp):
        if "tbot.xyz" in resp.url or "api" in resp.url.lower():
            log.info("📥 RESPONSE %s %s [%s]", resp.request.method, resp.url, resp.status)

    page.on("request", on_request)
    page.on("response", on_response)

    def on_console(msg):
        text = msg.text
        if any(k in text.lower() for k in ["error", "fail", "send", "mock", "game over", "restart"]):
            log.info("📜 CONSOLE [%s]: %s", msg.type, text[:300])

    page.on("console", on_console)

    await page.add_init_script(MOCK_JS)
    total, side, miss = 0, "L", 0
    consecutive_resets = 0
    last_score_check = 0
    game_started = False

    try:
        log.info(" loading game url...")
        await page.goto(url, wait_until="load", timeout=60000)
        await page.wait_for_timeout(4000)
        log.info("✅ mini app loaded")

        initial_shot = np.array(Image.open(io.BytesIO(await page.screenshot())).convert("RGB"))
        await _send_shot(client, initial_shot, 0)

        while total < C.TARGET_SCORE:
            a = np.array(Image.open(io.BytesIO(await page.screenshot())).convert("RGB"))

            # تشخیص صفحه شروع
            is_play = play_screen(a, C)
            if is_play:
                consecutive_resets += 1
                if consecutive_resets > 5:
                    log.warning("⚠️ too many consecutive resets (%s), may be detected as bot", consecutive_resets)
                    await asyncio.sleep(random.uniform(3.0, 5.0))
                else:
                    log.info("▶️  play screen detected (consecutive=%s), clicking start...", consecutive_resets)
                    await page.mouse.click(C.VIEW_W * C.PLAY_X, C.VIEW_H * C.PLAY_Y)
                    await asyncio.sleep(random.uniform(2.0, 3.5))
                    game_started = True
                continue
            else:
                consecutive_resets = 0
                if not game_started:
                    log.info("🎮 game in progress, waiting for first click...")
                    game_started = True

            st = analyze(a, C)
            if not st["ok"]:
                miss += 1
                log.warning("⚠️ analyze failed (miss=%s): dL=%s dR=%s", miss, st.get("dL", "?"), st.get("dR", "?"))
                if miss > 15:
                    log.error("❌ too many misses (%s), stopping run", miss)
                    break
                await page.wait_for_timeout(400)
                continue

            miss = 0
            side = decide(st, side)
            x = C.LEFT_X if side == "L" else C.RIGHT_X
            
            # کلیک با jitter بیشتر
            jitter_x = random.uniform(-0.03, 0.03)
            jitter_y = random.uniform(-0.02, 0.02)
            await page.mouse.click(
                C.VIEW_W * (x + jitter_x), 
                C.VIEW_H * (C.TAP_Y + jitter_y)
            )
            total += 1

            # لاگ هر 20 کلیک
            if total % 20 == 0:
                log.info("score=%s side=%s dL=%s dR=%s resets=%s ok=%s", 
                         total, side, st["dL"], st["dR"], consecutive_resets, st["ok"])
                
                if total % 100 == 0:
                    await _send_shot(client, a, total)

            # delay متغیر (کندتر)
            delay = random.uniform(0.25, 0.45)
            await asyncio.sleep(delay)

    except Exception as e:
        log.exception("run error: %s", e)
    finally:
        await page.close()

    log.info("🏁 run finished with %s clicks, %s consecutive resets", total, consecutive_resets)
    return total

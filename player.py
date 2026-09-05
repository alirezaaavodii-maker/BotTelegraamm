import asyncio
import io
import logging
import random
import numpy as np
import httpx
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
    if not C.SHOT_UPLOAD or client is None:
        return
    try:
        buf = io.BytesIO()
        Image.fromarray(a).save(buf, "JPEG", quality=70)
        buf.name = f"lj_{score}.jpg"
        await client.send_file("me", buf, caption=f"LumberJack shot @ {score}")
    except Exception as e:
        log.warning("shot send failed: %s", e)


async def play_run(browser, url, client=None):
    page = await browser.new_page(viewport={"width": C.VIEW_W, "height": C.VIEW_H}, user_agent=UA)

    # ★ لاگ کردن همه‌ی درخواست‌های شبکه
    def on_request(req):
        if "tbot.xyz" in req.url or "api" in req.url.lower():
            log.info("🌐 REQUEST %s %s", req.method, req.url)
    
    def on_response(resp):
        if "tbot.xyz" in resp.url or "api" in resp.url.lower():
            log.info("📥 RESPONSE %s %s [%s]", resp.request.method, resp.url, resp.status)
    
    def on_request_failed(req):
        log.error("❌ REQUEST FAILED %s %s: %s", req.method, req.url, req.failure)

    page.on("request", on_request)
    page.on("response", on_response)
    page.on("requestfailed", on_request_failed)

    # ★ لاگ کردن console پیام‌ها (خطاها و ارسال داده‌ها)
    def on_console(msg):
        text = msg.text
        if "error" in text.lower() or "fail" in text.lower() or "send" in text.lower() or "mock" in text.lower():
            log.info("📜 CONSOLE [%s]: %s", msg.type, text[:200])
    
    page.on("console", on_console)

    # ★ لاگ کردن WebSocket frames
    def on_websocket(ws):
        log.info("🔌 WEBSOCKET OPEN: %s", ws.url)
        
        def on_ws_frame(payload, is_sent):
            direction = "→" if is_sent else "←"
            log.info("🔌 WS %s %s: %s", direction, ws.url, payload[:150] if isinstance(payload, str) else "(binary)")
        
        ws.on("framesent", lambda e: on_ws_frame(e.payload, True))
        ws.on("framereceived", lambda e: on_ws_frame(e.payload, False))
        ws.on("close", lambda: log.warning("🔌 WEBSOCKET CLOSED: %s", ws.url))

    page.on("websocket", on_websocket)

    await page.add_init_script(MOCK_JS)
    total, side, miss = 0, "L", 0

    try:
        log.info("🌍 loading game url...")
        await page.goto(url, wait_until="load", timeout=60000)
        await page.wait_for_timeout(4000)
        log.info("✅ mini app loaded")

        # اسکرین‌شات اولیه برای تأیید بارگذاری
        initial_shot = np.array(Image.open(io.BytesIO(await page.screenshot())).convert("RGB"))
        await _send_shot(client, initial_shot, 0)

        while total < C.TARGET_SCORE:
            a = np.array(Image.open(io.BytesIO(await page.screenshot())).convert("RGB"))

            if play_screen(a, C):
                log.info("▶️  play screen detected, clicking start...")
                await page.mouse.click(C.VIEW_W * C.PLAY_X, C.VIEW_H * C.PLAY_Y)
                miss = 0
                await page.wait_for_timeout(1200)
                continue

            st = analyze(a, C)
            if not st["ok"]:
                miss += 1
                if miss > 20:
                    log.warning("❌ too many misses, stopping run")
                    break
                await page.wait_for_timeout(300)
                continue

            miss = 0
            side = decide(st, side)
            x = C.LEFT_X if side == "L" else C.RIGHT_X
            await page.mouse.click(C.VIEW_W * x, C.VIEW_H * C.TAP_Y)
            total += 1

            if total % 20 == 0:
                log.info("score=%s side=%s dL=%s dR=%s", total, side, st["dL"], st["dR"])
                if total % 50 == 0:
                    await _send_shot(client, a, total)

            await asyncio.sleep(max(.03, C.TAP_DELAY + random.uniform(-C.TAP_JITTER, C.TAP_JITTER)))

    except Exception as e:
        log.exception("run error: %s", e)
    finally:
        await page.close()

    log.info("🏁 run finished with %s clicks", total)
    return total

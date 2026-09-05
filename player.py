import asyncio, io, logging, random
import numpy as np, httpx
from PIL import Image
import config as C
from perception import analyze, play_screen
from strategy import decide
log = logging.getLogger("GAME")

UA = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
MOCK_JS = """
if (!window.Telegram) { const q = new URLSearchParams(location.search);
 window.Telegram = { WebApp: { initData: decodeURIComponent(q.get('tgWebAppData')||''),
  platform:'android', version:'7.2', colorScheme:'light', isExpanded:true,
  viewportStableHeight: innerHeight, ready(){}, expand(){}, close(){}, sendData(){},
  MainButton:{show(){},hide(){},onClick(){},offClick(){}}, BackButton:{show(){},hide(){},onClick(){},offClick(){}},
  HapticFeedback:{impactOccurred(){},notificationOccurred(){}}, onEvent(){}, offEvent(){}, }}; }
"""

async def _upload(a):
    if not C.SHOT_UPLOAD: return
    try:
        img = Image.fromarray(a); buf = io.BytesIO(); img.save(buf, "JPEG", quality=60)
        r = await httpx.AsyncClient().post("https://0x0.st", files={"file": ("s.jpg", buf.getvalue())}, timeout=15)
        log.info("📸 shot: %s", r.text.strip())
    except Exception as e: log.warning("shot upload: %s", e)

async def play_run(browser, url):
    page = await browser.new_page(viewport={"width":C.VIEW_W,"height":C.VIEW_H}, user_agent=UA)
    await page.add_init_script(MOCK_JS)
    total, side, miss = 0, "L", 0
    try:
        await page.goto(url, wait_until="load", timeout=60000)
        await page.wait_for_timeout(3000)
        log.info("✅ mini app loaded")
        while total < C.TARGET_SCORE:
            a = np.array(Image.open(io.BytesIO(await page.screenshot())).convert("RGB"))
            if play_screen(a, C):
                await page.mouse.click(C.VIEW_W*C.PLAY_X, C.VIEW_H*C.PLAY_Y)
                miss = 0; await page.wait_for_timeout(900); continue
            st = analyze(a, C)
            if not st["ok"]:
                miss += 1
                if miss > 20: break
                await page.wait_for_timeout(300); continue
            miss = 0; side = decide(st, side)
            x = C.LEFT_X if side=="L" else C.RIGHT_X
            await page.mouse.click(C.VIEW_W*x, C.VIEW_H*C.TAP_Y)
            total += 1
            if total % 50 == 0:
                log.info("score=%s side=%s dL=%s dR=%s", total, side, st["dL"], st["dR"])
                await _upload(a)
            await asyncio.sleep(max(.03, C.TAP_DELAY + random.uniform(-C.TAP_JITTER, C.TAP_JITTER)))
    except Exception as e:
        log.exception("run error: %s", e)
    finally:
        await page.close()
    return total

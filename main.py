import asyncio
import os

from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession
from playwright.async_api import async_playwright


API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION = os.environ["TG_SESSION"]

CHAT_ID = int(os.getenv("TG_CHAT_ID", "-1004467330949"))
MESSAGE_ID = int(os.getenv("TG_MESSAGE_ID", "149595"))

TARGET_SCORE = int(os.getenv("TARGET_SCORE", "2000"))
MAX_SECONDS = int(os.getenv("MAX_SECONDS", "900"))


async def get_mini_app_url(client):
    message = await client.get_messages(CHAT_ID, ids=MESSAGE_ID)

    if not message or not message.reply_markup:
        raise RuntimeError("پیام LumberJack یا دکمه پیدا نشد.")

    for row in message.reply_markup.rows:
        for button in row.buttons:

            if isinstance(button, types.KeyboardButtonWebView):
                if button.text.lower() == "play lumberjack!":
                    result = await client(
                        functions.messages.RequestWebViewRequest(
                            peer=CHAT_ID,
                            bot=message.peer_id,
                            platform="android",
                            url=button.url,
                            from_bot_menu=False,
                            start_param=None,
                            theme_params=None,
                        )
                    )

                    return result.url

    raise RuntimeError("دکمه Play LumberJack! پیدا نشد.")


async def main():
    print("Connecting to Telegram...")

    client = TelegramClient(
        StringSession(SESSION),
        API_ID,
        API_HASH,
    )

    await client.start()

    print("Getting LumberJack Mini App URL...")
    url = await get_mini_app_url(client)

    print("Mini App URL received.")

    async with async_playwright() as pw:

        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        page = await browser.new_page(
            viewport={
                "width": 390,
                "height": 844,
            }
        )

        await page.goto(url, wait_until="domcontentloaded")

        await page.wait_for_timeout(3000)

        print("Mini App opened.")

        await play_game(page)

        await browser.close()

    await client.disconnect()


async def play_game(page):
    start_time = asyncio.get_event_loop().time()

    print("Searching for game controls...")

    # First try normal HTML buttons.
    left_selectors = [
        'button:has-text("←")',
        'button:has-text("Left")',
        '[aria-label*="left" i]',
        '[data-direction="left"]',
    ]

    right_selectors = [
        'button:has-text("→")',
        'button:has-text("Right")',
        '[aria-label*="right" i]',
        '[data-direction="right"]',
    ]

    left = None
    right = None

    for selector in left_selectors:
        try:
            locator = page.locator(selector).first
            if await locator.count():
                left = locator
                break
        except Exception:
            pass

    for selector in right_selectors:
        try:
            locator = page.locator(selector).first
            if await locator.count():
                right = locator
                break
        except Exception:
            pass

    # If HTML buttons aren't available, use screen coordinates.
    while True:

        elapsed = asyncio.get_event_loop().time() - start_time

        if elapsed >= MAX_SECONDS:
            print("Maximum runtime reached.")
            return

        score = await read_score(page)

        if score is not None:
            print("Score:", score)

            if score >= TARGET_SCORE:
                print("TARGET REACHED:", score)
                return

        direction = await detect_branch(page)

        if direction == "left":
            # Branch on left => chop right.
            if right:
                await right.click()
            else:
                await page.mouse.click(285, 735)

        elif direction == "right":
            # Branch on right => chop left.
            if left:
                await left.click()
            else:
                await page.mouse.click(105, 735)

        await page.wait_for_timeout(70)


async def detect_branch(page):
    """
    Detect branch side from the game canvas/screenshot.

    Returns:
        left
        right
        None
    """

    image = await page.screenshot(type="png")

    import cv2
    import numpy as np

    data = np.frombuffer(image, dtype=np.uint8)

    frame = cv2.imdecode(data, cv2.IMREAD_COLOR)

    if frame is None:
        return None

    height, width = frame.shape[:2]

    # Upper-middle game area.
    y1 = int(height * 0.25)
    y2 = int(height * 0.60)

    roi = frame[y1:y2, :]

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # Brown branch detection.
    mask1 = cv2.inRange(
        hsv,
        np.array([5, 45, 35]),
        np.array([30, 255, 220]),
    )

    mask2 = cv2.inRange(
        hsv,
        np.array([0, 25, 25]),
        np.array([35, 255, 180]),
    )

    mask = cv2.bitwise_or(mask1, mask2)

    kernel = np.ones((5, 5), np.uint8)

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel,
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel,
    )

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    center = width / 2

    left_score = 0
    right_score = 0

    for contour in contours:

        x, y, w, h = cv2.boundingRect(contour)

        area = cv2.contourArea(contour)

        if area < 100:
            continue

        contour_center = x + w / 2

        if contour_center < center:
            left_score = max(
                left_score,
                center - (x + w),
            )

        else:
            right_score = max(
                right_score,
                x - center,
            )

    if left_score > 25 and left_score > right_score * 1.15:
        return "left"

    if right_score > 25 and right_score > left_score * 1.15:
        return "right"

    return None


async def read_score(page):
    """
    Attempts to read a visible score from the Mini App.
    """

    try:

        text = await page.locator("body").inner_text()

        import re

        numbers = re.findall(
            r"\b\d{1,5}\b",
            text,
        )

        if numbers:
            values = [int(x) for x in numbers]

            # Ignore tiny unrelated numbers.
            values = [
                x for x in values
                if x >= 0
            ]

            if values:
                return max(values)

    except Exception:
        pass

    return None


if __name__ == "__main__":
    asyncio.run(main())


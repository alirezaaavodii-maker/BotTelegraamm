import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import KeyboardButtonWebView, KeyboardButtonSimpleWebView
from telethon.tl.functions.messages import (RequestWebViewRequest,
    RequestSimpleWebViewRequest, ImportChatInviteRequest)
import config as C
log = logging.getLogger("TG")

class TG:
    def __init__(self):
        self.client = TelegramClient(StringSession(C.SESSION_STRING), C.API_ID, C.API_HASH)

    async def start(self):
        await self.client.start()
        me = await self.client.get_me()
        log.info("✅ connected as %s (id=%s)", me.username or me.first_name, me.id)

    async def ensure_joined(self):
        try:
            entity = await self.client.get_entity(C.GAME_CHAT)
            log.info("✅ chat entity: %s (id=%s)",
                     getattr(entity, 'title', None) or getattr(entity, 'username', None),
                     getattr(entity, 'id', '?'))
        except Exception as e:
            log.warning("get_entity failed: %s → trying invite hash", e)
            try:
                await self.client(ImportChatInviteRequest(hash=C.INVITE_HASH))
                log.info("✅ joined via invite")
            except Exception as e2:
                log.error("❌ join failed: %s", e2)

    async def find_game_message(self):
        candidates = []
        count = 0
        async for msg in self.client.iter_messages(C.GAME_CHAT, limit=300):
            count += 1
            mk = msg.reply_markup
            if not mk:
                continue

            # لاگ کردن همه‌ی پیام‌های دارای دکمه
            log.info("🔍 MSG id=%s text=%r", msg.id, (msg.text or "")[:100])
            for row in mk.rows:
                for b in row.buttons:
                    is_web = isinstance(b, (KeyboardButtonWebView, KeyboardButtonSimpleWebView))
                    log.info("   └─ BTN text=%r is_webapp=%s", b.text, is_web)
                    if is_web:
                        candidates.append((msg, b))
                        if C.BUTTON_TEXT.lower() in (b.text or "").lower():
                            log.info("✅ EXACT match found: msg_id=%s btn=%r", msg.id, b.text)
                            return msg, b

        log.warning("⚠️ scanned %d messages, no exact match for '%s'", count, C.BUTTON_TEXT)

        # اگر هیچ دکمه‌ی وبی پیدا نشد → یعنی عضو چت نیستیم یا چت اشتباهه
        if not candidates:
            log.error("❌ NO web buttons at all in this chat! Either GAME_CHAT is wrong or bot is not in chat.")
            raise RuntimeError("game button not found - chat may be wrong or not joined")

        # اگر دکمه‌های وب هست ولی اسمش فرق داره، لیستش می‌کنیم
        log.warning("📋 found %d web buttons, none matched '%s':", len(candidates), C.BUTTON_TEXT)
        for msg, b in candidates:
            log.warning("   → msg_id=%s  btn_text=%r", msg.id, b.text)

        # fallback: استفاده از اولین دکمه‌ی وب (اگر فقط یکی بود، احتمالاً همونه)
        if len(candidates) == 1:
            msg, b = candidates[0]
            log.info("🔄 using only available web button: msg=%s btn=%r", msg.id, b.text)
            return msg, b

        raise RuntimeError(f"game button not found. Found: {[b.text for _,b in candidates]}")

    async def get_webview_url(self, msg, b):
        peer = await self.client.get_input_entity(C.GAME_CHAT)
        if isinstance(b, KeyboardButtonWebView):
            r = await self.client(RequestWebViewRequest(
                peer=peer, msg_id=msg.id, button=b, platform="android"))
        else:
            r = await self.client(RequestSimpleWebViewRequest(
                peer=peer, button=b, platform="android"))
        log.info("✅ webview url obtained")
        return r.url

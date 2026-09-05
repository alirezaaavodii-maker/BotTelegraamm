import logging
from telethon import TelegramClient, functions
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
        try: await self.client.get_entity(C.GAME_CHAT)
        except Exception:
            try: await self.client(ImportChatInviteRequest(hash=C.INVITE_HASH)); log.info("✅ joined via invite")
            except Exception as e: log.warning("join: %s", e)
    async def find_game_message(self):
        async for msg in self.client.iter_messages(C.GAME_CHAT, limit=120):
            mk = msg.reply_markup
            if not mk: continue
            for row in mk.rows:
                for b in row.buttons:
                    if isinstance(b,(KeyboardButtonWebView,KeyboardButtonSimpleWebView)) \
                       and C.BUTTON_TEXT.lower() in (b.text or "").lower():
                        return msg, b
        raise RuntimeError("game button not found")
    async def get_webview_url(self, msg, b):
        peer = await self.client.get_input_entity(C.GAME_CHAT)
        if isinstance(b, KeyboardButtonWebView):
            r = await self.client(RequestWebViewRequest(peer=peer, msg_id=msg.id, button=b, platform="android"))
        else:
            r = await self.client(RequestSimpleWebViewRequest(peer=peer, button=b, platform="android"))
        log.info("✅ webview url obtained")
        return r.url

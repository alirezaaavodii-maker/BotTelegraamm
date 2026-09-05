import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import KeyboardButtonWebView, KeyboardButtonSimpleWebView
from telethon.tl.functions.messages import (RequestWebViewRequest,
    RequestSimpleWebViewRequest, ImportChatInviteRequest, GetFullChatRequest)
from telethon.tl.functions.channels import GetFullChannelRequest
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
            await self.client.get_entity(C.GAME_CHAT)
        except Exception:
            try:
                await self.client(ImportChatInviteRequest(hash=C.INVITE_HASH))
                log.info("✅ joined via invite")
            except Exception as e:
                log.warning("join: %s", e)

    @staticmethod
    def _web_buttons(msg):
        out = []
        mk = msg.reply_markup
        if not mk: return out
        for row in mk.rows:
            for b in row.buttons:
                if isinstance(b, (KeyboardButtonWebView, KeyboardButtonSimpleWebView)):
                    out.append(b)
        return out

    async def _pinned_message(self):
        """پیام پین‌شده‌ی گروه را مستقیم می‌گیرد (همون پیام بازی!)"""
        try:
            peer = await self.client.get_input_entity(C.GAME_CHAT)
            pid = None
            if hasattr(peer, "channel_id"):
                full = await self.client(GetFullChannelRequest(peer))
                pid = getattr(full.full_chat, "pinned_msg_id", None)
            elif hasattr(peer, "chat_id"):
                full = await self.client(GetFullChatRequest(peer.chat_id))
                pid = getattr(full.full_chat, "pinned_msg_id", None)
            if pid:
                log.info("📌 pinned msg id=%s", pid)
                return await self.client.get_messages(C.GAME_CHAT, ids=pid)
        except Exception as e:
            log.warning("pinned lookup failed: %s", e)
        return None

    async def find_game_message(self):
        # ۱) پیام پین‌شده (مطمئن‌ترین راه)
        msg = await self._pinned_message()
        if msg:
            for b in self._web_buttons(msg):
                log.info("✅ game button found in PINNED msg (id=%s, btn=%r)", msg.id, b.text)
                return msg, b
        # ۲) آیدی مستقیم پیام (زاپاس)
        if C.GAME_MSG_ID:
            msg = await self.client.get_messages(C.GAME_CHAT, ids=C.GAME_MSG_ID)
            if msg:
                for b in self._web_buttons(msg):
                    log.info("✅ game button found via GAME_MSG_ID (id=%s, btn=%r)", msg.id, b.text)
                    return msg, b
        # ۳) اسکن محدود (زاپاس آخر)
        async for msg in self.client.iter_messages(C.GAME_CHAT, limit=200):
            for b in self._web_buttons(msg):
                if C.BUTTON_TEXT.lower() in (b.text or "").lower():
                    return msg, b
        raise RuntimeError("game button not found (pinned/ID/scan all failed)")

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

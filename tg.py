import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import (KeyboardButtonWebView, KeyboardButtonSimpleWebView,
                               KeyboardButtonGame)
from telethon.tl.functions.messages import (RequestWebViewRequest,
    RequestSimpleWebViewRequest, ImportChatInviteRequest, GetFullChatRequest)
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.errors import AuthKeyDuplicatedError, SessionPasswordNeededError
import config as C

log = logging.getLogger("TG")


class TG:
    def __init__(self):
        self.client = TelegramClient(StringSession(C.SESSION_STRING), C.API_ID, C.API_HASH)

    async def start(self):
        try:
            await self.client.start()
            me = await self.client.get_me()
            log.info("✅ connected as %s (id=%s)", me.username or me.first_name, me.id)
        except AuthKeyDuplicatedError:
            log.error("❌ SESSION STRING باطل شده! یک Session جدید بساز و در Railway بذار")
            log.error(" راهنما: فایل generate_session.py را لوکال اجرا کن")
            raise RuntimeError("SESSION_INVALID")
        except SessionPasswordNeededError:
            log.error("❌ اکانت شما Two-Factor Authentication دارد. باید password بدهید")
            raise RuntimeError("2FA_REQUIRED")
        except Exception as e:
            log.error("❌ خطا در اتصال: %s", e)
            raise

    async def ensure_joined(self):
        try:
            await self.client.get_entity(C.GAME_CHAT)
        except Exception:
            try:
                await self.client(ImportChatInviteRequest(hash=C.INVITE_HASH))
                log.info("✅ joined via invite")
            except Exception as e:
                log.warning("join: %s", e)

    def _find_game_button(self, msg):
        mk = msg.reply_markup
        if not mk:
            return None
        for ri, row in enumerate(mk.rows):
            for ci, b in enumerate(row.buttons):
                if isinstance(b, (KeyboardButtonWebView,
                                  KeyboardButtonSimpleWebView,
                                  KeyboardButtonGame)):
                    return ri, ci, b
        return None

    async def _pinned_message(self):
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
        msg = await self._pinned_message()
        if msg:
            if msg.reply_markup:
                log.info("pinned buttons: %s",
                         [f"{type(b).__name__}:{(b.text or '')[:30]}"
                          for row in msg.reply_markup.rows for b in row.buttons])
            found = self._find_game_button(msg)
            if found:
                log.info("✅ game button in PINNED msg: type=%s text=%r",
                         type(found[2]).__name__, found[2].text)
                return msg, found

        if C.GAME_MSG_ID:
            msg = await self.client.get_messages(C.GAME_CHAT, ids=C.GAME_MSG_ID)
            if msg:
                found = self._find_game_button(msg)
                if found:
                    log.info("✅ game button via GAME_MSG_ID: type=%s", type(found[2]).__name__)
                    return msg, found

        async for msg in self.client.iter_messages(C.GAME_CHAT, limit=200):
            found = self._find_game_button(msg)
            if found:
                return msg, found

        raise RuntimeError("game button not found (pinned/ID/scan all failed)")

    async def get_webview_url(self, msg, info):
        ri, ci, b = info
        peer = await self.client.get_input_entity(C.GAME_CHAT)

        if isinstance(b, KeyboardButtonWebView):
            r = await self.client(RequestWebViewRequest(
                peer=peer, msg_id=msg.id, button=b, platform="android"))
            log.info("✅ webview url obtained")
            return r.url

        if isinstance(b, KeyboardButtonSimpleWebView):
            r = await self.client(RequestSimpleWebViewRequest(
                peer=peer, button=b, platform="android"))
            log.info("✅ simple webview url obtained")
            return r.url

        flat = sum(len(row.buttons) for row in msg.reply_markup.rows[:ri]) + ci
        r = await msg.click(flat)
        url = getattr(r, "url", None)
        if not url:
            log.error("❌ game click returned no url: %s", r)
            raise RuntimeError("game button clicked but no url returned")
        log.info("✅ GAME url obtained: %.80s...", url)
        return url

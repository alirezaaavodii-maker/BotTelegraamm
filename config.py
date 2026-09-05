import os
def s(n,d=""): return os.getenv(n,d)
def i(n,d=0): return int(os.getenv(n,str(d)))
def f(n,d=0.0): return float(os.getenv(n,str(d)))

# --- اتصال تلگرام (فقط در Variables رای‌وی، نه GitHub)
API_ID   = i("API_ID", 26998048)
API_HASH = s("API_HASH", "2b3b68c21fc2dc691bc4f54fad659141")
SESSION_STRING = s("SESSION_STRING", "")
GAME_CHAT  = i("GAME_CHAT", -1004467330949)      # از لینک t.me/c/4467330949/...
INVITE_HASH = s("INVITE_HASH", "HfoXTH_qx4k1Zjg0")
BUTTON_TEXT = s("BUTTON_TEXT", "Play LumberJack!")

# --- هدف
TARGET_SCORE = i("TARGET_SCORE", 2000)
RUN_PAUSE = f("RUN_PAUSE", 5)
TAP_DELAY = f("TAP_DELAY", 0.14)
TAP_JITTER = f("TAP_JITTER", 0.07)

# --- مرورگر
VIEW_W = i("VIEW_W", 390); VIEW_H = i("VIEW_H", 844)
PLAY_X = f("PLAY_X", .50); PLAY_Y = f("PLAY_Y", .81)
LEFT_X = f("LEFT_X", .29); RIGHT_X = f("RIGHT_X", .71); TAP_Y = f("TAP_Y", .81)

# --- ★ بینایی (اگر بازی تغییر کرد، فقط این‌ها را تنظیم کن)
CROP_TOP = f("CROP_TOP", 0.0); CROP_BOTTOM = f("CROP_BOTTOM", 0.0)
ROW_H = f("ROW_H", 0.056)
DANGER_TOP = f("DANGER_TOP", 0.9); DANGER_BOT = f("DANGER_BOT", 0.4)
NEXT_TOP = f("NEXT_TOP", 1.9);   NEXT_BOT = f("NEXT_BOT", 1.0)
GREEN_MIN = i("GREEN_MIN", 40)
TRUNK_M = f("TRUNK_M", 0.07); SPAN = f("SPAN", 0.42)

DEBUG = s("DEBUG","1")=="1"
SHOT_UPLOAD = s("SHOT_UPLOAD","0")=="1"   # آپلود اختیاری اسکرین‌شات برای دیباگ ریموت

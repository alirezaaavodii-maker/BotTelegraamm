import sys, os
import numpy as np
from PIL import Image, ImageDraw
from dotenv import load_dotenv; load_dotenv()
import config as C
from perception import analyze, play_screen

path = sys.argv[1]
a = np.array(Image.open(path).convert("RGB"))
print("play_screen:", play_screen(a, C))
st = analyze(a, C); print(st)
if st.get("ok"):
    d = ImageDraw.Draw(img := Image.open(path).convert("RGB"))
    off, W, tr, rt, rh = st["top"], st["W"], st["trunk_x"], st["red_top"], st["row_h"]
    m, sp = int(W*C.TRUNK_M), int(W*C.SPAN)
    d.line([(tr,0),(tr,img.height)], fill=(255,0,255), width=3)
    for top,bot,col in [(C.DANGER_TOP,C.DANGER_BOT,(255,0,0)),(C.NEXT_TOP,C.NEXT_BOT,(255,165,0))]:
        y1,y2 = off+int(rt-top*rh), off+int(rt+bot*rh)
        d.rectangle([(tr-sp,y1),(tr-m,y2)], outline=col, width=3)
        d.rectangle([(tr+m,y1),(tr+sp,y2)], outline=col, width=3)
    out = path.replace(".png","_annot.png"); img.save(out); print("saved:", out)

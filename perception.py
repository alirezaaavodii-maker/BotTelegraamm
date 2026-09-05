import numpy as np

def _crop(a, c):
    H = a.shape[0]
    return a[int(H*c.CROP_TOP):int(H*(1-c.CROP_BOTTOM))]

def analyze(a0, c):
    a = _crop(a0, c); H, W, _ = a.shape
    R = a[...,0].astype(np.int16); G = a[...,1].astype(np.int16); B = a[...,2].astype(np.int16)
    red = (R>120)&(R>G+45)&(R>B+45)                      # پیراهن قرمز بازیکن
    ys, xs = np.nonzero(red)
    if len(xs) < 25: return dict(ok=False)
    red_top, py, px = int(ys.min()), float(ys.mean()), float(xs.mean())
    brown = (R>100)&(R<215)&(G>60)&(G<160)&(B<110)&(R>G+18)&(G>B+5)
    x0, x1 = int(W*.30), int(W*.70)
    trunk = x0 + int(brown[:, x0:x1].sum(0).argmax())    # تنه درخت
    green = (G>100)&(G>R+12)&(G>B+30)                    # شاخه‌ها
    rh = max(6.0, H*c.ROW_H); m = int(W*c.TRUNK_M); sp = int(W*c.SPAN)
    def cnt(side, top, bot):
        y1 = max(0,int(red_top-top*rh)); y2 = min(H,int(red_top+bot*rh))
        if y2 <= y1: return 0
        xa, xb = (max(0,trunk-sp), max(0,trunk-m)) if side=="L" else (min(W,trunk+m), min(W,trunk+sp))
        return int(green[y1:y2, xa:xb].sum())
    dL, dR = cnt("L",c.DANGER_TOP,c.DANGER_BOT), cnt("R",c.DANGER_TOP,c.DANGER_BOT)
    nL, nR = cnt("L",c.NEXT_TOP,c.NEXT_BOT),   cnt("R",c.NEXT_TOP,c.NEXT_BOT)
    return dict(ok=True, W=W, H=H, top=int(a0.shape[0]*c.CROP_TOP), trunk_x=trunk,
                red_top=red_top, row_h=rh, player_side="L" if px<trunk else "R",
                dL=dL, dR=dR, nL=nL, nR=nR,
                danger_L=dL>=c.GREEN_MIN, danger_R=dR>=c.GREEN_MIN)

def play_screen(a0, c):
    """صفحه شروع/پایان: دکمه چوبی بزرگ وسط پایین"""
    a = _crop(a0, c); H, W, _ = a.shape
    reg = a[int(H*(c.PLAY_Y-.06)):int(H*(c.PLAY_Y+.06)), int(W*.40):int(W*.60)].astype(np.int16)
    R,G,B = reg[...,0], reg[...,1], reg[...,2]
    wood = (R>190)&(R<255)&(G>130)&(G<210)&(B>70)&(B<170)&(R>G+25)&(G>B+15)
    return float(wood.mean()) > 0.25

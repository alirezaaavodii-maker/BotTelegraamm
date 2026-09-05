def decide(st, last):
    dL, dR = st["danger_L"], st["danger_R"]
    if dL and not dR: return "R"     # شاخه سمت چپه → بپر راست
    if dR and not dL: return "L"
    if dL and dR:     return "R" if last=="L" else "L"   # نباید رخ بده
    return last                      # هر دو امن → همون سمت قبلی

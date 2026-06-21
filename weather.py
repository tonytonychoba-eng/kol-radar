"""雲端市場天氣:每天現抓資料,算「壓力共振」+「歷史位置(描述型)」。

來源:Yahoo(^TWII/^SOX/^VIX)、TWSE 官方(外資對大盤買賣超,best-effort)。
守則(沿用 stock-radar):
  - 只描述現況、不預測漲跌;高檔 ≠ 賣訊(估值/歷史位置只供參考,不計柴乾)。
  - 多項「實質轉弱」同時出現才算天氣轉壞(共振),不靠單一訊號嚇人。
  - 資料掉了就標問號、不讓報告崩。
"""
import datetime
import requests

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{}"


def _closes(symbol, range_="1y"):
    try:
        r = requests.get(CHART.format(symbol), params={"range": range_, "interval": "1d"},
                         headers=UA, timeout=20)
        r.raise_for_status()
        res = (r.json().get("chart") or {}).get("result")
        if not res:
            return []
        ts = res[0].get("timestamp") or []
        q = (res[0].get("indicators", {}).get("quote") or [{}])[0].get("close") or []
        return [(datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"), c)
                for t, c in zip(ts, q) if c is not None]
    except Exception:
        return []


def _twii():
    h = _closes("%5ETWII", "max")
    if len(h) < 30:
        return None
    cur = h[-1][1]
    yr = h[-1][0][:4]
    win = h[-252:] if len(h) >= 252 else h            # 近 52 週
    lo = min(c for _, c in win); hi = max(c for _, c in win)
    pos52 = (cur - lo) / (hi - lo) * 100 if hi > lo else None
    ytd_base = next((c for d, c in h if d[:4] == yr), h[0][1])
    ytd = (cur - ytd_base) / ytd_base * 100
    ath = max(c for _, c in h)                          # 歷史最高
    return {"cur": cur, "pos52": pos52, "ytd": ytd, "dist_ath": (cur - ath) / ath * 100}


def _sox():
    h = _closes("%5ESOX", "5d")
    return (h[-1][1] - h[-2][1]) / h[-2][1] * 100 if len(h) >= 2 else None


def _vix():
    h = _closes("%5EVIX", "5d")
    return h[-1][1] if h else None


def _foreign_net():
    """TWSE 三大法人:外資對整個大盤的買賣超(億元),抓最近有資料的交易日。"""
    base = datetime.datetime.utcnow() + datetime.timedelta(hours=8)   # 台北
    for back in range(0, 6):
        d = (base - datetime.timedelta(days=back)).strftime("%Y%m%d")
        try:
            r = requests.get("https://www.twse.com.tw/fund/BFI82U",
                             params={"response": "json", "dayDate": d, "type": "day"},
                             headers=UA, timeout=20)
            j = r.json()
            if j.get("stat") != "OK":
                continue
            for row in j.get("data", []):
                if "外資及陸資" in row[0]:            # =外資對大盤淨買賣超(不含外資自營商)
                    return {"date": d, "net_e": int(str(row[3]).replace(",", "")) / 1e8}
        except Exception:
            continue
    return None


def _kol_heat(results):
    """讀各台 KOL 分析 → 判散戶情緒/柴火。回傳 (顯示行, is_hot)。便宜的一次 Gemini 呼叫。"""
    import os
    from openai import OpenAI
    blob = "\n\n".join(f"# {tag}:{a[:600]}" for tag, _t, a in results)
    c = OpenAI(api_key=os.environ.get("LLM_API_KEY"),
               base_url=os.environ.get("LLM_BASE_URL",
                                       "https://generativelanguage.googleapis.com/v1beta/openai/"))
    prompt = ("根據以下財經 Podcast 各台分析,判斷『散戶情緒/市場柴火』。\n"
              "第一行只輸出一個詞:HOT(多台同喊同題材、明顯樂觀過熱)、NEUTRAL(中性/分歧)、FEAR(偏恐慌)。\n"
              "第二行一句話說明散戶在熱什麼或怕什麼(30 字內)。\n\n各台分析:\n" + blob[:18000])
    r = c.chat.completions.create(
        model=os.environ.get("KOL_SYNTH_MODEL", os.environ.get("KOL_MODEL", "gemini-2.5-flash-lite")),
        max_tokens=120, messages=[{"role": "user", "content": prompt}])
    txt = (r.choices[0].message.content or "").strip()
    head = txt.split("\n")[0].upper()
    desc = txt.split("\n", 1)[1].strip() if "\n" in txt else ""
    hot = "HOT" in head
    tag = "⚠️ 🔥散戶過熱" if hot else ("➖ 散戶偏恐慌" if "FEAR" in head else "✅ 散戶情緒中性")
    return (f"{tag}:{desc}（柴火,反指標參考）" if desc else f"{tag}（柴火,反指標參考）"), hot


def build(results=None):
    lines, warn, signals = [], 0, 0

    tw = _twii()
    if tw and tw["pos52"] is not None:
        # 描述型歷史:只說「現在在哪」,不計柴乾、不喊方向(1/15 教訓)
        lines.append(f"ℹ️ 加權指數:52週位置 {tw['pos52']:.0f}%、今年 {tw['ytd']:+.0f}%、"
                     f"距歷史高 {tw['dist_ath']:+.0f}%(描述,不預測)")

    sox = _sox()
    if sox is not None:
        signals += 1
        if sox <= -1.5:
            lines.append(f"⚠️ 費半昨夜 {sox:+.1f}%(半導體逆風)"); warn += 1
        elif sox >= 1.0:
            lines.append(f"✅ 費半昨夜 {sox:+.1f}%(順風)")
        else:
            lines.append(f"➖ 費半昨夜 {sox:+.1f}%")

    vix = _vix()
    if vix is not None:
        signals += 1
        if vix >= 30:
            lines.append(f"⚠️ VIX {vix:.0f}(市場恐慌)"); warn += 1
        elif vix >= 20:
            lines.append(f"➖ VIX {vix:.0f}(略緊張)")
        else:
            lines.append(f"✅ VIX {vix:.0f}(平靜)")

    fn = _foreign_net()
    if fn is not None:
        signals += 1
        if fn["net_e"] <= -100:
            lines.append(f"⚠️ 外資賣超大盤 {fn['net_e']:.0f} 億(資金退潮)"); warn += 1
        elif fn["net_e"] >= 100:
            lines.append(f"✅ 外資買超大盤 {fn['net_e']:.0f} 億")
        else:
            lines.append(f"➖ 外資對大盤 {fn['net_e']:+.0f} 億")

    # ⑤ 散戶情緒/柴火:讀 KOL 各台分析判市場過不過熱(反指標;過熱算一項實質轉弱=環境脆弱)
    if results:
        try:
            line, hot = _kol_heat(results)
            lines.append(line)
            signals += 1
            if hot:
                warn += 1
        except Exception:
            pass

    if not lines:
        return "🌡 今日天氣:⚠️ 資料源暫時取不到,今天天氣打問號、略過參考"

    if signals and warn >= max(2, signals * 0.6):
        level = f"🔴 天氣轉壞（{warn} 項實質轉弱）"
    elif warn == 0:
        level = "🟢 天氣晴（無實質轉弱）"
    else:
        level = f"🟡 局部轉弱（{warn} 項）"

    return (f"🌡 今日天氣 {level}\n" + "\n".join("・" + x for x in lines) +
            "\n(研判環境脆弱度,非預測漲跌;高檔≠賣訊)")


if __name__ == "__main__":
    print(build())

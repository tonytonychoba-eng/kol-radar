"""從各台 KOL 分析抽出「個股 → 老師說的優勢論述 + 可驗證claim + narrative」。
寫成 state/kol_stocks.json,給 stock-radar(本地、有硬數據)讀去驗證。

鐵律:這端只抽『老師說了什麼』,絕不判斷對錯——
      『對不對』要對硬數據(營收/法人/價量)驗,那在 stock-radar 端做。
      不讓 AI 憑自己知識瞎判產業資訊正確與否(那是假信心)。
"""
import json
import os
import datetime
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("LLM_API_KEY"),
    base_url=os.environ.get("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
)
MODEL = os.environ.get("KOL_SYNTH_MODEL", os.environ.get("KOL_MODEL", "gemini-2.5-flash-lite"))

PROMPT = """從以下財經 Podcast 各台分析,抽出「有講到『公司優勢/為什麼強』的個股」。
只抽「有論述」的(老師說明了它強在哪),不要只喊代號沒講理由的。

每檔輸出這些欄位:
- name: 公司名
- code: 台股代號(你很確定才填,不確定填空字串 "")
- channels: 哪幾台提到(陣列)
- advantage: 老師說的優勢/強在哪(一句話)
- claims: 「可被數據驗證」的量化說法,每個是 {{"type": ..., "text": ...}};type 只能是:
    revenue_up(營收成長/需求強/拉貨)、revenue_down、foreign_buy(外資買超/進場)、
    foreign_sell(外資賣)、trust_buy(投信買)、volume_up(爆量/帶量突破)、price_break(創高/突破)
- narrative: 「無法用數據驗證」的軟性/未來說法(技術領先、訂單滿到明年、護城河、未來會贏…),字串陣列

只根據分析內容、不要腦補。沒有合格個股就回 {{"stocks": []}}。
只回 JSON,格式:{{"stocks": [ {{...}} ]}}

各台分析:
{blob}
"""


def _parse(txt):
    txt = (txt or "").strip()
    if txt.startswith("```"):
        txt = txt.split("```")[1]
        if txt.lower().startswith("json"):
            txt = txt[4:]
    return json.loads(txt)


def extract(results):
    """results: [(tag,title,analysis)] → 回傳 [stock dict]。"""
    blob = "\n\n".join(f"# {tag}：{a}" for tag, _t, a in results)
    try:
        r = client.chat.completions.create(
            model=MODEL, max_tokens=1800,
            messages=[{"role": "user", "content": PROMPT.format(blob=blob[:40000])}])
        return _parse(r.choices[0].message.content).get("stocks", [])
    except Exception as e:
        print(f"  KOL 個股論述抽取失敗:{e}")
        return []


def save(stocks, path="state/kol_stocks.json"):
    today = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime("%Y-%m-%d")
    json.dump({"date": today, "stocks": stocks},
              open(path, "w"), ensure_ascii=False, indent=1)

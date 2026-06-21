"""跨 podcast 總結:讀「所有單台五層分析」→ 出一段「早安總結」。
走同一個 OpenAI 相容端點(預設 Gemini)。讀的是摘要(短),很便宜。
之後 GPT/Claude 的「收尾 take」會是另外的模組,各自再讀這份總結。
"""
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("LLM_API_KEY"),
    base_url=os.environ.get("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
)
MODEL = os.environ.get("KOL_SYNTH_MODEL", os.environ.get("KOL_MODEL", "gemini-2.5-flash-lite"))

PROMPT = """你拿到今天數個財經 Podcast「各自的五層分析」,以及「今日市場天氣」。請整合成一段精簡的「早安總結」(全部 300 字內),只根據下面內容、不要腦補:

🌡 散戶情緒 vs 天氣:綜合各台語氣,散戶偏樂觀/中性/恐慌?把這個跟「今日天氣」對照——例如「天氣晴但散戶很熱→柴火偏高、留意過熱」,或「天氣轉壞但散戶還樂觀→留意」。(天氣只描述現況、不預測;高檔≠賣訊)
🔥 跨台熱議 Top:哪些「產業/題材」被多台同時提到?列出是哪幾台 → 越多台講越值得注意。
📌 值得自己深挖:挑 1-2 條最該你親自查證的線索。

今日市場天氣(背景參考,描述非預測):
{weather}

各台分析如下:
{blob}
"""


def synthesize(results, weather=""):
    """results: list of (tag, title, analysis)。weather: 今日天氣文字。"""
    blob = "\n\n".join(f"# {tag}《{title[:40]}》\n{a}" for tag, title, a in results)
    resp = client.chat.completions.create(
        model=MODEL, max_tokens=800,
        messages=[{"role": "user", "content": PROMPT.format(
            weather=weather or "(今日天氣資料從缺)", blob=blob[:40000])}],
    )
    return (resp.choices[0].message.content or "").strip()

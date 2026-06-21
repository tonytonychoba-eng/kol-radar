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

PROMPT = """你拿到今天數個財經 Podcast「各自的五層分析」。請跨頻道整合成一段精簡的「早安總結」(全部 300 字內),只根據下面內容、不要腦補:

🌡 散戶情緒溫度:綜合各台語氣,整體偏樂觀/中性/恐慌?大家在熱議什麼題材 → 柴火高不高(過熱常是反指標)。
🔥 跨台熱議 Top:哪些「產業/題材」被多台同時提到?各列出是哪幾台講的 → 越多台講、越值得注意。
📌 值得自己深挖:挑 1-2 條最該你親自查證的線索。

各台分析如下:

{blob}
"""


def synthesize(results):
    """results: list of (tag, title, analysis)。"""
    blob = "\n\n".join(f"# {tag}《{title[:40]}》\n{a}" for tag, title, a in results)
    resp = client.chat.completions.create(
        model=MODEL, max_tokens=800,
        messages=[{"role": "user", "content": PROMPT.format(blob=blob[:40000])}],
    )
    return (resp.choices[0].message.content or "").strip()

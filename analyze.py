"""逐字稿 → 五層分析。

走 OpenAI 相容端點,預設接 Gemini 2.5 Flash-Lite(最便宜、中文好、有免費額度)。
要換 provider(DeepSeek/Groq/OpenAI…)只要改三個環境變數:
  LLM_API_KEY / LLM_BASE_URL / KOL_MODEL —— 程式不動。
分析時自動修專有名詞同音字(臥屑→沃許/Warsh 之類)。
"""
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("LLM_API_KEY"),
    base_url=os.environ.get("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
)
MODEL = os.environ.get("KOL_MODEL", "gemini-2.5-flash-lite")

PROMPT = """你是財經內容分析助理。下面是某財經 Podcast 的逐字稿(由語音辨識產生,專有名詞可能有同音錯字,請依上下文還原,例如「臥屑/沃許」是 Fed 的 Warsh)。

請只根據逐字稿、不要腦補,用五層結構濃縮(整段 350 字內,精簡):

【一句重點】這集最核心的一句結論。
【邏輯鏈】他為什麼這樣判斷(A→B→C)。
【事實vs觀點】(a)可查證事實(數據/政策/事件) (b)他的個人預測/喊話——務必分清。
【產業線索】點名了哪些產業/族群,簡述理由(這是供應鏈情報,不是買賣建議)。
【可信度】偏「產業科普」還是「喊盤明牌」?有沒有明確叫人買賣某檔?資訊密度高不高?

頻道:{tag}
標題:{title}

逐字稿:
{transcript}
"""


def analyze(tag, title, transcript):
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=1200,
        messages=[{"role": "user",
                   "content": PROMPT.format(tag=tag, title=title, transcript=transcript[:60000])}],
    )
    return (resp.choices[0].message.content or "").strip()

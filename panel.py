"""收尾 take:GPT + Claude 各讀「跨台總結」給一段獨立結論(交叉討論)。
每家獨立 try——一家掛不影響另一家(例:OpenAI 帳單沒開通時,GPT 跳過、Claude 照給)。
Gemini 已經做了總結,這層是另外兩家「對總結的收尾」,湊成三家交叉。
"""
import os

TAKE_PROMPT = """你是資深財經顧問。下面是今天多個財經 Podcast 的「跨台總結」,以及「今日市場天氣」。
請給一段精簡(150 字內)的「收尾結論」:
- 最值得注意的 1-2 件事(為什麼)——把 KOL 情報跟天氣對照看
- 一個風險提醒
讀者是 ETF 定期定額、不擇時的投資人——不要給買賣建議,給的是「理解世界 + 風險意識」。天氣只描述現況、不預測;高檔≠賣訊,別看歷史位置就喊保守。

今日市場天氣:
{w}

跨台總結:
{s}
"""


def _gpt(synthesis, weather):
    from openai import OpenAI
    c = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    r = c.chat.completions.create(
        model=os.environ.get("GPT_MODEL", "gpt-5.4-mini"),
        max_completion_tokens=800,
        messages=[{"role": "user", "content": TAKE_PROMPT.format(s=synthesis, w=weather)}],
    )
    return (r.choices[0].message.content or "").strip()


def _claude(synthesis, weather):
    import anthropic
    c = anthropic.Anthropic()
    m = c.messages.create(
        model=os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5"),
        max_tokens=500,
        messages=[{"role": "user", "content": TAKE_PROMPT.format(s=synthesis, w=weather)}],
    )
    return "".join(b.text for b in m.content if b.type == "text").strip()


ANALYSTS = [("GPT", "OPENAI_API_KEY", _gpt), ("Claude", "ANTHROPIC_API_KEY", _claude)]


def takes(synthesis, weather=""):
    """回傳 [(name, text)];沒金鑰→跳過該家;失敗→該家附簡短錯誤,不擋其他家。"""
    out = []
    w = weather or "(今日天氣資料從缺)"
    for name, keyenv, fn in ANALYSTS:
        if not os.environ.get(keyenv):
            continue
        try:
            txt = fn(synthesis, w)
            out.append((name, txt or "(無輸出)"))
        except Exception as e:
            out.append((name, f"(暫時失敗:{str(e)[:90]})"))
    return out

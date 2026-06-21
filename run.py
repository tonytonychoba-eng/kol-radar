"""每日主流程:抓新集 → 篩 → 轉錄 → 分析 → 彙整 → 推 LINE。
已分析過的集數記在 state/seen.json,跨日不重做。
單集失敗不會拖垮整批(各自 try)。
"""
import json, os, datetime, traceback
import channels, transcribe, analyze, notify

SEEN_PATH = "state/seen.json"
MAX_EPISODES = int(os.environ.get("KOL_MAX_EPISODES", "8"))   # 每次上限,控雲端時間


def load_seen():
    try:
        return set(json.load(open(SEEN_PATH)))
    except Exception:
        return set()


def save_seen(seen):
    json.dump(sorted(seen), open(SEEN_PATH, "w"), ensure_ascii=False, indent=0)


def main():
    seen = load_seen()
    results, skipped, done = [], [], 0

    for feed in channels.FEEDS:
        try:
            for ep in channels.latest(feed["url"], n=2):
                key = f"{feed['tag']}::{ep['guid']}"
                if key in seen:
                    continue
                if not channels.worth(ep, feed["policy"]):
                    skipped.append(f"{feed['tag']}|{ep['title'][:24]}(低產業相關,略過)")
                    seen.add(key)
                    continue
                if done >= MAX_EPISODES:
                    skipped.append(f"{feed['tag']}|{ep['title'][:24]}(超過本次上限,留待下次)")
                    continue
                print(f"▶ 轉錄+分析:{feed['tag']} | {ep['title'][:30]}", flush=True)
                text = transcribe.transcribe(ep["mp3"])
                a = analyze.analyze(feed["tag"], ep["title"], text)
                results.append((feed["tag"], ep["title"], a))
                seen.add(key)
                done += 1
        except Exception as e:
            skipped.append(f"{feed['tag']}|整台失敗:{e}")
            traceback.print_exc()

    save_seen(seen)

    # 彙整成一份 LINE 報告
    today = datetime.datetime.utcnow() + datetime.timedelta(hours=8)   # 台北時間
    lines = [f"☕ 你的財經頻道情報 {today:%m/%d}（自動）", ""]
    if not results:
        lines.append("今日沒有值得深析的新集(或都被篩掉)。")
    for tag, title, a in results:
        lines.append(f"━━ {tag} ━━")
        lines.append(f"《{title[:40]}》")
        lines.append(a)
        lines.append("")
    if skipped:
        lines.append("— 已略過 —")
        lines.extend(skipped)
    lines.append("")
    lines.append("👉 這是研究線索,不是買賣訊號。你是 ETF 定期定額,當理解世界用。")

    notify.push("\n".join(lines))
    print(f"完成:分析 {len(results)} 集,略過 {len(skipped)} 筆。")


if __name__ == "__main__":
    main()

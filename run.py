"""每日主流程:抓新集 → 篩 → 轉錄 → 分析 → 彙整 → 推 LINE。
已分析過的集數記在 state/seen.json,跨日不重做。
單集失敗不會拖垮整批(各自 try)。
"""
import json, os, datetime, traceback
import channels, transcribe, analyze, notify, synthesize, panel, weather, kolstocks

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
            for ep in channels.latest(feed["url"], n=1):
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

    # 抽 KOL 個股優勢論述 → 存 JSON 給 stock-radar(本地)對硬數據驗證
    try:
        ks = kolstocks.extract(results) if results else []
        kolstocks.save(ks)
        print(f"KOL 個股論述:{len(ks)} 檔")
    except Exception:
        traceback.print_exc()

    # 彙整成一份 LINE 報告
    today = datetime.datetime.utcnow() + datetime.timedelta(hours=8)   # 台北時間
    lines = [f"☕ 你的財經頻道情報 {today:%m/%d}（自動）", ""]
    try:
        wx = weather.build(results)          # 把 KOL 散戶情緒當柴火納入天氣
    except Exception:
        wx = "🌡 今日天氣:取得失敗"
        traceback.print_exc()
    lines.append(wx)
    lines.append("")
    if results:
        try:
            summary = synthesize.synthesize(results, weather=wx)
            lines.append("【今日總結】(Gemini 跨台整合，已參考天氣)")
            lines.append(summary)
            lines.append("")
            for name, take in panel.takes(summary, weather=wx):
                lines.append(f"🤖 {name} 收尾：")
                lines.append(take)
                lines.append("")
            lines.append("────────── 各台重點 ──────────")
            lines.append("")
        except Exception as e:
            lines.append(f"(總結/收尾生成失敗,先給各台:{e})")
            lines.append("")
            traceback.print_exc()
    else:
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

    digest = "\n".join(lines)
    print("\n===== 本次推播內容 =====\n" + digest + "\n========================\n")
    # 守住「早上 07:00 才推」——排程跑早了就忍到台北 7 點再推,避免太早吵你
    # (手動觸發若已過 7 點 → 立即推,不等待)
    now_tpe = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    seven = now_tpe.replace(hour=7, minute=0, second=0, microsecond=0)
    if now_tpe < seven:
        import time as _t
        wait = (seven - now_tpe).total_seconds()
        print(f"等到台北 07:00 再推(還 {wait/60:.0f} 分)…", flush=True)
        _t.sleep(wait)
    notify.push(digest)
    print(f"完成:分析 {len(results)} 集,略過 {len(skipped)} 筆。")


if __name__ == "__main__":
    main()

# kol-radar ☁️

每天清晨在 **GitHub 的伺服器**自動跑,把財經 Podcast 濃縮成「產業情報」推你 LINE。
**跑在雲端,不碰你的機器**——你的筆電睡不睡、帶不帶出門,它都照跑、不會斷。

## 流程
```
抓 7+ 台 RSS 最新集 → 標題/shownotes 篩(免費)→ 過關的才轉錄(whisper)
→ Claude 五層分析 → 彙整 → 推 LINE。已分析的記在 state/seen.json,不重做。
```

## 上線(一次性,約 10 分鐘)
1. **建一個 GitHub repo**(可設 private),把這整個資料夾推上去:
   ```bash
   cd ~/kol-radar && git init && git add . && git commit -m "init"
   git branch -M main
   git remote add origin git@github.com:<你的帳號>/kol-radar.git
   git push -u origin main
   ```
2. **設 3 個 Secret**(repo → Settings → Secrets and variables → Actions → New secret):
   - `LLM_API_KEY` — Gemini 金鑰(去 https://aistudio.google.com 免費申請,**有免費額度**)
   - `LINE_CHANNEL_TOKEN` — 你 LINE OA 的 channel token
   - `LINE_USER_ID` — 要推給誰(你的 user id)
3. **開啟 Actions**(repo → Actions 頁面按啟用)。
4. 想立刻測:Actions → 「KOL 財經情報」→ **Run workflow**(手動觸發)。
5. 之後**每天台北 06:00 自動跑**,起床就在 LINE。

## 調整(改 `.github/workflows/kol.yml` 的 env)
| 變數 | 預設 | 說明 |
|---|---|---|
| `KOL_MODEL` | `gemini-2.5-flash-lite` | 最便宜;要更深改 `gemini-2.5-flash` |
| `LLM_BASE_URL` | Gemini 相容端點 | 換 provider(DeepSeek/Groq/OpenAI)改這行即可 |
| `KOL_WHISPER` | `small` | 轉錄模型;要更準改 `medium`(較慢) |
| `KOL_MAX_EPISODES` | `8` | 每次最多分析幾集(控雲端時間/成本) |

排程時間:cron 是 UTC,`0 22 * * *` = 台北 06:00。要改時間改那行。

## 成本與規模(誠實)
- **錢**:Gemini 2.5 Flash-Lite($0.10/$0.40 每百萬字元,比 Haiku 便宜約 10 倍)→ 你的量大概 **~NT$10/月**,甚至落在免費額度內 = **$0**;轉錄用 runner 的 whisper **免費**。
- **時間瓶頸**:whisper 在雲端 2 核 runner 上會比較慢。**量大時**(每天 8 集以上)建議把 `transcribe.py` 的 `_get_model()` 換成**雲端 STT API(Groq/OpenAI)**——那層刻意獨立就是為了好抽換,runner 只跑 HTTP、又快又穩。
- 免費額度:public repo 的 Actions 分鐘數無上限;private repo 每月 2000 分鐘。

## 本機測試(不推 LINE,只印出來)
```bash
cd ~/kol-radar
export LLM_API_KEY=...              # Gemini 金鑰,要分析才需要
export LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
pip install -r requirements.txt
python run.py                       # 沒設 LINE secret 會改成印在終端機
```

## 待辦
- 推富漫談 futalk:拿到正確連結後加進 `channels.py` 的 FEEDS。
- 跨頻道彙整(本週熱議產業 Top）可再加一個 synthesis 步驟。

"""頻道清單 + 抓 RSS 最新集 + shownotes/標題篩選。

policy:
  always = 量少、產業密度高 → 永遠分析(不篩)
  filter = 日更/高量/混雜 → 套標題+shownotes 篩,值得才轉
"""
import urllib.request, xml.etree.ElementTree as ET, re, html

ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"

FEEDS = [
    {"tag": "股癌",       "url": "https://feeds.soundon.fm/podcasts/954689a5-3096-43a4-a80b-7810b219cef3.xml", "policy": "always"},
    {"tag": "游庭皓",     "url": "https://feeds.soundcloud.com/users/soundcloud:users:735679489/sounds.rss",   "policy": "filter"},
    {"tag": "曼報",       "url": "https://feed.firstory.me/rss/user/cmq4u0p94003n01xn3eia6e7k",                "policy": "filter"},
    {"tag": "M觀點",      "url": "https://feeds.soundon.fm/podcasts/b8f5a471-f4f7-4763-9678-65887beda63a.xml", "policy": "filter"},
    {"tag": "財報狗",     "url": "https://feed.firstory.me/rss/user/clcftm46z000201z45w1c47fi",                "policy": "always"},
    {"tag": "財經M平方",  "url": "https://feeds.soundon.fm/podcasts/d2aab16c-3a70-4023-b52b-e50f07852ecd.xml", "policy": "always"},
    {"tag": "財女珍妮",   "url": "https://feeds.soundon.fm/podcasts/4a8660a0-e0d0-490b-8d46-c28219606f47.xml", "policy": "filter"},
    {"tag": "1968退休倒計時", "url": "https://feed.firstory.me/rss/user/clo13nri90aop01y161ju0evc",            "policy": "filter"},
    {"tag": "股市隱者",   "url": "https://feeds.soundon.fm/podcasts/eb9e90a8-a889-425b-8855-4cf8cdf92c73.xml", "policy": "always"},
    # 待補:推富漫談 futalk（使用者提供連結後加入）
]

# 產業詞(加分) / 噪音詞(扣分)——只用標題+shownotes 判,免費、瞬間
PRODUCT = ["AI", "伺服器", "CoWoS", "矽光子", "HBM", "記憶體", "被動元件", "機器人", "重電",
           "矽智財", "台積電", "輝達", "供應鏈", "GaN", "HVDC", "半導體", "晶圓",
           "降息", "升息", "FED", "FOMC", "CPI", "通膨", "關稅", "產業", "財報", "EPS"]
NOISE = ["飆股", "報明牌", "會員", "當沖", "漲停", "噴出", "報警", "跟單", "蓋牌", "贊助", "優惠碼", "徵才", "回顧"]


def _clean(t):
    if not t:
        return ""
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def _dur_sec(s):
    if not s:
        return 0
    s = s.strip()
    if ":" in s:
        p = [int(x) for x in s.split(":")]
        return sum(v * 60 ** i for i, v in enumerate(reversed(p)))
    try:
        return int(float(s))
    except ValueError:
        return 0


def latest(feed_url, n=2):
    """回傳最新 n 集:[{guid,title,dur_sec,shownotes,mp3}]。"""
    req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
    root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
    out = []
    for item in root.findall(".//item")[:n]:
        enc = item.find("enclosure")
        out.append({
            "guid": (item.findtext("guid") or item.findtext("link") or item.findtext("title") or "").strip(),
            "title": _clean(item.findtext("title")),
            "dur_sec": _dur_sec(item.findtext(f"{ITUNES}duration")),
            "shownotes": _clean(item.findtext("description") or item.findtext(f"{ITUNES}summary")),
            "mp3": enc.get("url") if enc is not None else None,
        })
    return out


def score(ep):
    """標題權重高(shownotes 常是業配,可信度低)。"""
    title = ep["title"]
    notes = ep["shownotes"][:300]
    s = 0
    for w in PRODUCT:
        if w in title:
            s += 2
        if w in notes:
            s += 1
    for w in NOISE:
        if w in title:
            s -= 2
        if w in notes:
            s -= 1
    return s


def worth(ep, policy, threshold=1):
    """always → 一律收;filter → 分數過門檻 且 不是極短預告。"""
    if not ep["mp3"]:
        return False
    if 0 < ep["dur_sec"] < 480:          # < 8 分 = 預告/雜訊,跳過
        return False
    if policy == "always":
        return True
    return score(ep) >= threshold

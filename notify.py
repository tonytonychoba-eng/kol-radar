"""推 LINE(Messaging API push)。單則上限 5000 字,自動分段。"""
import os, json, urllib.request


def _chunks(text, size=4800):
    for i in range(0, len(text), size):
        yield text[i:i + size]


def push(text):
    token = os.environ.get("LINE_CHANNEL_TOKEN")
    uid = os.environ.get("LINE_USER_ID")
    if not token or not uid:
        print("⚠️ 未設 LINE secret,改印出:\n" + text)
        return
    for chunk in _chunks(text):
        req = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=json.dumps({"to": uid, "messages": [{"type": "text", "text": chunk}]}).encode(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=20)

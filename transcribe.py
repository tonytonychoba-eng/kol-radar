"""下載 MP3 → faster-whisper 轉文字(跑在雲端 runner)。

要擴大規模/求快時,把 _whisper() 換成雲端 STT API(Groq / OpenAI)即可,
其餘流程不變——這層刻意獨立就是為了好抽換。
"""
import os, subprocess, tempfile, time

_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        size = os.environ.get("KOL_WHISPER", "small")   # tiny/base/small/medium
        _MODEL = WhisperModel(size, device="cpu", compute_type="int8")
    return _MODEL


def _download(mp3_url, dst, retries=3):
    """帶 UA + 重試——今晚財報狗就是下載被重置才掛,這裡補上。"""
    last = None
    for i in range(retries):
        try:
            subprocess.run(["curl", "-sSL", "--fail", "-A", "Mozilla/5.0",
                            "--max-time", "300", "-o", dst, mp3_url], check=True)
            if os.path.getsize(dst) > 10000:
                return
        except Exception as e:
            last = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"下載失敗(重試 {retries} 次):{last}")


def transcribe(mp3_url):
    """回傳整集逐字稿(字串)。"""
    with tempfile.TemporaryDirectory() as d:
        mp3 = os.path.join(d, "a.mp3")
        wav = os.path.join(d, "a.wav")
        _download(mp3_url, mp3)
        subprocess.run(["ffmpeg", "-y", "-i", mp3, "-ac", "1", "-ar", "16000", wav],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        segs, _ = _get_model().transcribe(wav, language="zh", beam_size=1)
        return "".join(s.text for s in segs)

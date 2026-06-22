# -*- coding: utf-8 -*-
"""
applab_main.py — วางเป็น python/main.py ของ App Lab
SAFE บน UNO Q: พูด/ไฟล์เสียง -> AI -> Modulino Pixels 3 สี + Buzzer (แดง) + ปุ่ม A/B

ตั้งค่าได้ที่ตัวแปรด้านล่าง:
  USE_BRIDGE = True   ใช้ Modulino (pixels/buzzer/buttons) ผ่าน sketch.ino
             = False  ใช้ไฟ onboard + โหมดอัตโนมัติ (ไม่ใช้ปุ่ม) -> ใช้ตอน sketch ยังไม่พร้อม
  MODE = "mic"        ปุ่ม A = อัดเสียงสด (กดเริ่ม/กดหยุด)
       = "clips"      ปุ่ม A = วิเคราะห์ไฟล์เสียงถัดไปในโฟลเดอร์ python/clips/ (สำหรับเดโมคลิป)
ปุ่ม B = ล้างบทสนทนา เริ่มสายใหม่ (ทั้งสองโหมด)
"""
import os
import re
import time
import glob
import joblib
import numpy as np
from arduino.app_utils import App, Bridge, Leds
from pythainlp.tokenize import word_tokenize

# ================== ตั้งค่า ==================
USE_BRIDGE = True
MODE = "mic"
REC_SECONDS = 6      # ใช้กับโหมด non-bridge (auto) เท่านั้น
MODEL_SIZE = "small"  # tiny < base < small < medium (แม่นขึ้น/ช้าลง)
OFFLINE = True       # True = บังคับ Whisper ใช้ cache ไม่ต่อเน็ตเลย (สำหรับรันออฟไลน์/พรีเซนต์)
# ============================================

# บังคับออฟไลน์ ต้องตั้งก่อน import faster_whisper -> กันค้างเพราะรอต่อ HuggingFace
if OFFLINE:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"


def text_tokenize(text):
    return word_tokenize(text, engine="newmm") if isinstance(text, str) else []


_RE = re.compile(r"(.{2,15}?)\1{2,}")
def normalize_text(text):
    return _RE.sub(r"\1", text.lower().replace("ๆ", " ")) if isinstance(text, str) else ""


here = os.path.dirname(os.path.abspath(__file__))
model = joblib.load(os.path.join(here, "scam_model.pkl"))
vectorizer = joblib.load(os.path.join(here, "vectorizer.pkl"))
print("=== MODEL LOADED OK ===")

# ---------- ฮาร์ดแวร์ (Modulino ผ่าน Bridge หรือ onboard fallback) ----------
bridge = Bridge() if USE_BRIDGE else None
leds = Leds()
RGB = {"RED": (255, 0, 0), "YELLOW": (255, 150, 0), "GREEN": (0, 255, 0), "BLUE": (0, 0, 255)}
BOOL = {"RED": (True, False, False), "YELLOW": (True, True, False),
        "GREEN": (False, True, False), "BLUE": (False, False, True)}


def show_color(name):
    if USE_BRIDGE:
        try:
            r, g, b = RGB[name]
            bridge.call("set_color", r, g, b)
            return
        except Exception as e:
            print("set_color err:", e)
    r, g, b = BOOL[name]              # fallback ไฟ onboard
    leds.set_led1_color(r, g, b)
    leds.set_led2_color(r, g, b)


def do_buzz():
    if USE_BRIDGE:
        try:
            bridge.call("buzz", 880, 600)
        except Exception as e:
            print("buzz err:", e)


def read_buttons():
    if not USE_BRIDGE:
        return False, False
    try:
        v = int(bridge.call("read_buttons"))
        return bool(v & 1), bool(v & 2)
    except Exception:
        return False, False


def classify(text):
    conf = model.predict_proba(vectorizer.transform([text]))[0][list(model.classes_).index(1)] * 100
    return ("RED" if conf >= 70 else ("YELLOW" if conf >= 40 else "GREEN")), conf


# ---------- เสียง ----------
whisper = None
sd = None
try:
    import sounddevice as sd
    from faster_whisper import WhisperModel
    try:
        # ใช้โมเดลจาก cache โดยไม่แตะเน็ต (เหมาะกับรันเดี่ยวออฟไลน์)
        whisper = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8",
                               cpu_threads=4, local_files_only=True)
        print("=== AUDIO READY (โมเดลจาก cache, ออฟไลน์) ===")
    except Exception:
        # ครั้งแรกที่ยังไม่มี cache -> ดาวน์โหลด (ต้องมีเน็ต)
        whisper = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8", cpu_threads=4)
        print("=== AUDIO READY (ดาวน์โหลดโมเดลครั้งแรก) ===")
except Exception as e:
    print("เสียงยังไม่พร้อม:", e)

_AUDIO_EXT = (".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac")
CLIPS = sorted(f for f in glob.glob(os.path.join(here, "clips", "*"))
               if f.lower().endswith(_AUDIO_EXT))
_clip = 0
conv = []
recording = False
frames = []
stream = None


def transcribe_audio(audio_or_path):
    t0 = time.time()
    print("กำลังถอดเสียง...")
    segs, _ = whisper.transcribe(audio_or_path, language="th", vad_filter=True,
                                 beam_size=1, condition_on_previous_text=False)
    text = " ".join(s.text for s in segs).strip()
    print("ถอดเสร็จใน %.1f วิ" % (time.time() - t0))
    return text


def analyze(text):
    if not text or len([t for t in text_tokenize(normalize_text(text)) if t.strip()]) < 3:
        print("ฟังอยู่... (ข้อมูลยังไม่พอ)")
        return
    conv.append(text)
    full = " ".join(conv)
    name, conf = classify(full)
    show_color(name)
    if name == "RED":
        do_buzz()
    print("[%s] %.1f%%  %s" % (name, conf, text))


def reset_call():
    global conv, recording, frames, stream
    conv = []
    frames = []
    recording = False
    if stream:
        try:
            stream.stop(); stream.close()
        except Exception:
            pass
        stream = None
    show_color("GREEN")
    print("=== เริ่มสายใหม่ (ล้างบทสนทนา) ===")


def toggle_mic():
    """ปุ่ม A ในโหมด mic: กดเริ่มอัด / กดอีกที = หยุด แล้ววิเคราะห์"""
    global recording, frames, stream
    if not recording:
        frames = []
        recording = True
        show_color("BLUE")
        def cb(indata, n, t, s):
            if recording:
                frames.append(indata.copy())
        stream = sd.InputStream(samplerate=16000, channels=1, dtype="float32", callback=cb)
        stream.start()
        print("🔵 เริ่มอัด พูดได้เลย (กด A อีกครั้งเพื่อหยุด)")
    else:
        recording = False
        if stream:
            try:
                stream.stop(); stream.close()
            except Exception:
                pass
            stream = None
        if frames:
            audio = np.concatenate(frames).flatten()
            peak = float(np.max(np.abs(audio)))
            if peak < 0.02:
                print("เงียบ... (ไม่มีเสียงพูด)")
                return
            analyze(transcribe_audio(audio / peak * 0.95))


def next_clip():
    """ปุ่ม A ในโหมด clips: วิเคราะห์ไฟล์เสียงถัดไป"""
    global _clip
    if not CLIPS:
        print("ไม่มีไฟล์เสียงในโฟลเดอร์ clips/")
        return
    path = CLIPS[_clip % len(CLIPS)]
    _clip += 1
    show_color("BLUE")
    print("เล่นไฟล์:", os.path.basename(path))
    analyze(transcribe_audio(path))


def record_fixed():
    """โหมด non-bridge (ไม่มีปุ่ม): อัดอัตโนมัติรอบละ REC_SECONDS วิ"""
    show_color("BLUE")
    rec = sd.rec(int(REC_SECONDS * 16000), samplerate=16000, channels=1, dtype="float32")
    sd.wait()
    rec = rec.flatten()
    peak = float(np.max(np.abs(rec)))
    if peak < 0.02:
        print("เงียบ... (ไม่มีเสียงพูด)")
        return
    analyze(transcribe_audio(rec / peak * 0.95))


show_color("GREEN")
print("พร้อม | USE_BRIDGE=%s MODE=%s | clips=%d ไฟล์" % (USE_BRIDGE, MODE, len(CLIPS)))


def loop():
    if USE_BRIDGE:
        a, b = read_buttons()
        if b:
            reset_call()
        elif a:
            next_clip() if MODE == "clips" else toggle_mic()
        time.sleep(0.05)
    else:
        # ไม่มีปุ่ม -> ทำงานอัตโนมัติ
        next_clip() if MODE == "clips" else record_fixed()
        time.sleep(1)


App.run(user_loop=loop)

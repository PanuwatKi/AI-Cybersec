# -*- coding: utf-8 -*-
"""
applab_main.py — วางเป็น python/main.py ของ App Lab แล้วกด Run
SAFE บน UNO Q: วิเคราะห์มิจฉาชีพ -> ไฟ RGB ในตัวบอร์ด (Leds) เปลี่ยนสี แดง/เหลือง/เขียว

โหมดอัตโนมัติ:
  - ถ้ายังไม่มีไมค์/ไลบรารีเสียง -> "โหมดเดโม": วนโชว์ประโยคตัวอย่าง + ไฟเปลี่ยนสีจริง
  - ถ้ามี sounddevice + faster-whisper + ไมค์ -> "โหมดฟังสด": อัดเสียงทุก 6 วิ -> ถอด -> วิเคราะห์ -> ไฟ
(มี App.run ครั้งเดียวเท่านั้น!)
"""
import os
import re
import time
import joblib
from arduino.app_utils import App, Leds
from pythainlp.tokenize import word_tokenize


def text_tokenize(text):
    if not isinstance(text, str):
        return []
    return word_tokenize(text, engine="newmm")


_REPEAT_RE = re.compile(r"(.{2,15}?)\1{2,}")
def normalize_text(text):
    if not isinstance(text, str):
        return ""
    return _REPEAT_RE.sub(r"\1", text.lower().replace("ๆ", " "))


# ---------- โหลดโมเดล ----------
here = os.path.dirname(os.path.abspath(__file__))
model = joblib.load(os.path.join(here, "scam_model.pkl"))
vectorizer = joblib.load(os.path.join(here, "vectorizer.pkl"))
print("=== MODEL LOADED OK ===")


# ---------- ไฟ RGB ในตัวบอร์ด (Leds) ----------
leds = Leds()
COLORS = {  # (r, g, b) เป็น True/False
    "RED":    (True,  False, False),
    "YELLOW": (True,  True,  False),
    "GREEN":  (False, True,  False),
    "BLUE":   (False, False, True),   # ฟังอยู่
}


def show_led(name):
    r, g, b = COLORS[name]
    leds.set_led1_color(r, g, b)
    leds.set_led2_color(r, g, b)


def classify(text):
    conf = model.predict_proba(vectorizer.transform([text]))[0][list(model.classes_).index(1)] * 100
    name = "RED" if conf >= 70 else ("YELLOW" if conf >= 40 else "GREEN")
    return name, conf


# ---------- ลองตั้งค่าไมค์ (ถ้ามี -> โหมดฟังสด) ----------
SCAM_PROMPT = ("บทสนทนาทางโทรศัพท์ ธนาคาร บัญชี โอนเงิน รหัส OTP ตำรวจ คดี "
               "ฟอกเงิน พัสดุ ลิงก์ ลงทุน กำไร รางวัล")
# ขั้น 1: เช็กไมค์ (เพิ่ม "sounddevice" ใน requirements.txt ก่อน)
MIC_OK = False
sd = None
try:
    import sounddevice as sd
    print("MICS:", sd.query_devices())
    MIC_OK = True
except Exception as e:
    print("ยังไม่มี sounddevice:", e)

# ขั้น 2: เช็กตัวถอดเสียง (เพิ่ม "faster-whisper" ทีหลัง เมื่อไมค์ผ่านแล้ว)
LIVE = False
whisper = None
if MIC_OK:
    try:
        from faster_whisper import WhisperModel
        whisper = WhisperModel("tiny", device="cpu", compute_type="int8")
        LIVE = True
        print("=== LIVE MIC MODE: พูดใส่ไมค์ได้เลย (อัดรอบละ 6 วิ) ===")
    except Exception as e:
        print("ยังไม่มี faster-whisper:", e)

TESTS = [
    "ผมโทรจากตำรวจ บัญชีคุณพัวพันคดีฟอกเงิน โอนเงินมาตรวจสอบด่วน",
    "สวัสดีครับ ไม่ทราบว่าโทรมาจากไหนครับ",
    "ลงทุนกับเราการันตีกำไรสามสิบเปอร์เซ็นต์ต่อเดือน โอนเลย",
    "แม่ฝากซื้อไข่ไก่กับนมด้วยนะ",
    "เรียนคุณลูกค้า บัญชีถูกอายัด แจ้งรหัส OTP ด่วน",
]
_i = 0


def loop():
    """ถูกเรียกซ้ำโดย App framework"""
    global _i
    if LIVE:
        show_led("BLUE")  # ฟังอยู่
        rec = sd.rec(int(6 * 16000), samplerate=16000, channels=1, dtype="float32")
        sd.wait()
        segs, _ = whisper.transcribe(rec.flatten(), language="th",
                                     initial_prompt=SCAM_PROMPT, vad_filter=True)
        text = " ".join(s.text for s in segs).strip()
        if not text or len([t for t in text_tokenize(normalize_text(text)) if t.strip()]) < 3:
            print("ฟังอยู่... (ข้อมูลยังไม่พอ)")
            return
    else:
        text = TESTS[_i % len(TESTS)]
        _i += 1

    name, conf = classify(text)
    show_led(name)
    print("[" + name + "] " + ("%.1f" % conf) + "%  " + text)
    if not LIVE:
        time.sleep(3)


App.run(user_loop=loop)

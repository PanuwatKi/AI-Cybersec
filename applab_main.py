# -*- coding: utf-8 -*-
"""
applab_main.py — เนื้อหาสำหรับวางในช่อง python/main.py ของ Arduino App Lab
ใช้โครงสร้าง App.run(user_loop=loop) ตามที่ App Lab กำหนด (ต่างจาก app_unoq.py ที่เป็นสคริปต์เดี่ยว)

การทำงาน: กดปุ่ม A = เริ่ม/หยุดอัดเสียง -> AI ตรวจ -> ไฟ Modulino 3 สี + เสียง + %
          กดปุ่ม B = ล้างบทสนทนาเริ่มใหม่
*** ส่วน Modulino (set_pixels/beep/read_buttons) เป็น placeholder รอใส่ API จริง ดู BOARD_SETUP.md ***
หมายเหตุ: ถ้ายังไม่มีไมค์/ไลบรารีเสียง โค้ดจะไม่ crash (ข้ามส่วนเสียงไปก่อน)
"""
import os
import re
import time
import joblib
import numpy as np
from arduino.app_utils import App
from pythainlp.tokenize import word_tokenize


# --- ต้องชื่อตรงกับตอนเทรน เพราะ vectorizer.pkl อ้างถึง ---
def text_tokenize(text):
    if not isinstance(text, str):
        return []
    return word_tokenize(text, engine="newmm")


_REPEAT_RE = re.compile(r"(.{2,15}?)\1{2,}")
def normalize_text(text):
    if not isinstance(text, str):
        return ""
    return _REPEAT_RE.sub(r"\1", text.lower().replace("ๆ", " "))


# ---------- โหลดโมเดล (ทำครั้งเดียวตอนเริ่ม) ----------
here = os.path.dirname(os.path.abspath(__file__))
model = joblib.load(os.path.join(here, "scam_model.pkl"))
vectorizer = joblib.load(os.path.join(here, "vectorizer.pkl"))
print("✅ โหลดโมเดลแล้ว")


# ========== ส่วนฮาร์ดแวร์ Modulino — *** ปรับตาม API จริง (BOARD_SETUP.md Phase 4) *** ==========
def setup_modulino():
    # from modulino import ModulinoPixels, ModulinoBuzzer, ModulinoButtons
    # return ModulinoPixels(), ModulinoBuzzer(), ModulinoButtons()
    return None, None, None


def set_pixels(r, g, b):
    pass   # ตัวอย่าง: for i in range(8): pixels.set(i, r, g, b)  แล้ว pixels.show()


def beep(freq=1200, ms=120):
    pass   # buzzer.tone(freq, ms)


def read_buttons():
    # buttons.update(); return buttons.is_pressed("A"), buttons.is_pressed("B")
    return False, False


pixels, buzzer, buttons = setup_modulino()


# ---------- ตั้งค่าเสียง/Whisper (ถ้ายังไม่มีไมค์/ไลบรารี จะข้ามไปก่อน ไม่ crash) ----------
SCAM_PROMPT = ("บทสนทนาทางโทรศัพท์ ธนาคาร บัญชี โอนเงิน รหัส OTP ตำรวจ คดี "
               "ฟอกเงิน พัสดุ ลิงก์ ลงทุน กำไร รางวัล")
# ประกาศสถานะก่อน (เพื่อให้ callback อ้างถึง recording ได้แน่นอน)
conv = []
frames = []
recording = False
prev_a = prev_b = False

AUDIO_READY = False
whisper = None

try:
    import sounddevice as sd
    from faster_whisper import WhisperModel

    whisper = WhisperModel("tiny", device="cpu", compute_type="int8")  # บนบอร์ดใช้ tiny

    def _audio_cb(indata, n, t, status):
        if recording:
            frames.append(indata.copy())

    stream = sd.InputStream(samplerate=16000, channels=1, dtype="float32", callback=_audio_cb)
    stream.start()
    AUDIO_READY = True
    print("🎤 ระบบเสียงพร้อม")
except Exception as e:
    print("⚠️ ยังใช้เสียงไม่ได้ (รอไมค์/ไลบรารี):", e)


set_pixels(30, 30, 30)   # ไฟสถานะว่าง
print("พร้อม | ปุ่ม A = เริ่ม/หยุดอัด | ปุ่ม B = ล้างเริ่มใหม่")


def classify(text):
    conf = model.predict_proba(vectorizer.transform([text]))[0][list(model.classes_).index(1)] * 100
    if conf >= 70:
        return "RED", (255, 0, 0), conf
    if conf >= 40:
        return "YELLOW", (255, 150, 0), conf
    return "GREEN", (0, 255, 0), conf


def loop():
    """ถูกเรียกซ้ำ ๆ โดย App framework — ทำงาน 1 รอบต่อการเรียก"""
    global recording, prev_a, prev_b
    a, b = read_buttons()

    # ----- ปุ่ม A: เริ่ม/หยุดอัด -----
    if a and not prev_a and AUDIO_READY:
        if not recording:
            frames.clear()
            recording = True
            set_pixels(0, 0, 255); beep()          # ไฟน้ำเงิน = กำลังอัด
            print("🔵 เริ่มอัด พูดได้เลย")
        else:
            recording = False                       # กดอีกที = หยุด แล้ววิเคราะห์
            if frames:
                audio = np.concatenate(frames).flatten()
                segs, _ = whisper.transcribe(audio, language="th",
                                             initial_prompt=SCAM_PROMPT, vad_filter=True)
                text = " ".join(s.text for s in segs).strip()
                if text:
                    print("📝", text)
                    conv.append(text)
                    full = " ".join(conv)
                    if len([t for t in text_tokenize(normalize_text(full)) if t.strip()]) >= 3:
                        color, rgb, conf = classify(full)
                        set_pixels(*rgb)
                        if color == "RED":
                            beep(880, 600)
                        print(f"{color} {conf:.1f}%")
                    else:
                        set_pixels(30, 30, 30)

    # ----- ปุ่ม B: ล้างเริ่มใหม่ -----
    if b and not prev_b:
        conv.clear(); frames.clear(); recording = False
        set_pixels(30, 30, 30)
        print("📞 ล้างบทสนทนา เริ่มสายใหม่")

    prev_a, prev_b = a, b
    time.sleep(0.05)


App.run(user_loop=loop)

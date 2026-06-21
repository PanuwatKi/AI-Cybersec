# -*- coding: utf-8 -*-
"""
app_unoq.py — เวอร์ชันรันบน Arduino UNO Q (ฝั่ง Linux) ผ่าน Arduino App Lab
ขั้นตอน: พูดใส่ไมโครโฟน -> Whisper ถอดเป็นข้อความ -> AI ตรวจมิจฉาชีพ
        -> ไฟ Modulino 3 สี + เสียงเตือนเมื่อแดง + บอก % ความมั่นใจ
ควบคุมด้วยปุ่ม Modulino Buttons: ปุ่ม A = เริ่ม/หยุดอัด · ปุ่ม B = ล้างบทสนทนาเริ่มใหม่

*** นี่เป็น TEMPLATE ***
ส่วนควบคุม Modulino (ไฟ/เสียง) ใน setup_modulino()/show_result() ให้ปรับตาม API
ของไลบรารี Modulino Python ที่พี่เลี้ยงสอนใน Workshop Day 1 (ผมใส่ตัวอย่างเป็นคอมเมนต์ไว้)

การเตรียมบนบอร์ด (ทำใน App Lab):
  1) ลงไลบรารี:  pip install -r requirements-board.txt
  2) วางไฟล์ scam_model.pkl + vectorizer.pkl ไว้โฟลเดอร์เดียวกับไฟล์นี้
     แนะนำ: รัน  python train_model.py  บนบอร์ด เพื่อให้เวอร์ชัน sklearn ตรงกัน
     (เลี่ยงปัญหาโหลด .pkl ข้ามเวอร์ชัน)
  3) ใส่เป็นส่วน Python ของ App แล้ว Run
"""
import re
import joblib
from pythainlp.tokenize import word_tokenize


# --- ต้องนิยามให้ "ชื่อตรง" กับตอนเทรน เพราะ vectorizer.pkl อ้างถึง 2 ฟังก์ชันนี้ ---
def text_tokenize(text):
    if not isinstance(text, str):
        return []
    return word_tokenize(text, engine="newmm")


_REPEAT_RE = re.compile(r"(.{2,15}?)\1{2,}")
def normalize_text(text):
    if not isinstance(text, str):
        return ""
    return _REPEAT_RE.sub(r"\1", text.lower().replace("ๆ", " "))


RED_THRESHOLD, YELLOW_THRESHOLD = 70, 40   # เกณฑ์ % แบ่ง 3 สี


def classify(text, model, vectorizer):
    """คืน (สี, % โอกาสเป็นมิจฉาชีพ)"""
    proba = model.predict_proba(vectorizer.transform([text]))[0]
    conf = proba[list(model.classes_).index(1)] * 100
    if conf >= RED_THRESHOLD:
        return "RED", conf
    if conf >= YELLOW_THRESHOLD:
        return "YELLOW", conf
    return "GREEN", conf


# ============================================================
#  ส่วนฮาร์ดแวร์ Modulino — *** ปรับตาม API ที่เวิร์กช็อปสอน ***
# ============================================================
def setup_modulino():
    """เริ่มต้น Modulino Pixels (ไฟ) + Buzzer (เสียง) + Buttons (ปุ่มกด)"""
    # ตัวอย่าง (ชื่อจริงอาจต่างกันตามไลบรารีของ UNO Q):
    #   from modulino import ModulinoPixels, ModulinoBuzzer, ModulinoButtons
    #   pixels = ModulinoPixels()
    #   buzzer = ModulinoBuzzer()
    #   buttons = ModulinoButtons()
    #   return pixels, buzzer, buttons
    return None, None, None


def set_idle(pixels):
    """ไฟสถานะว่าง (รอกดปุ่ม) — เช่น ไฟขาวหรี่ ๆ"""
    print("⚪ พร้อม — กดปุ่ม A เพื่อเริ่มอัด")
    # for i in range(8): pixels.set(i, 30, 30, 30)
    # pixels.show()


def read_buttons(buttons):
    """อ่านปุ่ม คืน (กดA, กดB) — *** ปรับตาม API จริงของ Modulino Buttons ***"""
    # buttons.update()
    # return buttons.is_pressed("A"), buttons.is_pressed("B")
    return False, False


def show_result(pixels, buzzer, color, conf):
    """แสดงผลออกฮาร์ดแวร์: ไฟ 3 สี + เสียงเตือนเมื่อแดง + พิมพ์ %"""
    rgb = {"RED": (255, 0, 0), "YELLOW": (255, 150, 0), "GREEN": (0, 255, 0)}[color]
    emoji = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}[color]
    print(f"{emoji} [{color}] โอกาสเป็นมิจฉาชีพ {conf:.1f}%")

    # --- ปรับส่วนนี้ตาม API จริงของ Modulino ---
    # for i in range(8):
    #     pixels.set(i, rgb[0], rgb[1], rgb[2])
    # pixels.show()
    # if color == "RED":
    #     buzzer.tone(880, 600)   # เสียงเตือนเมื่อเสี่ยงสูง
    # ถ้ามี LCD ก็แสดง % ได้:  lcd.print(f"{color} {conf:.0f}%")


def signal_listening(pixels, buzzer):
    """บอกผู้ใช้ว่า 'เริ่มอัดเสียงแล้ว พูดได้เลย' — ไฟน้ำเงิน + เสียงบี๊บสั้น
    สำคัญตอนรันบนบอร์ดแบบไม่มีจอ ผู้ใช้จะได้รู้ว่าพูดตอนไหน"""
    print("🔵 เริ่มฟัง — พูดได้เลย")
    # --- ปรับตาม API จริงของ Modulino ---
    # for i in range(8):
    #     pixels.set(i, 0, 0, 255)     # ไฟน้ำเงิน = กำลังฟัง
    # pixels.show()
    # buzzer.tone(1200, 120)           # บี๊บสั้น ๆ บอกว่าเริ่มอัด


# ============================================================
#  ส่วนเสียง (Whisper) — รันบนบอร์ดใช้รุ่นเล็ก (tiny/base) เพราะ CPU จำกัด
# ============================================================
SCAM_PROMPT = ("บทสนทนาทางโทรศัพท์ เกี่ยวกับ ธนาคาร บัญชี โอนเงิน รหัส OTP "
               "ตำรวจ คดี ฟอกเงิน พัสดุ ลิงก์ ลงทุน กำไร รางวัล")


def get_whisper(size="tiny"):
    from faster_whisper import WhisperModel
    return WhisperModel(size, device="cpu", compute_type="int8")


def record(seconds=6, sr=16000):
    import sounddevice as sd
    print(f"🎙️  ฟัง {seconds} วินาที...")
    audio = sd.rec(int(seconds * sr), samplerate=sr, channels=1, dtype="float32")
    sd.wait()
    return audio.flatten()


def transcribe(whisper, audio):
    segs, _ = whisper.transcribe(audio, language="th",
                                 initial_prompt=SCAM_PROMPT, vad_filter=True)
    return " ".join(s.text for s in segs).strip()


def _enough(text):
    """มีข้อมูลพอจะตัดสินไหม (>= 3 คำหลัง normalize)"""
    return len([t for t in text_tokenize(normalize_text(text)) if t.strip()]) >= 3


def main():
    import time
    import numpy as np
    import sounddevice as sd

    print("⏳ กำลังโหลดโมเดล...")
    model = joblib.load("scam_model.pkl")
    vectorizer = joblib.load("vectorizer.pkl")
    pixels, buzzer, buttons = setup_modulino()
    whisper = get_whisper("tiny")          # บนบอร์ดเริ่มที่ tiny ก่อน (เบาสุด)

    conv = []                 # บทสนทนาสะสมทั้งสาย
    frames = []               # บัฟเฟอร์เสียงระหว่างอัด
    recording = False
    prev_a = prev_b = False   # ไว้จับ "ขอบขาขึ้น" (กด 1 ครั้ง ไม่ใช่กดค้าง)

    def audio_cb(indata, n, t, status):
        if recording:
            frames.append(indata.copy())

    stream = sd.InputStream(samplerate=16000, channels=1, dtype="float32", callback=audio_cb)
    stream.start()
    set_idle(pixels)
    print("✅ พร้อม | ปุ่ม A = เริ่ม/หยุดอัด | ปุ่ม B = ล้างเริ่มใหม่ (Ctrl+C ออก)")

    while True:
        a, b = read_buttons(buttons)

        # ----- ปุ่ม A: เริ่ม/หยุดอัด (กดสลับ) -----
        if a and not prev_a:
            if not recording:
                frames.clear()
                recording = True
                signal_listening(pixels, buzzer)         # ไฟน้ำเงิน+บี๊บ = กำลังอัด
            else:
                recording = False                        # กดอีกที = หยุด แล้ววิเคราะห์
                if frames:
                    audio = np.concatenate(frames).flatten()
                    text = transcribe(whisper, audio)
                    if text:
                        print(f"📝 ได้ยิน: {text}")
                        conv.append(text)
                        full = " ".join(conv)
                        if _enough(full):
                            color, conf = classify(full, model, vectorizer)
                            show_result(pixels, buzzer, color, conf)
                        else:
                            print("🟢 ฟังอยู่... (ข้อมูลยังไม่พอ)")
                            set_idle(pixels)

        # ----- ปุ่ม B: ล้างบทสนทนา เริ่มสายใหม่ -----
        if b and not prev_b:
            conv.clear()
            frames.clear()
            recording = False
            set_idle(pixels)
            print("📞 ล้างบทสนทนา เริ่มสายใหม่")

        prev_a, prev_b = a, b
        time.sleep(0.05)        # กันลูปวนเร็วเกินไป


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
app_unoq.py — เวอร์ชันรันบน Arduino UNO Q (ฝั่ง Linux) ผ่าน Arduino App Lab
ขั้นตอน: พูดใส่ไมโครโฟน -> Whisper ถอดเป็นข้อความ -> AI ตรวจมิจฉาชีพ
        -> ไฟ Modulino 3 สี + เสียงเตือนเมื่อแดง + บอก % ความมั่นใจ

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
    """เริ่มต้นโมดูล Modulino Pixels (ไฟ) + Buzzer (เสียง)"""
    # ตัวอย่าง (ชื่อจริงอาจต่างกันตามไลบรารีของ UNO Q):
    #   from modulino import ModulinoPixels, ModulinoBuzzer
    #   pixels = ModulinoPixels()
    #   buzzer = ModulinoBuzzer()
    #   return pixels, buzzer
    return None, None


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


def main():
    print("⏳ กำลังโหลดโมเดล...")
    model = joblib.load("scam_model.pkl")
    vectorizer = joblib.load("vectorizer.pkl")
    pixels, buzzer = setup_modulino()
    whisper = get_whisper("tiny")          # บนบอร์ดเริ่มที่ tiny ก่อน (เบาสุด)
    print("✅ พร้อมแล้ว — พูดใส่ไมค์ได้เลย (กด Ctrl+C เพื่อออก)")

    transcript = []                         # สะสมทั้งสายเหมือนฟังจนจบ
    while True:
        signal_listening(pixels, buzzer)    # ไฟน้ำเงิน + บี๊บ บอกว่า "พูดได้แล้ว"
        audio = record(6)
        text = transcribe(whisper, audio)
        if not text:
            continue
        print(f"📝 ได้ยิน: {text}")
        transcript.append(text)
        full = " ".join(transcript)

        # ข้อมูลยังน้อย -> รอฟังต่อ
        if len([t for t in text_tokenize(normalize_text(full)) if t.strip()]) < 3:
            print("🟢 ฟังอยู่... (ข้อมูลยังไม่พอ)")
            continue

        color, conf = classify(full, model, vectorizer)
        show_result(pixels, buzzer, color, conf)


if __name__ == "__main__":
    main()

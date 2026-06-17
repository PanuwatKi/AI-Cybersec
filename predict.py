# -*- coding: utf-8 -*-
"""
ระบบสาธิต (Demo) คัดกรองสายมิจฉาชีพแบบ 3 สี
- โหลดโมเดลที่เทรนไว้แล้ว (scam_model.pkl + vectorizer.pkl) มาใช้ทันที ไม่ต้องเทรนใหม่
- รองรับ 2 โหมดป้อนข้อมูล: (1) พิมพ์/วางข้อความ  (2) เสียงพูด -> ถอดเป็นข้อความด้วย Whisper (ออฟไลน์)
- ถ้าต่อบอร์ด Arduino จะส่งสีไปขึ้นไฟ Modulino Pixels + Buzzer

โดยปกติเป็น "โหมดสนทนา" = สะสมทุกบรรทัดของสายแล้ววิเคราะห์รวมกัน (เหมือนฟังจนจบสาย)
พิมพ์ 'จบ' เพื่อเริ่มสายใหม่ · ใส่ --single ถ้าอยากวิเคราะห์ทีละประโยคแบบเดิม

วิธีใช้:
    python predict.py                      # โหมดสนทนา (พิมพ์ทีละบรรทัด สะสมทั้งสาย)
    python predict.py --port COM3          # + ส่งสีไปบอร์ด Arduino
    python predict.py --listen             # อัดเสียงทีละรอบ สะสมทั้งสาย -> วิเคราะห์
    python predict.py --wav call.wav        # วิเคราะห์จากไฟล์เสียงที่บันทึกไว้ (ทีเดียวจบ)
    python predict.py --single             # วิเคราะห์ทีละประโยค (ปิดการสะสม)
    python predict.py --listen --denoise   # อัดเสียง + ลดเสียงรบกวนก่อนถอด (ห้องอื้ออึง)

ไลบรารีโหมดเสียง (ติดตั้งเพิ่มเมื่อจะใช้ ดู requirements-audio.txt):
    pip install faster-whisper sounddevice soundfile

============================ แผนผังโครงสร้างโค้ด (Code Map) ============================
  text_tokenize()      : ตัดประโยคไทยเป็นคำ ๆ (ต้องชื่อเดียวกับตอนเทรน vectorizer)
  ANSI / *_THRESHOLD   : ค่าคงที่ — โค้ดสีบนจอ และเกณฑ์ % ที่ใช้แบ่งแดง/เหลือง/เขียว
  classify()           : หัวใจของระบบ — รับข้อความ คืน สี + % ความมั่นใจ
  _scam_logodds()      : ตัวช่วยคำนวณความเอนเอียงไปทางมิจฉาชีพ (ใช้ใน explain_words)
  explain_words()      : บอกว่า "คำไหน" ทำให้ AI ตัดสินว่าเป็นมิจฉาชีพ
  show_and_send()      : แสดงผลเป็นแถบสีบนจอ + ส่งสัญญาณสีไปบอร์ด Arduino
  Conversation         : คลาสเก็บบทสนทนาสะสมทั้งสาย (จำหลายบรรทัด + ค่าสูงสุด)
  analyze_conversation(): วิเคราะห์บทสนทนาทั้งหมดที่สะสมมา
  load_whisper() / transcribe() / record_mic() : ส่วนโหมดเสียง (เสียง -> ข้อความ)
  main()               : ตัวควบคุมหลัก อ่าน argument แล้วเลือกโหมด (พิมพ์/เสียง/ไฟล์)
=====================================================================================
"""
import argparse
import math
import os
import re
import sys
import joblib
from pythainlp.tokenize import word_tokenize

# ทำให้พิมพ์ภาษาไทย/อิโมจิบน Windows ไม่ error (สำคัญตอนเดโมบนเครื่องอื่น)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
os.system("")  # เปิดใช้สีบนหน้าจอ Terminal ของ Windows

# โค้ดสีสำหรับแสดงผลเป็นแถบสีบนจอ (เห็นแดง/เหลือง/เขียวชัด แม้ยังไม่ต่อบอร์ด)
ANSI = {
    "RED": "\033[1;97;41m",     # ตัวอักษรขาวพื้นแดง
    "YELLOW": "\033[1;30;43m",  # ตัวอักษรดำพื้นเหลือง
    "GREEN": "\033[1;97;42m",   # ตัวอักษรขาวพื้นเขียว
    "RESET": "\033[0m",
}


# ฟังก์ชันเหล่านี้ต้อง "ชื่อเดียวกัน" กับตอนเทรน เพราะ vectorizer.pkl อ้างถึง
def text_tokenize(text):
    if not isinstance(text, str):
        return []
    return word_tokenize(text, engine="newmm")


_REPEAT_RE = re.compile(r"(.{2,15}?)\1{2,}")
def normalize_text(text):
    """ตัดไม้ยมก (ๆ) + ยุบคำซ้ำติดกัน 3 ครั้งขึ้นไป (คุณคุณคุณ -> คุณ) + พิมพ์เล็ก"""
    if not isinstance(text, str):
        return ""
    text = text.lower().replace("ๆ", " ")
    return _REPEAT_RE.sub(r"\1", text)


# เกณฑ์แบ่งสีจาก % โอกาสเป็นมิจฉาชีพ (ปรับได้ตามผลทดสอบจริง)
RED_THRESHOLD = 70     # >= 70%   -> สีแดง  (เสี่ยงสูงมาก)
YELLOW_THRESHOLD = 40  # 40-69%   -> สีเหลือง (น่าสงสัย) ;  < 40% -> สีเขียว (ปลอดภัย)


def classify(text, model, vectorizer):
    """รับข้อความ คืนผลเป็น dict: สี / ป้ายข้อความ / % ความมั่นใจว่าเป็นมิจฉาชีพ"""
    vec = vectorizer.transform([text])
    proba = model.predict_proba(vec)[0]

    # หา index ของ label 1 (มิจฉาชีพ) เผื่อกรณีลำดับ class ไม่ใช่ [0, 1]
    classes = list(model.classes_)
    scam_idx = classes.index(1) if 1 in classes else 1
    scam_confidence = proba[scam_idx] * 100

    if scam_confidence >= RED_THRESHOLD:
        return {"color": "RED", "emoji": "🔴",
                "label": "เสี่ยงเป็นมิจฉาชีพสูงมาก", "scam_confidence": scam_confidence}
    elif scam_confidence >= YELLOW_THRESHOLD:
        return {"color": "YELLOW", "emoji": "🟡",
                "label": "น่าสงสัย มีโอกาสเป็นมิจฉาชีพอยู่บ้าง", "scam_confidence": scam_confidence}
    else:
        return {"color": "GREEN", "emoji": "🟢",
                "label": "ปลอดภัย โอกาสเป็นมิจฉาชีพน้อยมาก", "scam_confidence": scam_confidence}


def _scam_logodds(text, model, vectorizer):
    """ค่าความเอนเอียงไปทาง 'มิจฉาชีพ' ในเชิง log-odds (ไวต่อการเปลี่ยนแปลงกว่า %)
    คำนวณจาก predict_proba เพื่อให้ใช้ได้กับทุกโมเดล รวมถึงโมเดลที่ผ่าน calibration"""
    p = model.predict_proba(vectorizer.transform([text]))[0]
    classes = list(model.classes_)
    s = classes.index(1) if 1 in classes else 1
    o = classes.index(0) if 0 in classes else 0
    eps = 1e-9
    return math.log(p[s] + eps) - math.log(p[o] + eps)


def explain_words(text, model, vectorizer, topn=5):
    """อธิบายว่า 'คำไหน' ทำให้ AI คิดว่าเป็นมิจฉาชีพ
    วิธี (occlusion): ลองตัดแต่ละคำออก แล้วดูว่าความเอนเอียงไปทางมิจฉาชีพลดลงเท่าไหร่
    คำที่ตัดออกแล้วลดมาก = คำนั้นเป็นตัวบ่งชี้มิจฉาชีพมาก (อธิบายกรรมการง่าย)"""
    base = _scam_logodds(text, model, vectorizer)
    contribs, seen = [], set()
    for tok in text_tokenize(text):
        tok = tok.strip()
        if not tok or tok in seen:
            continue
        seen.add(tok)
        reduced = text.replace(tok, " ")
        drop = base - _scam_logodds(reduced, model, vectorizer)
        if drop > 0.1:  # ตัดคำนี้ออกแล้วความเอนเอียงไปทางมิจฉาชีพลดลงจริง
            contribs.append((tok, drop))
    contribs.sort(key=lambda x: x[1], reverse=True)
    return contribs[:topn]


def show_and_send(text, model, vectorizer, ser):
    """วิเคราะห์ข้อความ แสดงผลเป็นแถบสี และส่งสีไปบอร์ด (ถ้าต่อไว้)"""
    if not text.strip():
        return
    result = classify(text, model, vectorizer)
    color = result["color"]
    bar = f" {result['emoji']}  {result['label']}  ({result['scam_confidence']:.1f}%) "
    print(f"\n{ANSI.get(color, '')}{bar}{ANSI['RESET']}")

    # ถ้าไม่ใช่สีเขียว โชว์คำที่ทำให้ AI สงสัย
    if color != "GREEN":
        risky = explain_words(text, model, vectorizer)
        if risky:
            words = "  ".join(f"{w}" for w, _ in risky)
            print(f"   🔍 คำที่ทำให้สงสัย: {words}")
    if ser:
        ser.write(color[0].encode())  # ส่ง 'R' / 'Y' / 'G' ไปขึ้นไฟ Arduino


# ---------------- โหมดสนทนา: วิเคราะห์ทั้งสายแบบสะสมหลายบรรทัด ----------------
class Conversation:
    """เก็บบทสนทนาสะสมทั้งสาย เพื่อวิเคราะห์รวมกัน (เหมือนฟังสายจริงจนจบ)
    - .add()   : เพิ่มประโยคใหม่ที่คู่สนทนาพูด
    - .peak    : ค่าความเสี่ยงสูงสุดที่เคยขึ้นในสายนี้ (เตือนแล้วไม่ลืม)
    - .reset() : เริ่มสายใหม่ (ล้างความจำ)"""
    def __init__(self):
        self.lines = []
        self.peak = 0.0

    def add(self, utterance):
        u = utterance.strip()
        if u:
            self.lines.append(u)

    def reset(self):
        self.lines.clear()
        self.peak = 0.0

    @property
    def transcript(self):
        return " ".join(self.lines)


def analyze_conversation(conv, model, vectorizer, ser):
    """วิเคราะห์ 'บทสนทนาทั้งหมดที่สะสมมา' แล้วแสดงผล + ส่งสีไปบอร์ด"""
    text = conv.transcript
    tokens = [t for t in text_tokenize(normalize_text(text)) if t.strip()]

    # ข้อมูลยังน้อยเกินไป (เช่น เพิ่งทักทาย/เรียกชื่อซ้ำ ๆ) -> ยังไม่ฟันธง รอฟังต่อ
    if len(tokens) < 3:
        print(f"\n{ANSI['GREEN']} 🟢  ฟังอยู่... (ข้อมูลยังไม่พอจะตัดสิน) {ANSI['RESET']}")
        if ser:
            ser.write(b"G")
        return

    result = classify(text, model, vectorizer)
    conf = result["scam_confidence"]
    conv.peak = max(conv.peak, conf)  # จำค่าสูงสุด: ถ้าเคยเสี่ยงสูงแล้ว ให้คงการเตือนไว้
    color = result["color"]
    bar = (f" {result['emoji']}  {result['label']}  "
           f"(ล่าสุด {conf:.1f}% / สูงสุดในสายนี้ {conv.peak:.1f}%) ")
    print(f"\n{ANSI.get(color, '')}{bar}{ANSI['RESET']}")

    if color != "GREEN":
        risky = explain_words(text, model, vectorizer)
        if risky:
            print(f"   🔍 คำที่ทำให้สงสัย: {'  '.join(w for w, _ in risky)}")
    if ser:
        ser.write(color[0].encode())


# ---------------- โหมดเสียง (โหลดเฉพาะตอนใช้ เพื่อให้โหมดพิมพ์เบาและเสถียร) ----------------
def load_whisper(model_size):
    """โหลดโมเดลถอดเสียง Whisper (เรียกครั้งเดียวพอ เพราะโหลดช้า)"""
    from faster_whisper import WhisperModel
    print(f"⏳ กำลังโหลดโมเดลถอดเสียง Whisper ({model_size}) ... (ครั้งแรกอาจดาวน์โหลดสักครู่)")
    return WhisperModel(model_size, device="cpu", compute_type="int8")


# คำใบ้ให้ Whisper รู้ว่าจะเจอศัพท์แนวไหน -> ถอดคำสำคัญแม่นขึ้น
SCAM_PROMPT = ("บทสนทนาทางโทรศัพท์ เกี่ยวกับ ธนาคาร บัญชี โอนเงิน รหัส OTP "
               "ตำรวจ คดี ฟอกเงิน อายัด พัสดุ ศุลกากร กดลิงก์ ลงทุน กำไร รางวัล ภาษี")


def transcribe(whisper_model, audio):
    """audio = path ไฟล์เสียง หรือ numpy array (float32 16kHz mono)
    - initial_prompt : ป้อนคำศัพท์แนวมิจฉาชีพล่วงหน้า ช่วยให้ถอดคำสำคัญแม่นขึ้น
    - vad_filter     : กรองช่วงเงียบ/ที่ไม่ใช่เสียงพูดออกก่อนถอด -> ผลนิ่งขึ้น"""
    segments, _ = whisper_model.transcribe(
        audio, language="th",
        initial_prompt=SCAM_PROMPT,
        vad_filter=True,
    )
    return " ".join(seg.text for seg in segments).strip()


def record_mic(seconds, samplerate=16000, device=None):
    """อัดเสียงจากไมโครโฟนตามจำนวนวินาทีที่กำหนด คืนเป็นคลื่นเสียง (numpy array)"""
    import sounddevice as sd
    print(f"🎙️  กำลังอัดเสียง {seconds} วินาที... พูดได้เลย")
    audio = sd.rec(int(seconds * samplerate), samplerate=samplerate,
                   channels=1, dtype="float32", device=device)
    sd.wait()
    return audio.flatten()


def denoise_audio(audio, samplerate=16000):
    """ลดเสียงรบกวนพื้นหลังด้วย noisereduce (spectral gating) ก่อนส่งเข้า Whisper
    ช่วยตอนอยู่ในที่มีเสียงอื้ออึง เช่น ห้องแข่ง (ต้องติดตั้ง noisereduce ก่อน)"""
    import noisereduce as nr
    return nr.reduce_noise(y=audio, sr=samplerate)


def main():
    """ตัวควบคุมหลัก: อ่าน argument -> โหลดโมเดล -> เลือกโหมดทำงาน (ไฟล์เสียง/อัดสด/พิมพ์)"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="พอร์ตบอร์ด Arduino เช่น COM3 (ไม่ใส่ = ไม่ต่อฮาร์ดแวร์)")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--listen", action="store_true", help="โหมดอัดเสียงจากไมโครโฟน")
    parser.add_argument("--wav", help="วิเคราะห์จากไฟล์เสียง เช่น call.wav")
    parser.add_argument("--seconds", type=int, default=8, help="ความยาวที่อัดต่อรอบในโหมด --listen")
    parser.add_argument("--model", default="small", help="ขนาดโมเดล Whisper: tiny/base/small/medium")
    parser.add_argument("--device", type=int, help="หมายเลขไมโครโฟน (ดูได้จาก --list-devices)")
    parser.add_argument("--list-devices", action="store_true", help="แสดงรายชื่อไมโครโฟนทั้งหมดแล้วออก")
    parser.add_argument("--single", action="store_true",
                        help="วิเคราะห์ทีละประโยค (ปิดโหมดสะสมบทสนทนา)")
    parser.add_argument("--denoise", action="store_true",
                        help="ลดเสียงรบกวนก่อนถอดเสียง (ต้องติดตั้ง noisereduce)")
    args = parser.parse_args()

    # โหมดดูรายชื่อไมค์: ใช้เลือกไมค์ก่อนเดโม เช่น ไมค์เว็บแคม vs ไมค์โน้ตบุ๊ก
    if args.list_devices:
        import sounddevice as sd
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                print(f"  [{i}] {d['name']}")
        print("\nใช้ไมค์ที่ต้องการด้วย:  python predict.py --listen --device <หมายเลข>")
        return

    print("⏳ กำลังโหลดโมเดลคัดกรอง...")
    try:
        model = joblib.load("scam_model.pkl")
        vectorizer = joblib.load("vectorizer.pkl")
    except FileNotFoundError:
        print("❌ ไม่พบไฟล์โมเดล (scam_model.pkl / vectorizer.pkl)")
        print("   กรุณารัน  python train_model.py  เพื่อสร้างโมเดลก่อนนะครับ")
        return
    print("✅ โหลดโมเดลเรียบร้อย")

    ser = None
    if args.port:
        import serial  # ต้องติดตั้ง pyserial ก่อน
        ser = serial.Serial(args.port, args.baud, timeout=1)
        print(f"🔌 ต่อบอร์ดที่ {args.port} เรียบร้อย")

    reset_words = {"จบ", "จบสาย", "สายใหม่", "ล้าง", "reset", "end"}
    try:
        # --- โหมดไฟล์เสียง (วิเคราะห์ทีเดียวจบ) ---
        if args.wav:
            wmodel = load_whisper(args.model)
            text = transcribe(wmodel, args.wav)
            print(f"📝 ถอดเสียงได้: {text}")
            show_and_send(text, model, vectorizer, ser)

        # --- โหมดอัดเสียงสด (สะสมทั้งสาย) ---
        elif args.listen:
            wmodel = load_whisper(args.model)
            conv = Conversation()
            print("\n🔮 === โหมดเสียง (สะสมทั้งสาย) — กด Enter เพื่ออัด 1 รอบ ===")
            print("   พิมพ์ 'จบ' = เริ่มสายใหม่ | 'exit' = ออก")
            while True:
                cmd = input("\nกด Enter เพื่อเริ่มอัด (หรือพิมพ์ จบ/exit) : ").strip()
                if cmd.lower() == "exit":
                    break
                if cmd.lower() in reset_words:
                    conv.reset(); print("📞 เริ่มสายใหม่"); continue
                audio = record_mic(args.seconds, device=args.device)
                if args.denoise:
                    audio = denoise_audio(audio)
                text = transcribe(wmodel, audio)
                print(f"📝 ถอดเสียงได้: {text}")
                if args.single:
                    show_and_send(text, model, vectorizer, ser)
                else:
                    conv.add(text)
                    analyze_conversation(conv, model, vectorizer, ser)

        # --- โหมดพิมพ์ข้อความ (ค่าเริ่มต้น = สะสมบทสนทนา) ---
        else:
            conv = Conversation()
            if args.single:
                print("\n🔮 === คัดกรองทีละประโยค (พิมพ์ 'exit' เพื่อออก) ===")
            else:
                print("\n🔮 === โหมดสนทนา: พิมพ์ทีละบรรทัดเหมือนฟังสายจริง ===")
                print("   พิมพ์ 'จบ' = เริ่มสายใหม่ | 'exit' = ออก")
            while True:
                user_input = input("\nคู่สนทนาพูดว่า : ").strip()
                if user_input.lower() == "exit":
                    break
                if not user_input:
                    continue
                if not args.single and user_input.lower() in reset_words:
                    conv.reset(); print("📞 เริ่มสายใหม่"); continue
                if args.single:
                    show_and_send(user_input, model, vectorizer, ser)
                else:
                    conv.add(user_input)
                    analyze_conversation(conv, model, vectorizer, ser)
    finally:
        if ser:
            ser.close()
        print("👋 ปิดระบบแล้ว")


if __name__ == "__main__":
    main()

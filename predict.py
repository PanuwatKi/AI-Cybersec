# -*- coding: utf-8 -*-
"""
ระบบสาธิต (Demo) คัดกรองสายมิจฉาชีพแบบ 3 สี
- โหลดโมเดลที่เทรนไว้แล้ว (scam_model.pkl + vectorizer.pkl) มาใช้ทันที ไม่ต้องเทรนใหม่
- รองรับ 2 โหมดป้อนข้อมูล: (1) พิมพ์/วางข้อความ  (2) เสียงพูด -> ถอดเป็นข้อความด้วย Whisper (ออฟไลน์)
- ถ้าต่อบอร์ด Arduino จะส่งสีไปขึ้นไฟ Modulino Pixels + Buzzer

วิธีใช้:
    python predict.py                      # โหมดพิมพ์ข้อความ (เสถียรสุด ใช้เป็นโหมดสำรองเสมอ)
    python predict.py --port COM3          # โหมดพิมพ์ + ส่งสีไปบอร์ด Arduino
    python predict.py --listen             # โหมดอัดเสียงจากไมค์ -> ถอดเสียง -> วิเคราะห์
    python predict.py --wav call.wav        # วิเคราะห์จากไฟล์เสียงที่บันทึกไว้

ไลบรารีโหมดเสียง (ติดตั้งเพิ่มเมื่อจะใช้ ดู requirements-audio.txt):
    pip install faster-whisper sounddevice soundfile
"""
import argparse
import os
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


# ฟังก์ชันตัดคำต้อง "ชื่อเดียวกัน" กับตอนเทรน เพราะ vectorizer.pkl อ้างถึงฟังก์ชันนี้
def text_tokenize(text):
    if not isinstance(text, str):
        return []
    return word_tokenize(text, engine="newmm")


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
    """ค่าความเอนเอียงไปทาง 'มิจฉาชีพ' ในเชิง log-odds (ไวต่อการเปลี่ยนแปลงกว่า %)"""
    lp = model.predict_log_proba(vectorizer.transform([text]))[0]
    classes = list(model.classes_)
    s = classes.index(1) if 1 in classes else 1
    o = classes.index(0) if 0 in classes else 0
    return lp[s] - lp[o]


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


# ---------------- โหมดเสียง (โหลดเฉพาะตอนใช้ เพื่อให้โหมดพิมพ์เบาและเสถียร) ----------------
def load_whisper(model_size):
    from faster_whisper import WhisperModel
    print(f"⏳ กำลังโหลดโมเดลถอดเสียง Whisper ({model_size}) ... (ครั้งแรกอาจดาวน์โหลดสักครู่)")
    return WhisperModel(model_size, device="cpu", compute_type="int8")


def transcribe(whisper_model, audio):
    """audio = path ไฟล์เสียง หรือ numpy array (float32 16kHz mono)"""
    segments, _ = whisper_model.transcribe(audio, language="th")
    return " ".join(seg.text for seg in segments).strip()


def record_mic(seconds, samplerate=16000, device=None):
    import sounddevice as sd
    print(f"🎙️  กำลังอัดเสียง {seconds} วินาที... พูดได้เลย")
    audio = sd.rec(int(seconds * samplerate), samplerate=samplerate,
                   channels=1, dtype="float32", device=device)
    sd.wait()
    return audio.flatten()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="พอร์ตบอร์ด Arduino เช่น COM3 (ไม่ใส่ = ไม่ต่อฮาร์ดแวร์)")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--listen", action="store_true", help="โหมดอัดเสียงจากไมโครโฟน")
    parser.add_argument("--wav", help="วิเคราะห์จากไฟล์เสียง เช่น call.wav")
    parser.add_argument("--seconds", type=int, default=8, help="ความยาวที่อัดต่อรอบในโหมด --listen")
    parser.add_argument("--model", default="small", help="ขนาดโมเดล Whisper: tiny/base/small/medium")
    parser.add_argument("--device", type=int, help="หมายเลขไมโครโฟน (ดูได้จาก --list-devices)")
    parser.add_argument("--list-devices", action="store_true", help="แสดงรายชื่อไมโครโฟนทั้งหมดแล้วออก")
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

    try:
        # --- โหมดไฟล์เสียง ---
        if args.wav:
            wmodel = load_whisper(args.model)
            text = transcribe(wmodel, args.wav)
            print(f"📝 ถอดเสียงได้: {text}")
            show_and_send(text, model, vectorizer, ser)

        # --- โหมดอัดเสียงสด ---
        elif args.listen:
            wmodel = load_whisper(args.model)
            print("\n🔮 === โหมดเสียง: กด Enter เพื่ออัดเสียง 1 รอบ (พิมพ์ 'exit' เพื่อออก) ===")
            while True:
                cmd = input("\nกด Enter เพื่อเริ่มอัด (หรือพิมพ์ exit) : ").strip()
                if cmd.lower() == "exit":
                    break
                audio = record_mic(args.seconds, device=args.device)
                text = transcribe(wmodel, audio)
                print(f"📝 ถอดเสียงได้: {text}")
                show_and_send(text, model, vectorizer, ser)

        # --- โหมดพิมพ์ข้อความ (ค่าเริ่มต้น / โหมดสำรองเสมอ) ---
        else:
            print("\n🔮 === ระบบคัดกรองสายมิจฉาชีพ 3 สี (พิมพ์ 'exit' เพื่อออก) ===")
            while True:
                user_input = input("\nวางบทสนทนา/ข้อความที่ต้องการตรวจ : ").strip()
                if user_input.lower() == "exit":
                    break
                show_and_send(user_input, model, vectorizer, ser)
    finally:
        if ser:
            ser.close()
        print("👋 ปิดระบบแล้ว")


if __name__ == "__main__":
    main()

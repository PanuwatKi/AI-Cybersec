# -*- coding: utf-8 -*-
"""
applab_demo.py — วางเป็น python/main.py แล้วกด Run
ทำ 2 อย่าง: (1) โชว์ AI วิเคราะห์มิจฉาชีพ "สด ๆ บนบอร์ด" ในแท็บ Python (พิสูจน์ Edge AI)
            (2) พิมพ์ API ของ Leds/audio/Bridge ออกมา เพื่อต่อยอดทำไฟ/ไมค์จริงทีหลัง
ทำงานได้ทันทีโดยใช้แค่ไลบรารีที่ลงไปแล้ว — ไม่ต้องมี Modulino/ไมค์
"""
import os
import re
import time
import joblib
from arduino.app_utils import App
import arduino.app_utils as au
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


here = os.path.dirname(os.path.abspath(__file__))
model = joblib.load(os.path.join(here, "scam_model.pkl"))
vectorizer = joblib.load(os.path.join(here, "vectorizer.pkl"))
print("=== MODEL LOADED OK (AI พร้อมบนบอร์ด) ===")

# พิมพ์ API ของตัวช่วยคุมไฟ/ไมค์ (ส่งบรรทัด API ... ให้ผม เพื่อทำไฟจริงต่อ)
for n in ["Leds", "leds", "ledmatrix", "audio", "Bridge", "call", "provide"]:
    obj = getattr(au, n, None)
    members = [x for x in dir(obj) if not x.startswith("_")] if obj is not None else "NONE"
    print(f"API {n} -> {members}")

TESTS = [
    "ผมโทรจากตำรวจ บัญชีคุณพัวพันคดีฟอกเงิน โอนเงินมาตรวจสอบด่วน",
    "สวัสดีครับ ไม่ทราบว่าโทรมาจากไหนครับ",
    "ลงทุนกับเราการันตีกำไรสามสิบเปอร์เซ็นต์ต่อเดือน โอนเลย",
    "แม่ฝากซื้อไข่ไก่กับนมด้วยนะ",
    "เรียนคุณลูกค้า บัญชีถูกอายัด แจ้งรหัส OTP ด่วน",
    "เย็นนี้ว่างไหม ไปกินข้าวกัน",
]
_i = 0


def loop():
    """ถูกเรียกซ้ำโดย App — โชว์ผลวิเคราะห์ทีละประโยคทุก 3 วินาที"""
    global _i
    t = TESTS[_i % len(TESTS)]
    conf = model.predict_proba(vectorizer.transform([t]))[0][list(model.classes_).index(1)] * 100
    color = "RED   " if conf >= 70 else ("YELLOW" if conf >= 40 else "GREEN ")
    print(f"[{color}] {conf:5.1f}%  {t}")
    _i += 1
    time.sleep(3)


App.run(user_loop=loop)

# -*- coding: utf-8 -*-
"""
board_selftest.py — ทดสอบโมเดลบนบอร์ดด้วย "ประโยคในตัว" (ไม่ต้องพิมพ์ภาษาไทยใน terminal)
แก้ปัญหา terminal บนบอร์ดพิมพ์ไทยไม่ได้ (ขึ้น ?) — เพราะประโยคทดสอบฝังในไฟล์นี้แล้ว

รัน:  python3 board_selftest.py
(ป้ายสี RED/YELLOW/GREEN เป็นตัวอังกฤษ เผื่อ terminal แสดงไทยไม่ได้ จะได้ยังอ่าน % รู้เรื่อง)
"""
import os
import re
import joblib
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

TESTS = [
    "ผมโทรจากตำรวจ บัญชีคุณพัวพันคดีฟอกเงิน โอนเงินมาตรวจสอบด่วน",
    "ลงทุนกับเราการันตีกำไรสามสิบเปอร์เซ็นต์ต่อเดือน โอนเลย",
    "พัสดุตกค้าง กดลิงก์ชำระค่าปรับด่วน",
    "เรียนคุณลูกค้า บัญชีถูกอายัด แจ้งรหัส OTP ด่วน",
    "สวัสดีครับ ไม่ทราบว่าโทรมาจากไหนครับ",
    "แม่ฝากซื้อไข่ไก่กับนมด้วยนะ",
    "เย็นนี้ว่างไหม ไปกินข้าวกัน",
]

print("=== TEST MODEL ON BOARD ===")
for t in TESTS:
    conf = model.predict_proba(vectorizer.transform([t]))[0][list(model.classes_).index(1)] * 100
    color = "RED   " if conf >= 70 else ("YELLOW" if conf >= 40 else "GREEN ")
    print(f"[{color}] {conf:5.1f}%  {t}")
print("=== DONE ===")

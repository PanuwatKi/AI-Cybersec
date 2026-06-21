# -*- coding: utf-8 -*-
"""
board_check.py — ทดสอบบน UNO Q "โดยใช้แค่ตัวบอร์ด" (ยังไม่ต้องมี Modulino/ไมค์)
ใช้ยืนยัน 3 อย่างที่เสี่ยงสุดก่อนวันแข่ง:
  1) ลงไลบรารีบนบอร์ดได้ (scikit-learn / joblib / pythainlp)
  2) โหลดโมเดล .pkl ได้ (เวอร์ชัน sklearn ตรงกัน)
  3) วิเคราะห์ข้อความได้จริงบนบอร์ด

วิธีใช้ (ใน Terminal ของบอร์ด — ต้องอยู่โฟลเดอร์เดียวกับ .pkl เช่น python/):
    python3 -m pip install scikit-learn joblib pythainlp
    python3 board_check.py
พิมพ์ประโยคทดสอบ แล้วดูผลเป็น 3 สี + %  (พิมพ์ exit เพื่อออก)
"""
import os
import re
import joblib
from pythainlp.tokenize import word_tokenize


# ต้องนิยามให้ "ชื่อตรง" กับตอนเทรน เพราะ vectorizer.pkl อ้างถึง 2 ฟังก์ชันนี้
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
print("⏳ กำลังโหลดโมเดล...")
model = joblib.load(os.path.join(here, "scam_model.pkl"))
vectorizer = joblib.load(os.path.join(here, "vectorizer.pkl"))
print("✅ โหลดสำเร็จ! โมเดลรันบนบอร์ดได้ — ลองพิมพ์ข้อความได้เลย (exit เพื่อออก)\n")

while True:
    t = input("ข้อความ : ").strip()
    if t.lower() == "exit":
        break
    if not t:
        continue
    conf = model.predict_proba(vectorizer.transform([t]))[0][list(model.classes_).index(1)] * 100
    color = "🔴 แดง" if conf >= 70 else ("🟡 เหลือง" if conf >= 40 else "🟢 เขียว")
    print(f"  {color}  (โอกาสเป็นมิจฉาชีพ {conf:.1f}%)\n")

# -*- coding: utf-8 -*-
"""
applab_demo.py — แทนที่ python/main.py ทั้งไฟล์ด้วยอันนี้ แล้วกด Run
ทำ 3 อย่างในไฟล์เดียว (มี App.run ครั้งเดียวเท่านั้น!):
  1) โหลดโมเดล -> พิสูจน์ว่า AI พร้อมบนบอร์ด
  2) พิมพ์ API ของ audio/Leds/Bridge แบบละเอียด (ก๊อปบล็อกพวกนี้ส่งให้ Claude เขียนตัวเต็มต่อ)
  3) วนโชว์การวิเคราะห์มิจฉาชีพสด ๆ ทีละประโยค (สี + %)
"""
import os
import re
import time
import inspect
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


# ---------- 1) โหลดโมเดล ----------
here = os.path.dirname(os.path.abspath(__file__))
model = joblib.load(os.path.join(here, "scam_model.pkl"))
vectorizer = joblib.load(os.path.join(here, "vectorizer.pkl"))
print("=== MODEL LOADED OK (AI พร้อมบนบอร์ด) ===")


# ---------- 2) พิมพ์ API ละเอียด (ก๊อปส่งให้ Claude) ----------
def probe(name):
    print("======== " + name + " ========")
    obj = getattr(au, name, None)
    if obj is None:
        print("  NONE"); return
    print("  type:", type(obj).__name__)
    try:
        print("  sig:", inspect.signature(obj))
    except Exception:
        pass
    for m in [x for x in dir(obj) if not x.startswith("_")]:
        sub = getattr(obj, m, None)
        if callable(sub):
            sig = ""
            try:
                sig = str(inspect.signature(sub))
            except Exception:
                pass
            doc = (getattr(sub, "__doc__", "") or "").strip().replace("\n", " ")[:70]
            print("   ." + m + sig + "   " + doc)
        else:
            print("   ." + m + " = " + type(sub).__name__)

print("\n##### API DISCOVERY (copy ทั้งหมดส่งให้ Claude) #####")
for n in ["audio", "Leds", "leds", "ledmatrix", "Bridge", "bridge", "call", "provide", "brick"]:
    try:
        probe(n)
    except Exception as e:
        print("########", n, "ERR", e)
print("##### END API DISCOVERY #####\n")


# ---------- 3) โชว์ AI วิเคราะห์สด ----------
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
    global _i
    t = TESTS[_i % len(TESTS)]
    conf = model.predict_proba(vectorizer.transform([t]))[0][list(model.classes_).index(1)] * 100
    color = "RED   " if conf >= 70 else ("YELLOW" if conf >= 40 else "GREEN ")
    print("[" + color + "] " + ("%5.1f" % conf) + "%  " + t)
    _i += 1
    time.sleep(3)


App.run(user_loop=loop)

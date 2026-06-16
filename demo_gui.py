# -*- coding: utf-8 -*-
"""
หน้าจอสาธิต (GUI) ระบบคัดกรองสายมิจฉาชีพ 3 สี — เหมาะกับใช้ตอนนำเสนอ
แสดงแถบสีใหญ่ + เปอร์เซ็นต์ + ข้อความที่วิเคราะห์ + คำที่ทำให้ AI สงสัย

วิธีใช้:
    python demo_gui.py                  # พิมพ์ข้อความ + ปุ่มอัดเสียง
    python demo_gui.py --port COM3      # ส่งสีไปบอร์ด Arduino ด้วย
    python demo_gui.py --model base     # เลือกขนาดโมเดลถอดเสียง (tiny/base/small/medium)
กด F11 = เต็มจอ / Esc = ออกจากเต็มจอ

============================ แผนผังโครงสร้างโค้ด (Code Map) ============================
  text_tokenize()        : ตัดคำไทย (ต้องชื่อเดียวกับตอนเทรน เพื่อโหลด vectorizer.pkl ได้)
  classify/explain_words : ยืมมาจาก predict.py (ใช้ตรรกะวิเคราะห์ชุดเดียวกัน ไม่เขียนซ้ำ)
  คลาส ScamDetectorApp   : ตัวหน้าจอทั้งหมด
     __init__()          : วางหน้าตา (แถบสี / ช่องข้อความ / คำที่สงสัย / ปุ่ม)
     _set_result()       : เปลี่ยนสีและข้อความบนหน้าจอตามผลที่ได้
     analyze()           : วิเคราะห์ข้อความ -> อัปเดตหน้าจอ -> ส่งสีไปบอร์ด
     analyze_text()      : ปุ่ม/Enter จากช่องพิมพ์
     record_async()/_record_worker() : ปุ่มอัดเสียง (ทำงานคนละเธรด ไม่ให้จอค้าง)
  main()                 : โหลดโมเดล แล้วเปิดหน้าต่าง
=====================================================================================
"""
import argparse
import threading
import tkinter as tk

import joblib
from pythainlp.tokenize import word_tokenize


# ต้องนิยาม text_tokenize ในไฟล์ที่รันเป็นหลัก เพื่อให้ joblib โหลด vectorizer.pkl ได้
def text_tokenize(text):
    if not isinstance(text, str):
        return []
    return word_tokenize(text, engine="newmm")


# ใช้ตรรกะวิเคราะห์ชุดเดียวกับ predict.py (ไม่เขียนซ้ำ)
from predict import classify, explain_words

BG = {"RED": "#c62828", "YELLOW": "#f9a825", "GREEN": "#2e7d32", "IDLE": "#455a64"}
FG = {"RED": "#ffffff", "YELLOW": "#212121", "GREEN": "#ffffff", "IDLE": "#ffffff"}
FONT = "Tahoma"


class ScamDetectorApp:
    def __init__(self, root, model, vectorizer, ser=None, whisper_size="small"):
        self.root = root
        self.model = model
        self.vectorizer = vectorizer
        self.ser = ser
        self.whisper_size = whisper_size
        self.whisper = None  # โหลดตอนกดอัดเสียงครั้งแรก

        root.title("🛡️ ระบบ AI คัดกรองสายมิจฉาชีพ")
        root.geometry("960x680")
        root.configure(bg="#263238")

        # --- แถบผลลัพธ์สีใหญ่ ---
        self.result_frame = tk.Frame(root, bg=BG["IDLE"], height=320)
        self.result_frame.pack(fill="x")
        self.result_frame.pack_propagate(False)

        self.emoji_lbl = tk.Label(self.result_frame, text="🛡️", font=(FONT, 80),
                                  bg=BG["IDLE"], fg=FG["IDLE"])
        self.emoji_lbl.pack(pady=(28, 0))
        self.status_lbl = tk.Label(self.result_frame, text="พร้อมตรวจสอบ",
                                   font=(FONT, 26, "bold"), bg=BG["IDLE"], fg=FG["IDLE"])
        self.status_lbl.pack()
        self.pct_lbl = tk.Label(self.result_frame, text="", font=(FONT, 22),
                                bg=BG["IDLE"], fg=FG["IDLE"])
        self.pct_lbl.pack(pady=(4, 0))

        # --- ข้อความที่วิเคราะห์ ---
        tk.Label(root, text="ข้อความที่วิเคราะห์:", font=(FONT, 13, "bold"),
                 bg="#263238", fg="#b0bec5").pack(anchor="w", padx=24, pady=(18, 2))
        self.text_lbl = tk.Label(root, text="—", font=(FONT, 15), wraplength=900,
                                 justify="left", bg="#263238", fg="#eceff1")
        self.text_lbl.pack(anchor="w", padx=24)

        # --- คำที่ทำให้สงสัย ---
        tk.Label(root, text="🔍 คำที่ทำให้ AI สงสัย:", font=(FONT, 13, "bold"),
                 bg="#263238", fg="#b0bec5").pack(anchor="w", padx=24, pady=(14, 2))
        self.words_lbl = tk.Label(root, text="—", font=(FONT, 16, "bold"), wraplength=900,
                                  justify="left", bg="#263238", fg="#ffd54f")
        self.words_lbl.pack(anchor="w", padx=24)

        # --- ช่องพิมพ์ + ปุ่ม ---
        bottom = tk.Frame(root, bg="#263238")
        bottom.pack(side="bottom", fill="x", padx=24, pady=20)
        self.entry = tk.Entry(bottom, font=(FONT, 15))
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.entry.bind("<Return>", lambda e: self.analyze_text())
        tk.Button(bottom, text="วิเคราะห์", font=(FONT, 13, "bold"), bg="#1976d2",
                  fg="white", command=self.analyze_text).pack(side="left", padx=(8, 0))
        self.rec_btn = tk.Button(bottom, text="🎤 อัดเสียง", font=(FONT, 13, "bold"),
                                 bg="#6a1b9a", fg="white", command=self.record_async)
        self.rec_btn.pack(side="left", padx=(8, 0))

        root.bind("<F11>", lambda e: root.attributes("-fullscreen", True))
        root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False))
        self.entry.focus()

    def _set_result(self, color, status, pct, text, words):
        self.result_frame.configure(bg=BG[color])
        for w in (self.emoji_lbl, self.status_lbl, self.pct_lbl):
            w.configure(bg=BG[color], fg=FG[color])
        emoji = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢", "IDLE": "🛡️"}[color]
        self.emoji_lbl.configure(text=emoji)
        self.status_lbl.configure(text=status)
        self.pct_lbl.configure(text=pct)
        self.text_lbl.configure(text=text or "—")
        self.words_lbl.configure(text=words or "—")

    def analyze(self, text):
        if not text.strip():
            return
        result = classify(text, self.model, self.vectorizer)
        color = result["color"]
        pct = f"ความมั่นใจว่าเป็นมิจฉาชีพ {result['scam_confidence']:.1f}%"
        if color == "GREEN":
            words = "(ไม่พบคำที่น่าสงสัย)"
        else:
            risky = explain_words(text, self.model, self.vectorizer)
            words = "   ".join(w for w, _ in risky) if risky else "—"
        self._set_result(color, result["label"], pct, text, words)
        if self.ser:
            self.ser.write(color[0].encode())  # 'R'/'Y'/'G'

    def analyze_text(self):
        text = self.entry.get().strip()
        if text:
            self.analyze(text)
            self.entry.delete(0, "end")

    def record_async(self):
        self.rec_btn.configure(state="disabled", text="⏺ กำลังฟัง...")
        threading.Thread(target=self._record_worker, daemon=True).start()

    def _record_worker(self):
        try:
            from predict import record_mic, transcribe, load_whisper
            if self.whisper is None:
                self.root.after(0, lambda: self.status_lbl.configure(text="กำลังโหลดตัวถอดเสียง..."))
                self.whisper = load_whisper(self.whisper_size)
            audio = record_mic(8)
            text = transcribe(self.whisper, audio)
            self.root.after(0, lambda: self.analyze(text))
        except Exception as e:
            msg = f"อัดเสียงไม่ได้: {e}"
            self.root.after(0, lambda: self.status_lbl.configure(text=msg))
        finally:
            self.root.after(0, lambda: self.rec_btn.configure(state="normal", text="🎤 อัดเสียง"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="พอร์ตบอร์ด Arduino เช่น COM3")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--model", default="small", help="ขนาดโมเดลถอดเสียง")
    args = parser.parse_args()

    try:
        model = joblib.load("scam_model.pkl")
        vectorizer = joblib.load("vectorizer.pkl")
    except FileNotFoundError:
        print("❌ ไม่พบไฟล์โมเดล กรุณารัน  python train_model.py  ก่อน")
        return

    ser = None
    if args.port:
        import serial
        ser = serial.Serial(args.port, args.baud, timeout=1)

    root = tk.Tk()
    ScamDetectorApp(root, model, vectorizer, ser=ser, whisper_size=args.model)
    root.mainloop()
    if ser:
        ser.close()


if __name__ == "__main__":
    main()

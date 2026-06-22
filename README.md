# 🛡️ SAFE — Scam Alert For Everyone

> **S**cam **A**lert **F**or **E**veryone — ระบบ AI คัดกรองสายมิจฉาชีพ 3 สี

ระบบ AI ที่ "ฟัง" บทสนทนาของสายโทรเข้า แล้ววิเคราะห์แบบเรียลไทม์ว่าน่าจะเป็น
**มิจฉาชีพ** แค่ไหน เตือนด้วย **ไฟ 3 สี + เปอร์เซ็นต์ความมั่นใจ** เพื่อช่วยปกป้อง
ผู้สูงอายุและคนทั่วไปจากภัยแก๊งคอลเซ็นเตอร์

> โปรเจกต์สำหรับงาน **depa Regional Coding & AI Competition** (รอบ Prototype)
> 📖 รายละเอียดเชิงลึก + คู่มือนำเสนอ อยู่ในไฟล์ [TEAM_GUIDE.md](TEAM_GUIDE.md)

---

## 🚦 ระบบทำงานยังไง

```
🎤 เสียงสาย → 🧠 Whisper (เสียง→ข้อความ) → 🔢 TF-IDF → 🤖 Naive Bayes (% มิจฉาชีพ)
   → 🎨 3 สี → 🔌 Arduino UNO Q → 💡 Modulino Pixels + 🔊 Buzzer
```

| สี | ความหมาย | เกณฑ์ |
|----|----------|-------|
| 🔴 แดง | เสี่ยงสูงมาก | ≥ 70% |
| 🟡 เหลือง | น่าสงสัย | 40–69% |
| 🟢 เขียว | ปลอดภัย | < 40% |

---

## ✨ จุดเด่น
- **วิเคราะห์ทั้งบทสนทนาต่อเนื่อง** — สะสมทุกบรรทัดของสายแล้ววิเคราะห์รวม (multi-turn) ไม่ใช่แค่ประโยคเดียว
- **ทำงานออฟไลน์ 100%** — เสียงไม่ถูกส่งขึ้นคลาวด์ เป็นส่วนตัวและปลอดภัย
- **ทนต่อการถอดเสียงเพี้ยน** — ใช้ฟีเจอร์ระดับตัวอักษร แม้พูดแล้วถอดผิดก็ยังจับได้
- **เบา รันบนอุปกรณ์เล็กได้** — Naive Bayes ประมวลผลเร็ว
- **ความแม่นยำ ~96%** (วัดด้วย Cross-Validation 5 รอบ) ครอบคลุมมิจฉาชีพ 14+ ประเภท
- ข้อมูลอ้างอิงรูปแบบจริงจากข่าวและรายงาน AOC 1441

---

## 📦 โครงสร้างไฟล์
| ไฟล์ | หน้าที่ |
|------|---------|
| `train_model.py` | เทรนโมเดล + วัดผล + บันทึก `.pkl` |
| `predict.py` | ระบบสาธิตบน Terminal (โหมดพิมพ์ / เสียง / ต่อบอร์ด) |
| `demo_gui.py` | หน้าจอสาธิตเต็มจอ สำหรับนำเสนอ |
| `applab_main.py` | โค้ดสำหรับวางใน `python/main.py` ของ App Lab (โครง App.run) |
| `app_unoq.py` | เวอร์ชันสคริปต์เดี่ยว รันบนบอร์ดผ่าน terminal |
| `board_check.py` | ทดสอบบนบอร์ดด้วยตัวบอร์ดอย่างเดียว (ไม่ต้องมี Modulino/ไมค์) |
| `arduino_unoq_modulino.ino` | โค้ดฝั่ง Arduino คุมไฟ Modulino Pixels + Buzzer |
| `Dataset1–8.csv` | ข้อมูลฝึก AI (เพิ่มไฟล์ใหม่ได้ ระบบโหลดอัตโนมัติ) |
| `requirements.txt` / `requirements-audio.txt` | รายการไลบรารี |
| `TEAM_GUIDE.md` | คู่มือทีมฉบับเต็ม (การทำงาน, จุดเด่น/ด้อย, แนวตอบกรรมการ) |
| `PITCH_SCRIPT.md` | สคริปต์นำเสนอ 7 นาที แบ่งบท 3 คน |
| `PITCH_QA.md` | คำถามกรรมการที่ต้องเตรียม + แนวตอบ |
| `DAY_PLAN.md` | แผนสิ่งที่ต้องทำในวันแข่ง แยกเป็นวัน |
| `LEAN_CANVAS.md` | Lean / Idea Canvas |
| `INFRASTRUCTURE_FUND.md` | ร่างแผนขอทุน depa Infrastructure Fund (15 คะแนน) |
| `MAKER_SPACE_TOKENS.md` | รายการราคา Token + แผนเบิกของ |
| `BOARD_SETUP.md` | วิธีย้ายขึ้นบอร์ด UNO Q ผ่าน Arduino App Lab |

---

## 🚀 วิธีใช้งาน

```bash
# 1) ติดตั้งไลบรารีหลัก
pip install -r requirements.txt

# 2) (ทางเลือก) ติดตั้งไลบรารีโหมดเสียง
pip install -r requirements-audio.txt

# 3) เทรนโมเดล (สร้าง scam_model.pkl + vectorizer.pkl)
python train_model.py

# 4) รันระบบสาธิต
python predict.py                 # โหมดพิมพ์ข้อความ
python predict.py --listen        # โหมดพูดใส่ไมค์
python predict.py --list-devices  # ดูรายชื่อไมโครโฟน
python predict.py --port COM3 --listen   # เสียง + ส่งไฟไป Arduino
```

> โมเดล `.pkl` ไม่ได้เก็บไว้ใน repo (สร้างใหม่ได้เร็วด้วย `python train_model.py`)

---

## 👥 ทีมผู้พัฒนา
depa Regional Coding & AI Competition — ระดับมัธยมศึกษา/อาชีวศึกษา

# 🔧 วิธีย้าย SAFE ขึ้นบอร์ด UNO Q ผ่าน Arduino App Lab

> เป้าหมาย: พูดใส่ไมค์ → บอร์ดถอดเสียง → ตรวจมิจฉาชีพ → ไฟ Modulino 3 สี + Buzzer + บอก %
> ⚠️ ชื่อเมนู/ไฟล์ของ App Lab อาจต่างเล็กน้อยตามเวอร์ชัน — ของจริงยึดตามที่พี่เลี้ยงสอน Day 1

---

## 🧩 App Lab แบ่งงานเป็น 2 ส่วน
| ส่วน | รันที่ไหน | หน้าที่ในงานเรา |
|------|----------|-----------------|
| **Python (ฝั่ง Linux)** | ชิป Qualcomm | สมองหลัก: ถอดเสียง + AI + ตัดสินสี/% |
| **Sketch (ฝั่ง MCU)** | STM32 | (ทางเลือก) คุมไฟ Modulino ถ้าสั่งจาก Python ตรงไม่ได้ |
| **Bridge** | เชื่อม 2 ส่วน | ส่งค่าระหว่าง Python ↔ Sketch |

---

## 📍 โค้ดของเราวางตรงไหน (ตารางสรุป)
| ไฟล์ของเรา | เอาไปวางใน App Lab | หมายเหตุ |
|------------|---------------------|----------|
| `app_unoq.py` | **ส่วน Python ของ App** | สมองหลัก (คัดลอกทั้งไฟล์) |
| `scam_model.pkl`, `vectorizer.pkl` | โฟลเดอร์เดียวกับ Python | หรือรัน `train_model.py` บนบอร์ดเพื่อสร้างใหม่ |
| `requirements-board.txt` | ไฟล์ requirements ของ App | ให้บอร์ดติดตั้งไลบรารี |
| `arduino_unoq_modulino.ino` | **ส่วน Sketch** (เฉพาะ Option 2) | ถ้าให้ MCU คุมไฟ |

---

## 🔀 เลือกวิธีคุมไฟ Modulino (เลือก 1 แบบ)

### ✅ Option 1 — Python คุม Modulino ตรง ๆ (แนะนำ ง่ายสุด)
ใช้ **Modulino Python library** สั่งไฟ/เสียงจากฝั่ง Python เลย ไม่ต้องมี Sketch
- เติมโค้ดในฟังก์ชัน `setup_modulino()` และ `show_result()` ใน `app_unoq.py`
- ตัวอย่าง (ชื่อจริงดูจากไลบรารีบนบอร์ด):
  ```python
  from modulino import ModulinoPixels, ModulinoBuzzer
  pixels = ModulinoPixels(); buzzer = ModulinoBuzzer()
  # ...
  pixels.set_all_color((255,0,0)); pixels.show()
  buzzer.tone(880, 600)
  ```
→ งานเราอยู่ในส่วน Python ส่วนเดียว จบ

### Option 2 — Sketch คุม Modulino (ถ้า Python สั่งตรงไม่ได้)
- ส่วน Python: ตัดโค้ดคุมไฟออก แล้วส่งตัวอักษรสี (`R`/`Y`/`G`) ผ่าน **Bridge**
- ส่วน Sketch: ใช้ `arduino_unoq_modulino.ino` แต่เปลี่ยนจากอ่าน `Serial` เป็นอ่านจาก **Bridge**

---

## 📥 เอาไฟล์ + ไลบรารีขึ้นบอร์ดยังไง (อ่านก่อน!)
- `train_model.py` ต้องมีไฟล์ `Dataset*.csv` ถึงจะเทรนได้ → **ต้องเอา CSV ขึ้นบอร์ดด้วย**
- วิธีง่ายสุด: บนบอร์ด `git clone https://github.com/PanuwatKi/AI-Cybersec` (ได้ CSV+โค้ดครบ)
  หรือก๊อปทั้งโฟลเดอร์ผ่าน **USB**
- ⚠️ ไฟล์ `.pkl` ไม่ได้อยู่บน GitHub (gitignore) → บนบอร์ดให้ **เทรนใหม่** (มี CSV แล้วเทรนได้)
  หรือก๊อป `.pkl` จากโน้ตบุ๊กผ่าน USB
- ⚠️ `pip install` ไลบรารี (sklearn/pythainlp/whisper) **ต้องมีอินเทอร์เน็ต** → เช็กว่าบอร์ดต่อ WiFi
  ที่งานได้ไหม / ถ้าได้บอร์ดมาซ้อมก่อนวันงาน ให้ลงให้เสร็จก่อน

## 🪜 ขั้นตอนทำจริง (Day 2)
1. เปิด App Lab → **สร้าง App ใหม่** สำหรับ UNO Q
2. **เริ่มจาก example ของ Modulino** (เช่นตัวอย่างไฟ Pixels) เป็นโครง → จะได้ API ไฟที่ถูกต้องแน่ ๆ
3. เอาโค้ดใน`app_unoq.py` ไปวางในส่วน Python ของ App (รวม `text_tokenize`/`normalize_text`)
4. วาง `scam_model.pkl` + `vectorizer.pkl` ไว้ในโฟลเดอร์ App (หรือรัน `train_model.py` บนบอร์ด)
5. ใส่ไลบรารีจาก `requirements-board.txt` → ติดตั้งบนบอร์ด
6. ต่อ Modulino Pixels + Buzzer เข้าช่อง Qwiic
7. **Run** → พูดใส่ไมค์ → ดูไฟขึ้นสี + % + เสียงเตือน

---

## 🩹 แก้ปัญหาที่อาจเจอ
| อาการ | แก้ |
|------|-----|
| โหลด `.pkl` ไม่ได้ / เพี้ยน | sklearn บนบอร์ดคนละเวอร์ชัน → **รัน `train_model.py` บนบอร์ด** สร้าง .pkl ใหม่ |
| `text_tokenize`/`normalize_text` not found | ต้องนิยาม 2 ฟังก์ชันนี้ในไฟล์ Python ที่โหลด .pkl (มีอยู่ใน app_unoq.py แล้ว) |
| ถอดเสียงช้ามาก | ใช้ Whisper `tiny` (ตั้งไว้แล้ว) หรือย้ายการถอดเสียงไปที่โน้ตบุ๊ก |
| สั่งไฟ Modulino จาก Python ไม่ได้ | ใช้ Option 2 (ผ่าน Sketch + Bridge) |

> 💡 แผนสำรองชัวร์: ถ้า Day 2 ติดปัญหาบนบอร์ด ใช้ `demo_gui.py` บนโน้ตบุ๊กสาธิตได้ทันที — ไม่มีทางพลาด

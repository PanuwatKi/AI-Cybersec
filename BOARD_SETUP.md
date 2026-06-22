# 🔧 คู่มือทำหน้างาน: ติดตั้ง SAFE บนบอร์ด UNO Q ตั้งแต่ศูนย์

> ทำตามทีละข้อจากบนลงล่าง · แต่ละข้อบอก **คำสั่ง** + **จะได้อะไร**
> 🛟 ถ้าบอร์ดติดขัด ใช้ `demo_gui.py` บนโน้ตบุ๊กสาธิตได้เสมอ (ชัวร์ 100%)

---

## ✅ ของที่ต้องมี (เช็กก่อนเริ่ม)
- [ ] บอร์ด **UNO Q** + สาย USB-C + ไฟเลี้ยง (ที่ชาร์จ GaN / power bank)
- [ ] **Modulino: Pixels + Buzzer + Buttons** + สาย Qwiic
- [ ] **ไมโครโฟน USB** (+ USB Hub)
- [ ] โน้ตบุ๊กที่ลง **Arduino App Lab**
- [ ] **อินเทอร์เน็ต** (สำหรับ pip install / git clone) ← สำคัญมาก ถ้าไม่มีจะลงไลบรารีไม่ได้
- [ ] **รหัสผ่าน/ล็อกอินบอร์ด** (ขอจากพี่เลี้ยงถ้าระบบถาม)

---

## 🟦 PHASE 0 — เชื่อมต่อ
1. ต่อบอร์ดกับโน้ตบุ๊กด้วย USB-C → เปิด App Lab → มุมล่างซ้ายต้องเห็นชื่อบอร์ด `uno-q-...`
2. คลิกไอคอน **`>_` (Terminal)** ล่างซ้าย → จะได้หน้าต่างพิมพ์คำสั่งบน **Linux ของบอร์ด**
   → *จะได้:* ช่องพิมพ์คำสั่งเข้าบอร์ดได้

---

## 🟩 PHASE 1 — เอาไฟล์ขึ้นบอร์ด + เทรนโมเดล (ทำใน Terminal)
> วิธีนี้ดีสุด เพราะ **เทรนบนบอร์ดเอง** = ไม่มีปัญหาเวอร์ชัน .pkl

3. โหลดโปรเจกต์ลงบอร์ด:
   ```
   git clone https://github.com/PanuwatKi/AI-Cybersec
   cd AI-Cybersec
   ```
   → *จะได้:* โค้ด + ไฟล์ `Dataset1–8.csv` ครบ (แต่ยังไม่มี .pkl)

4. ลงไลบรารี (บอร์ดเป็น Debian ต้องใส่ `--break-system-packages`):
   ```
   python3 -m pip install --break-system-packages pandas scikit-learn joblib pythainlp
   ```
   - ทำไมต้องมี flag นี้: Debian กันการลงทับระบบ (PEP 668) — flag นี้สั่งให้ลงได้เลย เหมาะกับ prototype
   - **อย่าใช้ venv** เพราะปุ่ม Run ของ App Lab ใช้ python ระบบ จะหาไลบรารีใน venv ไม่เจอ
   - ถ้า `pip: command not found` ใช้ `python3 -m pip ...` · ถ้าไม่มี pip เลย: `sudo apt install -y python3-pip`
   → *จะได้:* ไลบรารีพร้อมใช้บนบอร์ด

5. เทรนโมเดลบนบอร์ด:
   ```
   python3 train_model.py
   ```
   (พอขึ้นช่องให้พิมพ์ทดสอบ ให้พิมพ์ `exit`)
   → *จะได้:* ไฟล์ `scam_model.pkl` + `vectorizer.pkl` ที่ตรงเวอร์ชันบอร์ด + เห็นความแม่นยำ ~96%

---

## 🟨 PHASE 2 — ทดสอบ "สมอง AI" (ยังไม่ต้องต่อ Modulino/ไมค์)
6. ทดสอบวิเคราะห์ข้อความบนบอร์ด:
   ```
   python3 board_check.py
   ```
   พิมพ์ประโยคไทย เช่น *"ผมโทรจากตำรวจ บัญชีคุณพัวพันคดีฟอกเงิน โอนเงินมาด่วน"*
   → *จะได้:* ผลเป็น 🔴/🟡/🟢 + % → **ยืนยันว่า AI ทำงานบนบอร์ดได้จริง** (พิมพ์ exit ออก)

> ✅ ถ้าถึงตรงนี้ได้ = ส่วนที่เสี่ยงสุดผ่านหมดแล้ว ที่เหลือคือต่อฮาร์ดแวร์

---

> ⚠️ **สำคัญมาก:** ตอนกดปุ่ม **Run** App Lab รัน Python ใน **Docker container + venv แยก**
> (ไม่ใช่ python ของ terminal) → การ `pip install` ใน terminal **ไม่มีผลกับ App**
> ต้องประกาศไลบรารีในไฟล์ **`python/requirements.txt`** (ดู `requirements-app.txt`) แล้ว App Lab
> จะลงให้เองตอน Run · ส่วน terminal install ใช้สำหรับทดสอบด้วย `board_check.py`/`board_selftest.py` เท่านั้น

## 🟧 PHASE 3 — สร้าง App ใน App Lab + วางไฟล์
7. ใน App Lab → **สร้าง App ใหม่** สำหรับ UNO Q (โครงสร้างจะมี `python/`, `sketch/`, `app.yaml`)
8. **หาโฟลเดอร์ App แล้วเด้งเข้าไป** (ไม่ต้องรู้พาธล่วงหน้า):
   ```
   cd "$(dirname "$(find ~ -name app.yaml 2>/dev/null | head -1)")"
   ls          # ต้องเห็น  python/  sketch/  app.yaml = ถูกโฟลเดอร์แล้ว
   ```
   > ถ้าเจอหลาย App ให้เลือกอันที่ชื่อโฟลเดอร์ตรงกับชื่อ App (`test`)
9. คัดลอกไฟล์เข้า `python/` (พิมพ์สั้น ๆ ได้เพราะอยู่ในโฟลเดอร์ App แล้ว):
   ```
   cp ~/AI-Cybersec/app_unoq.py     python/main.py
   cp ~/AI-Cybersec/scam_model.pkl  python/
   cp ~/AI-Cybersec/vectorizer.pkl  python/
   ```
   > หรือเพิ่มไฟล์ผ่านหน้าต่าง App Lab (GUI) แบบที่เคยลาก .pkl เข้า `python/` ก็ได้ — ไม่ต้องใช้ cp
   → *จะได้:* โครงสร้างไฟล์พร้อมรัน:
   ```
   python/
     ├─ main.py            (สมองหลัก = app_unoq.py)
     ├─ scam_model.pkl
     └─ vectorizer.pkl
   sketch/sketch.ino       (ใช้เฉพาะถ้าให้ MCU คุมไฟ)
   app.yaml
   ```
   **(ถ้าจะใช้เสียงบนบอร์ด)** ลงไลบรารีเสียงเพิ่ม:
   ```
   python3 -m pip install --break-system-packages faster-whisper sounddevice
   ```

---

## 🟥 PHASE 4 — ต่อฮาร์ดแวร์ + เติม API Modulino
10. ต่อสาย (ไม่ต้องบัดกรี):
    - Modulino **Pixels + Buzzer + Buttons** → เสียบ **Qwiic** พ่วงกัน
    - ไมโครโฟน → **USB** (ผ่าน USB Hub)
11. หา API จริงของ Modulino:
    ```
    python3 -c "import modulino; print(dir(modulino))"
    ```
    → ส่งผลลัพธ์มาให้ Claude → จะได้โค้ดเติมใน 4 ฟังก์ชันของ `main.py`:
    `setup_modulino()` · `show_result()` · `read_buttons()` · `signal_listening()`

---

## 🟪 PHASE 5 — รันจริง
12. กดปุ่ม **Run** ใน App Lab (หรือใน Terminal: `python3 <APP_PATH>/python/main.py`)
13. **กดปุ่ม A** → ไฟน้ำเงิน+บี๊บ (พูดได้) → พูด → กด A อีกที → ไฟ 🔴/🟡/🟢 + % (แดงมีเสียง)
    **กดปุ่ม B** = ล้างเริ่มสายใหม่
14. (ทางเลือก) ตั้ง **auto-start on boot** → เสียบไฟอย่างเดียวก็ทำงาน (ถามวิธีตั้งจากพี่เลี้ยง)

---

## 📂 ไฟล์ที่ใช้ (สรุป)
| ไฟล์ | หน้าที่ |
|------|---------|
| `app_unoq.py` → `python/main.py` | สมองหลัก (เสียง→AI→ไฟ/เสียง/% + ปุ่มควบคุม) |
| `scam_model.pkl`, `vectorizer.pkl` | โมเดล (เทรนบนบอร์ดใน Phase 1) |
| `board_check.py` | ทดสอบ AI บนบอร์ด (Phase 2) |
| `train_model.py`, `Dataset1–8.csv` | เทรนโมเดลบนบอร์ด |

## ⌨️ คำสั่งสรุป (Cheat Sheet)
```
git clone https://github.com/PanuwatKi/AI-Cybersec   # โหลดโปรเจกต์
python3 -m pip install --break-system-packages pandas scikit-learn joblib pythainlp   # ลงไลบรารี
# (App อยู่ใน ~/ArduinoApps/<ชื่อ App> เช่น ~/ArduinoApps/SAFE)
python3 train_model.py        # เทรน -> ได้ .pkl (พิมพ์ exit เมื่อเสร็จ)
python3 board_check.py        # ทดสอบ AI บนบอร์ด
python3 -c "import modulino; print(dir(modulino))"   # หา API Modulino
```

## ⚠️ ข้อควรระวัง / แผนสำรอง
| ปัญหา | ทางแก้ |
|------|--------|
| บอร์ดไม่มีเน็ต → ลงไลบรารีไม่ได้ | ขอเน็ต/ฮอตสปอตจากพี่เลี้ยง · ไม่งั้นใช้แผนสำรองโน้ตบุ๊ก |
| Whisper ช้ามากบนบอร์ด | ใช้ `tiny` · หรือถอดเสียงที่โน้ตบุ๊กแทน |
| สั่ง Modulino จาก Python ไม่ได้ | ให้ MCU คุมผ่าน `sketch/sketch.ino` + Bridge |
| ทำบนบอร์ดไม่ทัน | **ใช้ `demo_gui.py` บนโน้ตบุ๊ก** — เดโมได้ครบเหมือนกัน |

## 🎁 สิ่งที่จะได้รับ (ผลลัพธ์สุดท้าย)
อุปกรณ์ **SAFE** ที่ทำงานบนบอร์ดเองทั้งหมด (Edge AI ไม่พึ่งคอม/เน็ต):
**กดปุ่ม → พูด → ไฟ 3 สีเตือน + บอก % + เสียงเตือนเมื่อเสี่ยงสูง**

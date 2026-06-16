# -*- coding: utf-8 -*-
"""
train_model.py — สอน (เทรน) AI ให้รู้จักแยกข้อความมิจฉาชีพ แล้วบันทึกเป็นไฟล์โมเดล

============================ แผนผังโครงสร้างโค้ด (Code Map) ============================
  text_tokenize()   : ตัดประโยคไทยเป็นคำ ๆ ด้วย pythainlp (newmm)
  make_vectorizer() : สร้างตัวแปลง "ข้อความ -> ตัวเลข" = ระดับคำ (word) + ระดับตัวอักษร (char)
  ขั้นที่ 2         : โหลดไฟล์ CSV ทุกไฟล์ในโฟลเดอร์มารวมกันอัตโนมัติ
  ขั้นที่ 3         : ทดสอบความแม่นยำด้วย Cross-Validation 5 รอบ + เลือกโมเดลที่ดีที่สุด
  ขั้นที่ 4         : รายงาน precision/recall บนชุดสอบ 20% ที่กันไว้
  ขั้นที่ 5         : เทรน "ตัวจริง" บนข้อมูลทั้งหมด แล้วเซฟ scam_model.pkl + vectorizer.pkl
  ขั้นที่ 6         : โหมดทดสอบสด พิมพ์ประโยคแล้วดูผลเป็น 3 สี
=====================================================================================
"""
import sys
import glob
import pandas as pd
import joblib
from pythainlp.tokenize import word_tokenize
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.naive_bayes import MultinomialNB, ComplementNB
from sklearn.metrics import classification_report
from sklearn.base import clone

# ทำให้พิมพ์ภาษาไทย/อิโมจิบน Windows ไม่ error
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# 1. ฟังก์ชันตัดคำภาษาไทย ให้ AI เข้าใจว่าประโยคมีคำอะไรบ้าง
def text_tokenize(text):
    # ป้องกันกรณีมีค่าว่าง (NaN) หลุดเข้ามาใน Data
    if not isinstance(text, str):
        return []
    return word_tokenize(text, engine="newmm")


# สร้างตัว "แปลงข้อความเป็นตัวเลข" โดยรวม 2 มุมมองเข้าด้วยกัน:
#   (1) ระดับคำ (word)  : ดูคำและคู่คำ เช่น "โอน เงิน", "กด ลิงก์"
#   (2) ระดับตัวอักษร (char): ดูชิ้นส่วนตัวอักษร 2-4 ตัว ทำให้ยังจับได้แม้คำสะกดเพี้ยน
#       (สำคัญมากเพราะเสียงพูดที่ถอดด้วย Whisper มักสะกดผิดเล็กน้อย เช่น OTP -> โอที่พี่)
def make_vectorizer():
    word_vec = TfidfVectorizer(
        tokenizer=text_tokenize, lowercase=True,
        ngram_range=(1, 2), sublinear_tf=True,
    )
    char_vec = TfidfVectorizer(
        analyzer="char_wb", lowercase=True,
        ngram_range=(2, 4), sublinear_tf=True,
    )
    return FeatureUnion([("word", word_vec), ("char", char_vec)])


# 2. ค้นหาและโหลดไฟล์ CSV ทั้งหมดในโฟลเดอร์มารวมกันอัตโนมัติ
print("⏳ กำลังหาไฟล์ Dataset ทั้งหมดในโฟลเดอร์...")
all_csv_files = glob.glob("*.csv")

if not all_csv_files:
    print("❌ ไม่พบไฟล์ .csv ในโฟลเดอร์นี้เลย กรุณาตรวจสอบไฟล์อีกครั้ง")
    sys.exit()

all_dataframes = [pd.read_csv(file) for file in all_csv_files]
df = pd.concat(all_dataframes, ignore_index=True)

# ล้างค่าว่างทิ้งเพื่อป้องกันโค้ด error
df = df.dropna(subset=["text", "label"])
df["label"] = df["label"].astype(int)

X = df["text"]
y = df["label"]

print(f"✅ โหลดเสร็จแล้ว! ตรวจพบไฟล์ CSV ทั้งหมด {len(all_csv_files)} ไฟล์")
print(f"📊 รวมจำนวนข้อมูลทั้งหมด: {len(df)} แถว "
      f"(มิจฉาชีพ {int((y == 1).sum())} / ปกติ {int((y == 0).sum())})")

# 3. เลือกโมเดลที่ดีที่สุดด้วย Cross-Validation (แบ่งข้อมูลทดสอบ 5 รอบ วัดผลเฉลี่ย)
#    ค่านี้ "น่าเชื่อถือกว่า" การวัดครั้งเดียว เอาไปพูดตอนนำเสนอได้
print("\n🔬 === ทดสอบความแม่นยำด้วย Cross-Validation (5 รอบ) ===")
candidates = {"MultinomialNB": MultinomialNB(), "ComplementNB": ComplementNB()}
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

best_name, best_score, best_clf = None, -1.0, None
for name, clf in candidates.items():
    pipe = Pipeline([("vec", make_vectorizer()), ("clf", clf)])
    scores = cross_val_score(pipe, X, y, cv=cv, scoring="accuracy")
    print(f"  - {name:15s}: ความแม่นยำเฉลี่ย {scores.mean() * 100:.1f}% "
          f"(±{scores.std() * 100:.1f}%)")
    if scores.mean() > best_score:
        best_name, best_score, best_clf = name, scores.mean(), clf

print(f"🏆 เลือกใช้โมเดล: {best_name} (แม่นยำเฉลี่ย {best_score * 100:.1f}%)")

# 4. รายงานผลแบบละเอียด (precision/recall) บนชุดทดสอบที่กันไว้ 20%
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
report_vec = make_vectorizer()
X_train_vec = report_vec.fit_transform(X_train)
X_test_vec = report_vec.transform(X_test)
report_clf = clone(best_clf)
report_clf.fit(X_train_vec, y_train)

print("\n📊 === รายงานผลแบบละเอียด (ชุดทดสอบ 20%) ===")
print(classification_report(y_test, report_clf.predict(X_test_vec),
                            target_names=["ปกติ (0)", "มิจฉาชีพ (1)"]))

# 5. เทรน "ตัวจริง" บนข้อมูลทั้งหมด เพื่อให้โมเดลเก่งที่สุด แล้วบันทึกลงเครื่อง
print("⚡ กำลังเทรนโมเดลตัวจริงบนข้อมูลทั้งหมด...")
vectorizer = make_vectorizer()
X_all_vec = vectorizer.fit_transform(X)
model = clone(best_clf)
model.fit(X_all_vec, y)

joblib.dump(model, "scam_model.pkl")
joblib.dump(vectorizer, "vectorizer.pkl")
print("✅ บันทึกเสร็จแล้ว: scam_model.pkl และ vectorizer.pkl")
print("--------------------------------------------------")

# 6. โหมดทดสอบสด พิมพ์ประโยคแล้วบอกผลเป็น 3 สี + % ความมั่นใจ
print("🔮 === เปิดระบบทดสอบ AI คัดกรองมิจฉาชีพ (Live Test) ===")
print("(หากต้องการเลิกทดสอบ ให้พิมพ์คำว่า 'exit')")

while True:
    user_input = input("\nลองพิมพ์ประโยคสนทนา : ").strip()

    if user_input.lower() == "exit":
        print("👋 ปิดระบบทดสอบแล้ว")
        break
    if user_input == "":
        continue

    test_vec = vectorizer.transform([user_input])
    proba = model.predict_proba(test_vec)[0]
    scam_confidence = proba[list(model.classes_).index(1)] * 100

    if scam_confidence >= 70:
        print(f"🔴 สีแดง: เสี่ยงเป็นมิจฉาชีพสูงมาก! (ความมั่นใจ {scam_confidence:.2f}%)")
    elif scam_confidence >= 40:
        print(f"🟡 สีเหลือง: น่าสงสัย มีโอกาสเป็นมิจฉาชีพอยู่บ้าง (ความมั่นใจ {scam_confidence:.2f}%)")
    else:
        print(f"🟢 สีเขียว: ปลอดภัย โอกาสเป็นมิจฉาชีพน้อยมาก (ความมั่นใจ {scam_confidence:.2f}%)")

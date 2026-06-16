/*
  ไฟแจ้งเตือนสายมิจฉาชีพ 3 สี (Modulino Pixels + Buzzer)
  ----------------------------------------------------------
  รับคำสั่งสีจากคอมพิวเตอร์ผ่าน Serial (จากสคริปต์ predict.py):
    'R' = แดง   (เสี่ยงสูงมาก) -> ไฟแดง + เสียงเตือน
    'Y' = เหลือง (น่าสงสัย)    -> ไฟเหลือง
    'G' = เขียว  (ปลอดภัย)     -> ไฟเขียว

  ใช้กับ Arduino UNO Q / บอร์ด Arduino + โมดูล Modulino (ต่อสาย Qwiic)
  *** หมายเหตุ: ชื่อฟังก์ชันของไลบรารี Modulino อาจต่างกันเล็กน้อยตามเวอร์ชัน
      ให้ยึดตามที่พี่เลี้ยงสอนในเวิร์กช็อป Day 1 เป็นหลัก โค้ดนี้เป็นแม่แบบตั้งต้น ***
*/
#include <Modulino.h>

ModulinoPixels pixels;
ModulinoBuzzer buzzer;

const int NUM_LEDS = 8;       // Modulino Pixels มีไฟ 8 ดวง
const int BRIGHTNESS = 40;    // ความสว่าง 0-255

void setAll(uint8_t r, uint8_t g, uint8_t b) {
  for (int i = 0; i < NUM_LEDS; i++) {
    pixels.set(i, ModulinoColor(r, g, b), BRIGHTNESS);
  }
  pixels.show();
}

void setup() {
  Serial.begin(9600);
  Modulino.begin();
  pixels.begin();
  buzzer.begin();
  setAll(0, 0, 0);            // เริ่มต้นดับไฟ
}

void loop() {
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == 'R') {
      setAll(255, 0, 0);      // แดง
      buzzer.tone(880, 600);  // เสียงเตือนเมื่อเสี่ยงสูง
    } else if (c == 'Y') {
      setAll(255, 150, 0);    // เหลือง/ส้ม
    } else if (c == 'G') {
      setAll(0, 255, 0);      // เขียว
    }
  }
}

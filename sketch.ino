/*
  sketch.ino — วางใน sketch/sketch.ino ของ App Lab (ฝั่ง MCU)
  คุม Modulino Pixels + Buzzer + Buttons แล้วเปิดเป็น RPC ให้ Python (main.py) เรียกผ่าน Bridge

  Python เรียก:  Bridge.call("set_color", r, g, b)   -> ไฟ 8 ดวงเป็นสีนั้น
                 Bridge.call("buzz", freq, ms)        -> เสียงเตือน
                 Bridge.call("read_buttons")          -> คืน 1=กด A, 2=กด B, 3=ทั้งคู่ (แล้วล้าง)

  *** ถ้า compile ไม่ผ่าน ให้ส่ง log ในแท็บ App launch มา เดี๋ยวปรับชื่อฟังก์ชันให้ตรงไลบรารี ***
*/
#include <Arduino_RouterBridge.h>
#include <Modulino.h>

ModulinoPixels pixels;
ModulinoButtons buttons;
ModulinoBuzzer  buzzer;

bool pressedA = false;
bool pressedB = false;

// ตั้งสีไฟทั้ง 8 ดวง
int rpc_set_color(int r, int g, int b) {
  for (int i = 0; i < 8; i++) {
    pixels.set(i, ModulinoColor(r, g, b), 25);   // 25 = ความสว่าง
  }
  pixels.show();
  return 0;
}

// เสียงเตือน
int rpc_buzz(int freq, int ms) {
  buzzer.tone(freq, ms);
  return 0;
}

// อ่านปุ่ม -> คืน bitmask แล้วล้างสถานะ
int rpc_read_buttons() {
  int v = 0;
  if (pressedA) v |= 1;
  if (pressedB) v |= 2;
  pressedA = false;
  pressedB = false;
  return v;
}

void setup() {
  Bridge.begin();
  Modulino.begin();
  pixels.begin();
  buttons.begin();
  buzzer.begin();

  Bridge.provide("set_color", rpc_set_color);
  Bridge.provide("buzz", rpc_buzz);
  Bridge.provide("read_buttons", rpc_read_buttons);
}

void loop() {
  // อัปเดตปุ่ม แล้วจำว่ามีการกด (ให้ Python มาอ่านทีหลัง)
  if (buttons.update()) {
    if (buttons.isPressed(0)) pressedA = true;   // ปุ่ม A
    if (buttons.isPressed(1)) pressedB = true;   // ปุ่ม B
  }
  Bridge.update();   // ให้บริการ RPC (ถ้าไลบรารีไม่มีเมธอดนี้ ลบบรรทัดนี้ออก)
  delay(10);
}

/*
  sketch.ino — วางใน sketch/sketch.ino ของ App Lab (ฝั่ง MCU)
  คุม Modulino Pixels + Buzzer + Buttons เปิดเป็น RPC ให้ Python (main.py) เรียกผ่าน Bridge

  Python เรียก:  Bridge.call("set_color", r, g, b)   -> ไฟ 8 ดวงเป็นสีนั้น
                 Bridge.call("buzz", freq, ms)        -> เสียงเตือน
                 Bridge.call("read_buttons")          -> 1=กด A, 2=กด B (แล้วล้าง)
  ปุ่ม C (จัดการในบอร์ดเอง): วนลดความสว่าง 25 -> 10 -> 5 -> 25 ...
*/
#include <Arduino_RouterBridge.h>
#include <Modulino.h>

ModulinoPixels pixels;
ModulinoButtons buttons;
ModulinoBuzzer  buzzer;

bool pressedA = false, pressedB = false;

int brightness = 25;              // ความสว่างปัจจุบัน
int lastR = 0, lastG = 0, lastB = 0;   // สีล่าสุดที่ตั้งไว้ (ไว้ปรับความสว่างย้อนหลัง)

// ทาสีไฟทั้ง 8 ดวงด้วยสีล่าสุด + ความสว่างปัจจุบัน
void applyPixels() {
  for (int i = 0; i < 8; i++) {
    pixels.set(i, ModulinoColor(lastR, lastG, lastB), brightness);
  }
  pixels.show();
}

// วนความสว่าง 25 -> 10 -> 5 -> 25 แล้วปรับไฟปัจจุบันทันที
void cycleBrightness() {
  if (brightness == 25)      brightness = 10;
  else if (brightness == 10) brightness = 5;
  else                       brightness = 25;
  applyPixels();
}

int rpc_set_color(int r, int g, int b) {
  lastR = r; lastG = g; lastB = b;
  applyPixels();
  return 0;
}

int rpc_buzz(int freq, int ms) {
  buzzer.tone(freq, ms);
  return 0;
}

int rpc_read_buttons() {
  int v = 0;
  if (pressedA) v |= 1;
  if (pressedB) v |= 2;
  pressedA = false; pressedB = false;
  return v;
}

void setup() {
  Bridge.begin();
  Modulino.begin();
  pixels.begin(); buttons.begin(); buzzer.begin();
  Bridge.provide("set_color", rpc_set_color);
  Bridge.provide("buzz", rpc_buzz);
  Bridge.provide("read_buttons", rpc_read_buttons);
}

void loop() {
  if (buttons.update()) {
    if (buttons.isPressed(0)) pressedA = true;        // ปุ่ม A
    if (buttons.isPressed(1)) pressedB = true;        // ปุ่ม B
    if (buttons.isPressed(2)) cycleBrightness();      // ปุ่ม C -> หรี่ไฟ
  }
  Bridge.update();
  delay(10);
}

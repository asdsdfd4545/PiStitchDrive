import RPi.GPIO as GPIO
import time

# ✅ Mapping ปุ่มใหม่ตามตำแหน่งจริง
KEYPAD = [
    ["F1", "F2", "#", "*"],
    ["1",  "2",  "3", "↑"],
    ["4",  "5",  "6", "↓"],
    ["7",  "8",  "9", "Esc"],
    ["←",  "0",  "→", "Ent"]
]

# ✅ GPIO ที่คุณใช้จริง
ROW_PINS = [5, 6, 13, 19, 26]     # Row 0–4 (บน → ล่าง)
COL_PINS = [21,20,16,12]       # Col 0–3 (ซ้าย → ขวา)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# ตั้งค่าขา Row เป็น input pull-up
for row_pin in ROW_PINS:
    GPIO.setup(row_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# ตั้งค่าขา Column เป็น output
for col_pin in COL_PINS:
    GPIO.setup(col_pin, GPIO.OUT)
    GPIO.output(col_pin, GPIO.HIGH)

text_input = []

print("🟢 เริ่มรับค่าจาก Keypad...")

def scan_keypad():
    for col_idx, col_pin in enumerate(COL_PINS):
        GPIO.output(col_pin, GPIO.LOW)
        time.sleep(0.005)  # ป้องกัน ghosting
        for row_idx, row_pin in enumerate(ROW_PINS):
            if GPIO.input(row_pin) == GPIO.LOW:
                while GPIO.input(row_pin) == GPIO.LOW:
                    time.sleep(0.01)
                GPIO.output(col_pin, GPIO.HIGH)
                return KEYPAD[row_idx][col_idx]
        GPIO.output(col_pin, GPIO.HIGH)
    return None

try:
    last_key = None
    while True:
        key = scan_keypad()
        if key and key != last_key:
            print("🔘 กด:", key)
            if key == "Ent":
                print("✅ ส่งข้อความ:", "".join(text_input))
                text_input = []
            elif key == "Esc":
                print("❌ ล้างข้อความ")
                text_input = []
            else:
                text_input.append(key)
            last_key = key
        elif not key:
            last_key = None
        time.sleep(0.05)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("👋 จบโปรแกรมแล้ว")

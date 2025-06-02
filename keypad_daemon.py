import RPi.GPIO as GPIO
import time
import subprocess
import os
import threading

import sys
import termios
import tty
import board
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

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
PIPE_PATH = "/tmp/keypad_pipe"

# ตั้งค่าขา Row เป็น input pull-up
for row_pin in ROW_PINS:
    GPIO.setup(row_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# ตั้งค่าขา Column เป็น output
for col_pin in COL_PINS:
    GPIO.setup(col_pin, GPIO.OUT)
    GPIO.output(col_pin, GPIO.HIGH)

text_input = []

RED = 27
YELLOW = 17
GREEN = 22
# state สำหรับบอกให้หยุดกระพริบ
blinking = {"green": False, "yellow": False, "red": False}

def init_led():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RED, GPIO.OUT)
    GPIO.setup(YELLOW, GPIO.OUT)
    GPIO.setup(GREEN, GPIO.OUT)

def blink(pin, name):
    while blinking[name]:
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(0.5)
def stop_all():
    for key in blinking:
        blinking[key] = False
    GPIO.output(RED, GPIO.LOW)
    GPIO.output(YELLOW, GPIO.LOW)
    GPIO.output(GREEN, GPIO.LOW)

def start_blink(color):
    stop_all()  # หยุดทุกไฟก่อน
    blinking[color] = True
    if color == "green":
        thread = threading.Thread(target=blink, args=(GREEN, "green"))
    elif color == "yellow":
        thread = threading.Thread(target=blink, args=(YELLOW, "yellow"))
    elif color == "red":
        thread = threading.Thread(target=blink, args=(RED, "red"))
    thread.daemon = True  # ปิดโปรแกรมแล้ว thread จะหยุด
    thread.start()


def close():
    stop_all()
    GPIO.cleanup()

def scan_keypad():
    for col_idx, col_pin in enumerate(COL_PINS):
        GPIO.output(col_pin, GPIO.LOW)
        time.sleep(0.005)  # ป้องกัน ghosting
        for row_idx, row_pin in enumerate(ROW_PINS):
            if GPIO.input(row_pin) == GPIO.LOW:
                time.sleep(0.02)  # เพิ่มเวลารอก่อนอ่านจริง
                if GPIO.input(row_pin) == GPIO.LOW:  # ยืนยันอีกที
                    while GPIO.input(row_pin) == GPIO.LOW:
                        time.sleep(0.01)
                    GPIO.output(col_pin, GPIO.HIGH)
                    return KEYPAD[row_idx][col_idx]

        GPIO.output(col_pin, GPIO.HIGH)
    return None
def send_to_pipe(char):
    try:
        with open(PIPE_PATH, "w") as pipe:
            pipe.write(char)
            pipe.flush()
    except Exception as e:
        print(f"❌ ไม่สามารถส่งข้อมูลไปที่ pipe: {e}")

#OLED--------------------------------------------------------------------------------
i2c = busio.I2C(board.SCL, board.SDA)
display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

# โหลดฟอนต์
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font_size = 32  # ปรับขนาดตามที่เหมาะกับจอ
font = ImageFont.truetype(font_path, font_size)

# สร้างพื้นภาพ
def draw_text(text):
    image = Image.new("1", (display.width, display.height))
    draw = ImageDraw.Draw(image)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = max((display.width - text_width) // 2, 0)
    y = max((display.height - text_height) // 2 - bbox[1], 0)  # ✅ ปรับให้ไม่ตกขอบล่าง

    draw.text((x, y), text, font=font, fill=255)
    display.image(image)
    display.show()

def reset_pipe(pipe_path="/tmp/keypad_pipe"):
    try:
        if os.path.exists(pipe_path):
            os.remove(pipe_path)
            print(f"🗑️ ลบ pipe เก่าแล้ว: {pipe_path}")
        os.mkfifo(pipe_path)
        print(f"✅ สร้าง pipe ใหม่เรียบร้อย: {pipe_path}")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดขณะ reset pipe: {e}")

def scroll_text_background(text, speed=0.0001):
    thread = threading.Thread(target=scroll_text, args=(text, speed))
    thread.daemon = True  # ให้ปิดอัตโนมัติเมื่อโปรแกรมหลักจบ
    thread.start()

scrolling = False

def scroll_text_controlled(text, speed=0.0001):
    global scrolling
    scrolling = True

    thaifont = ImageFont.truetype("/usr/share/fonts/truetype/tlwg/Kinnari.ttf", 24)

    image = Image.new("1", (display.width, display.height))
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), text, font=thaifont)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    y = max((display.height - text_height) // 2 - bbox[1], 0)

    if text_width <= display.width:
        # ถ้าข้อความสั้น แสดงอยู่ตรงกลางนิ่งๆ
        image = Image.new("1", (display.width, display.height))
        draw = ImageDraw.Draw(image)
        x = (display.width - text_width) // 2
        draw.text((x, y), text, font=thaifont, fill=255)
        display.image(image)
        display.show()
        return

    # ข้อความยาว → scroll จาก x=0 ไป x=-(text_width - display.width)
    start_x = 0
    end_x = -(text_width - display.width)

    while scrolling:
        for offset in range(start_x, end_x - 1, -1):
            if not scrolling:
                break
            image = Image.new("1", (display.width, display.height))
            draw = ImageDraw.Draw(image)
            draw.text((offset, y), text, font=thaifont, fill=255)
            display.image(image)
            display.show()
            time.sleep(speed)



def start_scroll(text):
    thread = threading.Thread(target=scroll_text_controlled, args=(text,))
    thread.daemon = True
    thread.start()

def stop_scroll():
    global scrolling
    scrolling = False
def clear_display():
    image = Image.new("1", (display.width, display.height))
    display.image(image)
    display.show()


#--------------------------------------------------------------------------------

try:
    last_key = None
    init_led()
    GPIO.output(RED, GPIO.LOW)
    GPIO.output(YELLOW, GPIO.LOW)
    GPIO.output(GREEN, GPIO.HIGH)
    stop_scroll()
    clear_display()
    start_scroll("กด -> เพื่อเริ่มต้น หรือ กด * เพื่อปิดเครื่อง")
    while True:
        key = scan_keypad()
        if key and key != last_key:
            print("🔘 กด:", key)

            if key == "*":
                stop_scroll()
                clear_display()
                start_scroll("ปิดเครื่อง")
                GPIO.output(RED, GPIO.HIGH)
                GPIO.output(YELLOW, GPIO.HIGH)
                GPIO.output(GREEN, GPIO.HIGH)
                subprocess.run(["sudo", "shutdown", "-h", "now"])

            elif key == "→":
                # ตรวจสอบว่า testmou.py กำลังทำงานอยู่หรือไม่
                stop_scroll()
                clear_display()
                GPIO.output(GREEN, GPIO.LOW)
                GPIO.output(YELLOW, GPIO.HIGH)
                result = subprocess.run(
                    ["pgrep", "-f", "testmou.py"],
                    stdout=subprocess.PIPE,
                    text=True
                )

                if result.stdout:
                    pids = result.stdout.strip().split("\n")
                    for pid in pids:
                        print(f"🛑 ฆ่า testmou.py PID: {pid}")
                        subprocess.run(["sudo", "kill", "-9", pid])
                    time.sleep(0.5)  # รอให้เคลียร์ก่อนรันใหม่

                print("🚀 เริ่มรัน testmou.py ใหม่")
                subprocess.Popen(
                    ["python3", "/home/tee/Desktop/dbindex/mount.py"],
                    start_new_session=True
                )

            else:
                send_to_pipe(key)  # ✅ ตรงนี้!


            last_key = key
        elif not key:
            last_key = None
        time.sleep(0.05)

except KeyboardInterrupt:
    GPIO.cleanup()
import os
import shutil
import re

import subprocess
import json
import time

import sys
import termios
import tty
import board
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

import RPi.GPIO as GPIO
import threading



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


# ใช้ raw mode เพื่อไม่ต้องกด Enter
def realtime_input():
    text = ""
    pipe_path = "/tmp/keypad_pipe"

    reset_pipe(pipe_path)

    print("⌨️ กดข้อความผ่าน Keypad (Ent เพื่อส่ง, ← เพื่อลบทีละตัว, Esc เพื่อล้าง):")

    first_input = True  # ✅ เพิ่ม flag ว่าเพิ่งเริ่มรับข้อความ

    with open(pipe_path, "r") as pipe:
        while True:
            char = pipe.read(1)
            if not char:
                continue

            # ✅ เคลียร์จอเมื่อเริ่มข้อความใหม่
            if first_input:
                clear_display()
                first_input = False

            if char == "←":
                text = text[:-1]
            elif char == "E":
                if pipe.read(2) == "nt":
                    draw_text("")  # เคลียร์จอ
                    return text
            else:
                text += char

            draw_text(text)


    print("\n👋 ออกจาก realtime input")
def realtime_input_check_special():
    pipe_path = "/tmp/keypad_pipe"
    reset_pipe(pipe_path)

    with open(pipe_path, "r") as pipe:
        while True:
            char = pipe.read(1)
            if not char:
                continue

            if char == "E":
                next_chars = pipe.read(2)
                if next_chars == "sc":
                    return True

def scroll_text_background(text, speed=0.02):
    thread = threading.Thread(target=scroll_text, args=(text, speed))
    thread.daemon = True  # ให้ปิดอัตโนมัติเมื่อโปรแกรมหลักจบ
    thread.start()

scrolling = False

def scroll_text_controlled(text, speed=0.001):
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

#RGB--------------------------------------------------------------------------------

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

def stop_all():
    for key in blinking:
        blinking[key] = False
    GPIO.output(RED, GPIO.LOW)
    GPIO.output(YELLOW, GPIO.LOW)
    GPIO.output(GREEN, GPIO.LOW)

def close():
    stop_all()
    GPIO.cleanup()

#--------------------------------------------------------------------------------

USB_IMG_PATH = "/home/tee/Desktop/dbindex/usb.img"
USB_MOUNT_PATH = "/mnt/usbimg" 
flash_path = None
def find_usb_flash_mount():
    attempts = 0
    while True:
        try:
            result = subprocess.run(["lsblk", "-o", "NAME,TRAN,MOUNTPOINT", "-J"], capture_output=True, text=True)
            data = json.loads(result.stdout)
            for dev in data["blockdevices"]:
                if dev.get("tran") == "usb" and "children" in dev:
                    for part in dev["children"]:
                        mountpoint = part.get("mountpoint")
                        if mountpoint and os.path.ismount(mountpoint):
                            return mountpoint
            attempts += 1
            if attempts > 10:
                raise RuntimeError("🔌 Flash Drive ไม่ตอบสนองเกิน 10 วินาที")
        except Exception as e:
            print(f"⚠️ Error: {e}")
        time.sleep(1)


#PATTERN_ROOT = find_usb_flash_mount()
PATTERN_ROOT = "/home/tee/Desktop/dbindex/rootfolder"
print(f"✅ พบ USB Flash Drive ที่: {PATTERN_ROOT}")

def list_pattern_folders():
    try:
        folders = [
            f for f in os.listdir(PATTERN_ROOT)
            if os.path.isdir(os.path.join(PATTERN_ROOT, f)) and not f.startswith('.')
        ]
        folders.sort()
        return folders
    except FileNotFoundError:
        print(f"❌ ไม่พบโฟลเดอร์: {PATTERN_ROOT}")
        return []


def mount_image():
    print("🔄 Mounting image...")
    uid = str(os.getuid())
    gid = str(os.getgid())

    # ล้าง loop device ที่อาจค้าง
    subprocess.run(["sudo", "umount", USB_MOUNT_PATH], stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "losetup", "-D"], stderr=subprocess.DEVNULL)
    subprocess.run(["sync"])
    time.sleep(0.3)  # รอ flush system

    # ลอง mount
    subprocess.run([
        "sudo", "mount",
        "-o", f"loop,uid={uid},gid={gid}",
        USB_IMG_PATH,
        USB_MOUNT_PATH
    ], check=True)


def unmount_image():
    print("✅ Unmounting image...")
    subprocess.run(["sudo", "umount", USB_MOUNT_PATH], check=True)
    subprocess.run(["sync"])
    time.sleep(1.0) 

def copy_dst_files(folder_name):
    src_path = os.path.join(PATTERN_ROOT, folder_name)
    dst_path = USB_MOUNT_PATH

    # ลบทุกอย่างใน usb.img ก่อน
    for f in os.listdir(dst_path):
        f_path = os.path.join(dst_path, f)
        if os.path.isfile(f_path) or os.path.islink(f_path):
            os.remove(f_path)
        elif os.path.isdir(f_path):
            shutil.rmtree(f_path)

    # คัดลอกโครงสร้างและไฟล์ทั้งหมดจาก src → dst
    for root, dirs, files in os.walk(src_path):
        rel_path = os.path.relpath(root, src_path)
        dest_dir = os.path.join(dst_path, rel_path)
        os.makedirs(dest_dir, exist_ok=True)

        for f in files:
            # 🔒 ทำชื่อไฟล์ให้ปลอดภัยก่อน
            safe_name = re.sub(r'[^\w\-.]', '_', f)
            src_file = os.path.join(root, f)
            dst_file = os.path.join(dest_dir, safe_name)

            try:
                shutil.copy2(src_file, dst_file)
            except OSError as e:
                print(f"❌ Error copying '{src_file}' → '{dst_file}': {e}")

    print(f"📁 คัดลอกโฟลเดอร์ '{folder_name}' → usb.img สำเร็จ")

def create_usb_image():
    if os.path.exists(USB_IMG_PATH):
        print("🧹 ลบ usb.img เก่า...")
        os.remove(USB_IMG_PATH)

    print("🛠️  สร้าง usb.img ขนาด 64MB...")
    subprocess.run(["dd", "if=/dev/zero", f"of={USB_IMG_PATH}", "bs=1M", "count=64"], check=True)
    subprocess.run(["mkfs.vfat", USB_IMG_PATH], check=True)
    subprocess.run(["chmod", "+rw", USB_IMG_PATH], check=True)
    subprocess.run(["sync"])
    time.sleep(1.0)
    print("✅ usb.img พร้อมใช้งาน\n")

def save_all_back_from_usb():
    try:
        subprocess.run(["sudo", "modprobe", "-r", "g_mass_storage"], check=True)
        time.sleep(0.5)

        mount_image()
        print("📥 ดึงข้อมูลทั้งหมดกลับมายัง PATTERN_ROOT...")

        # ลบทุกไฟล์ใน PATTERN_ROOT
        for f in os.listdir(PATTERN_ROOT):
            f_path = os.path.join(PATTERN_ROOT, f)
            if os.path.isfile(f_path) or os.path.islink(f_path):
                os.remove(f_path)
            elif os.path.isdir(f_path):
                shutil.rmtree(f_path)

        # คัดลอกจาก USB_MOUNT_PATH → PATTERN_ROOT
        for item in os.listdir(USB_MOUNT_PATH):
            s = os.path.join(USB_MOUNT_PATH, item)
            d = os.path.join(PATTERN_ROOT, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

        unmount_image()
        print("✅ ดึงข้อมูลทั้งหมดกลับมายัง PATTERN_ROOT สำเร็จ")
    except Exception as e:
        print(f"❌ ล้มเหลวในการดึงข้อมูลทั้งหมด: {e}")



def main():
    create_usb_image()
    print("📂 Available pattern folders:")
    init_led()
    start_blink("yellow")
    folders = list_pattern_folders()
    if not folders:
        return

    for i, name in enumerate(folders):
        print(f"  [{i}] {name}")
    start_blink("green")  # ไฟเขียวกระพริบ
    stop_scroll()
    clear_display()
    start_scroll("ใส่เลขช่อง")
    stop_scroll()
    idx = realtime_input()
    check_0 = False
    try:
        if idx != "0":
            selected = folders[int(idx)-1]
        else:
            selected = PATTERN_ROOT
            check_0 = True
        stop_scroll()
        clear_display()
        draw_text(idx)
        start_blink("yellow")
    except (IndexError, ValueError):
        print("❌ เลือกหมายเลขไม่ถูกต้อง")
        start_blink("red")
        stop_scroll()
        clear_display()
        start_scroll("ไม่มีช่อง "+str(idx))
        time.sleep(2)
        return

    mount_image()
    copy_dst_files(selected)
    unmount_image()
    try:
        # ถอด g_mass_storage ออกก่อน (จะ error ถ้ายังไม่ได้โหลด ก็จับไว้)
        subprocess.run(["sudo", "modprobe", "-r", "g_mass_storage"], check=False)

        # โหลดใหม่พร้อมไฟล์ img
        subprocess.run([
            "sudo", "modprobe", "g_mass_storage",
            f"file={USB_IMG_PATH}",
            "stall=0",
            "removable=1",
            "ro=0"
        ], check=True)
        start_blink("green")
        stop_scroll()
        clear_display()
        start_scroll(str(idx)+" เสียบเครื่อง")
        time.sleep(5)
        print("✅ g_mass_storage ถูกโหลดเรียบร้อย")
    except subprocess.CalledProcessError as e:
        start_blink("red")
        stop_scroll()
        clear_display()
        start_scroll("ผิดพลาดกด → เพื่อเริ่มใหม่")
        time.sleep(2)
        print("❌ เกิดข้อผิดพลาดในการโหลด g_mass_storage:", e)
    if check_0:
        start_blink("yellow")
        stop_scroll()
        clear_display()
        start_scroll("เสร็จแล้วกด Esc")
        while True:
            if realtime_input_check_special():
                save_all_back_from_usb()
                stop_scroll()
                clear_display()
                break
    # reload systemd
    subprocess.run(["sudo", "systemctl", "daemon-reload"])

    # restart your service
    subprocess.run(["sudo", "systemctl", "restart", "keypad-daemon"])

        

if __name__ == "__main__":
    main()
    
import time
import board
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

# สร้าง I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# สร้างอ็อบเจกต์จอ OLED
display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)  # หรือเปลี่ยนเป็น 128, 64 ถ้าใช้จอใหญ่กว่า

# เคลียร์จอ
display.fill(0)
display.show()

# สร้างพื้นภาพ
image = Image.new("1", (display.width, display.height))
draw = ImageDraw.Draw(image)

# ข้อความที่จะแสดง
text = input("🔤 ข้อความที่ต้องการแสดง: ")

# โหลดฟอนต์ TrueType และปรับขนาดแบบอัตโนมัติ
max_size = 32  # เริ่มจากฟอนต์ใหญ่สุดเท่าความสูงของจอ
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

while max_size > 6:
    font = ImageFont.truetype(font_path, max_size)
    text_width, text_height = draw.textsize(text, font=font)
    if text_width <= display.width and text_height <= display.height:
        break
    max_size -= 1

# ล้างพื้นหลัง
draw.rectangle((0, 0, display.width, display.height), outline=0, fill=0)

# คำนวณให้อยู่ตรงกลาง
x = (display.width - text_width) // 2
y = (display.height - text_height) // 2

# วาดข้อความ
draw.text((x, y), text, font=font, fill=255)

# แสดงผลบนจอ
display.image(image)
display.show()

import time
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont

# --- KONFIGURACJA ---
# address=0x3C to standard. Jeśli i2cdetect pokazało 3D, zmień na 0x3D
serial = i2c(port=1, address=0x3C)

# Inicjalizacja ekranu
device = ssd1306(serial)

print("Włączam ekran I2C...")

try:
    while True:
        with canvas(device) as draw:
            # Rysujemy ramkę
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            
            # Napisy
            draw.text((10, 10), "TEST I2C", fill="white")
            draw.text((10, 25), "Dziala!", fill="white")
            
            # Migający kursor dla efektu
            if int(time.time()) % 2 == 0:
                draw.text((10, 45), "*", fill="white")
        
        time.sleep(0.5)

except KeyboardInterrupt:
    print("Koniec.")
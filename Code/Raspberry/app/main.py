import time
import sqlite3
import threading
import datetime
import csv
import io
from flask import Flask, render_template, jsonify, send_file, make_response, redirect, url_for
import minimalmodbus
import serial

# --- IMPORTY DO OLED ---
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont

# --- KONFIGURACJA CZUJNIKA GLEBY ---
PORT = '/dev/serial0'
SLAVE_ADDRESS = 1
BAUDRATE = 4800

# --- KONFIGURACJA BAZY ---
DB_NAME = 'soil_data.db'

# --- ZMIENNA GLOBALNA NA DANE (Dla ekranu OLED) ---
# Tutaj wątek czujnika wrzuca dane, a wątek OLED je czyta.
latest_data = {
    'hum': None,
    'temp': None,
    'ec': None,
    'ph': None,
    'timestamp': "Brak danych"
}

app = Flask(__name__)

# --- INICJALIZACJA BAZY DANYCH ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS readings 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp DATETIME, 
                  hum REAL, 
                  temp REAL, 
                  ec INTEGER, 
                  ph REAL)''')
    conn.commit()
    conn.close()

# --- SETUP CZUJNIKA ---
def setup_sensor():
    try:
        instrument = minimalmodbus.Instrument(PORT, SLAVE_ADDRESS)
        instrument.serial.baudrate = BAUDRATE
        instrument.serial.bytesize = 8
        instrument.serial.parity   = serial.PARITY_NONE
        instrument.serial.stopbits = 1
        instrument.serial.timeout  = 1.0
        instrument.mode = minimalmodbus.MODE_RTU
        instrument.clear_buffers_before_each_transaction = True
        return instrument
    except Exception as e:
        print(f"Błąd inicjalizacji RS485: {e}")
        return None

# --- SETUP EKRANU OLED (I2C) ---
def setup_oled():
    try:
        # Konfiguracja dla ekranu 128x32
        serial_i2c = i2c(port=1, address=0x3C)
        device = ssd1306(serial_i2c, width=128, height=32, rotate=0)
        return device
    except Exception as e:
        print(f"Błąd inicjalizacji OLED: {e}")
        return None

# --- WĄTEK EKRANU OLED (Nowość) ---
def oled_loop():
    device = setup_oled()
    if not device:
        print("Brak OLED - wątek wyświetlacza zatrzymany.")
        return

    print("OLED uruchomiony.")
    
    while True:
        try:
            # Sprawdzamy czas, żeby wiedzieć, który ekran pokazać
            # Dzielimy czas przez 5 sekund. Reszta z dzielenia przez 4 daje nam numer ekranu (0, 1, 2, 3)
            # Cykl: 0->1->2->3->0...
            screen_index = int(time.time() / 5) % 4
            
            with canvas(device) as draw:
                # Jeśli nie ma jeszcze żadnych danych z czujnika
                if latest_data['hum'] is None:
                    draw.text((10, 5), "Inicjalizacja...", fill="white")
                    draw.text((10, 20), "Czekam na dane", fill="white")
                
                else:
                    # EKRAN 1: WILGOTNOŚĆ
                    if screen_index == 0:
                        draw.text((0, 0), "WILGOTNOSC:", fill="white")
                        # Wyświetlamy dużą wartość
                        draw.text((10, 15), f"{latest_data['hum']} %", fill="white")
                        # Pasek postępu na dole (opcjonalny bajer)
                        bar_width = int((latest_data['hum'] / 100) * 128)
                        draw.rectangle((0, 30, bar_width, 32), outline="white", fill="white")

                    # EKRAN 2: TEMPERATURA
                    elif screen_index == 1:
                        draw.text((0, 0), "TEMPERATURA:", fill="white")
                        draw.text((10, 15), f"{latest_data['temp']} C", fill="white")
                    
                    # EKRAN 3: EC (Przewodność)
                    elif screen_index == 2:
                        draw.text((0, 0), "EC (zasolenie):", fill="white")
                        draw.text((10, 15), f"{latest_data['ec']} uS/cm", fill="white")
                    
                    # EKRAN 4: pH
                    elif screen_index == 3:
                        draw.text((0, 0), "pH GLEBY:", fill="white")
                        draw.text((10, 15), f"{latest_data['ph']} pH", fill="white")

            # Odświeżanie pętli (nie za szybko, żeby nie zjadać procesora, 10fps wystarczy)
            time.sleep(0.1)

        except Exception as e:
            print(f"Błąd w pętli OLED: {e}")
            time.sleep(1)

# --- WĄTEK ODCZYTU DANYCH ---
def sensor_loop():
    sensor = setup_sensor()
    if not sensor:
        print("Nie udało się połączyć z czujnikiem. Wątek zatrzymany.")
        return

    while True:
        try:
            # 1. Odczyt fizyczny
            hum = sensor.read_register(0, 1, functioncode=3)
            temp = sensor.read_register(1, 1, functioncode=3)
            ec = sensor.read_register(2, 0, functioncode=3)
            ph = sensor.read_register(3, 1, functioncode=3)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 2. Aktualizacja zmiennej globalnej dla OLED
            latest_data['hum'] = hum
            latest_data['temp'] = temp
            latest_data['ec'] = ec
            latest_data['ph'] = ph
            latest_data['timestamp'] = timestamp
            
            print(f"Zapis: {timestamp} | H:{hum}% T:{temp}C EC:{ec} pH:{ph}")

            # 3. Zapis do bazy
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO readings (timestamp, hum, temp, ec, ph) VALUES (?, ?, ?, ?, ?)",
                      (timestamp, hum, temp, ec, ph))
            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Błąd odczytu w pętli: {e}")
        
        time.sleep(10)

# --- FLASK (STRONA WWW) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()
    data = [dict(row) for row in rows]
    return jsonify(data[::-1])

@app.route('/download_db')
def download_db():
    try:
        return send_file(DB_NAME, as_attachment=True)
    except Exception as e:
        return str(f"Błąd pobierania bazy: {e}")

@app.route('/download_csv')
def download_csv():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM readings ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    si = io.StringIO()
    cw = csv.writer(si, delimiter=';') 
    cw.writerow(['ID', 'Data i Czas', 'Wilgotność (%)', 'Temperatura (C)', 'EC (uS/cm)', 'pH'])
    
    for row in rows:
        r = list(row)
        def to_pl_number(value):
            if value is None: return ""
            return str(value).replace('.', ',')

        r[2] = to_pl_number(r[2]) 
        r[3] = to_pl_number(r[3]) 
        r[4] = to_pl_number(r[4]) 
        r[5] = to_pl_number(r[5]) 
        cw.writerow(r)
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=pomiary.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8-sig"
    return output

@app.route('/reset_db')
def reset_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM readings")
        c.execute("DELETE FROM sqlite_sequence WHERE name='readings'")
        conn.commit()
        conn.close()
        # Resetujemy też dane na wyświetlaczu
        latest_data['hum'] = None
        return redirect(url_for('index'))
    except Exception as e:
        return str(f"Błąd resetowania: {e}")

if __name__ == '__main__':
    init_db()
    
    # Start wątku czujnika
    t_sensor = threading.Thread(target=sensor_loop)
    t_sensor.daemon = True
    t_sensor.start()

    # Start wątku OLED
    t_oled = threading.Thread(target=oled_loop)
    t_oled.daemon = True
    t_oled.start()
    
    # Start serwera WWW
    app.run(host='0.0.0.0', port=80, debug=False)
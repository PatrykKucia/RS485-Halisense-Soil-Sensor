import time
import sqlite3
import threading
import datetime
import csv
import io
import subprocess
from flask import Flask, render_template, jsonify, send_file, make_response, redirect, url_for, request
import minimalmodbus
import serial

# --- IMPORTY DO OLED ---
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont

# --- KONFIGURACJA ---
PORT = '/dev/serial0'
SLAVE_ADDRESS = 1
BAUDRATE = 4800
DB_NAME = 'soil_data.db'

# --- ZMIENNE GLOBALNE ---
# Domyślny czas między pomiarami (w sekundach) - startujemy od 10s
MEASUREMENT_INTERVAL = 10 

latest_data = {
    'hum': None, 'temp': None, 'ec': None, 'ph': None, 'timestamp': "Brak danych"
}

app = Flask(__name__)

# --- BAZA DANYCH ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS readings 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp DATETIME, hum REAL, temp REAL, ec INTEGER, ph REAL)''')
    conn.commit()
    conn.close()

# --- SENSORY I EKRAN ---
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
        print(f"Błąd RS485: {e}")
        return None

def setup_oled():
    try:
        serial_i2c = i2c(port=1, address=0x3C)
        device = ssd1306(serial_i2c, width=128, height=32, rotate=0)
        return device
    except Exception as e:
        print(f"Błąd OLED: {e}")
        return None

def oled_loop():
    device = setup_oled()
    if not device: return
    
    while True:
        try:
            screen_index = int(time.time() / 5) % 4
            with canvas(device) as draw:
                if latest_data['hum'] is None:
                    draw.text((10, 5), "Inicjalizacja...", fill="white")
                else:
                    if screen_index == 0:
                        draw.text((0, 0), "WILGOTNOSC:", fill="white")
                        draw.text((10, 15), f"{latest_data['hum']} %", fill="white")
                        bar_width = int((latest_data['hum'] / 100) * 128)
                        draw.rectangle((0, 30, bar_width, 32), outline="white", fill="white")
                    elif screen_index == 1:
                        draw.text((0, 0), "TEMPERATURA:", fill="white")
                        draw.text((10, 15), f"{latest_data['temp']} C", fill="white")
                    elif screen_index == 2:
                        draw.text((0, 0), "EC:", fill="white")
                        draw.text((10, 15), f"{latest_data['ec']} uS/cm", fill="white")
                    elif screen_index == 3:
                        draw.text((0, 0), "pH GLEBY:", fill="white")
                        draw.text((10, 15), f"{latest_data['ph']} pH", fill="white")
            time.sleep(0.1)
        except:
            time.sleep(1)

def sensor_loop():
    global MEASUREMENT_INTERVAL
    sensor = setup_sensor()
    if not sensor: return
    
    while True:
        try:
            # 1. POBIERANIE DANYCH
            hum = sensor.read_register(0, 1, 3)
            temp = sensor.read_register(1, 1, 3)
            ec = sensor.read_register(2, 0, 3)
            ph = sensor.read_register(3, 1, 3)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            latest_data.update({'hum': hum, 'temp': temp, 'ec': ec, 'ph': ph, 'timestamp': timestamp})
            print(f"Zapis: {timestamp} | H:{hum}% T:{temp}C EC:{ec} pH:{ph} | Interwał: {MEASUREMENT_INTERVAL}s")

            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO readings (timestamp, hum, temp, ec, ph) VALUES (?, ?, ?, ?, ?)",
                      (timestamp, hum, temp, ec, ph))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Błąd odczytu: {e}")
        
        # 2. INTELIGENTNE CZEKANIE (Smart Sleep)
        # Zamiast time.sleep(MEASUREMENT_INTERVAL), który zablokowałby wątek na np. godzinę,
        # sprawdzamy co 0.5 sekundy, czy czas minął. Dzięki temu zmiana interwału działa natychmiast.
        start_wait = time.time()
        while (time.time() - start_wait) < MEASUREMENT_INTERVAL:
            time.sleep(0.5)

# --- FLASK ---

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
    return jsonify([dict(row) for row in rows][::-1])

# Nowy endpoint do pobierania aktualnych ustawień (żeby dropdown wiedział co pokazać)
@app.route('/get_settings')
def get_settings():
    return jsonify({"interval": MEASUREMENT_INTERVAL})

# Nowy endpoint do ustawiania interwału
@app.route('/set_interval', methods=['POST'])
def set_interval():
    global MEASUREMENT_INTERVAL
    try:
        data = request.json
        new_interval = int(data.get('interval'))
        MEASUREMENT_INTERVAL = new_interval
        print(f"Zmieniono interwał pomiarowy na: {MEASUREMENT_INTERVAL} sekund")
        return jsonify({"status": "success", "new_interval": MEASUREMENT_INTERVAL})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/download_db')
def download_db():
    try: return send_file(DB_NAME, as_attachment=True)
    except Exception as e: return str(e)

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
        to_pl = lambda v: str(v).replace('.', ',') if v is not None else ""
        r[2], r[3], r[4], r[5] = to_pl(r[2]), to_pl(r[3]), to_pl(r[4]), to_pl(r[5])
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
        c.execute("DELETE FROM readings"); c.execute("DELETE FROM sqlite_sequence WHERE name='readings'")
        conn.commit(); conn.close()
        latest_data['hum'] = None
        return redirect(url_for('index'))
    except Exception as e: return str(e)

@app.route('/set_time', methods=['POST'])
def set_time():
    try:
        data = request.json
        new_time = data.get('time')
        if new_time:
            print(f"Ustawiam czas na: {new_time}")
            subprocess.run(["date", "-s", new_time], check=True)
            return jsonify({"status": "success", "message": f"Czas ustawiony na {new_time}"})
        else:
            return jsonify({"status": "error", "message": "Brak danych"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    init_db()
    threading.Thread(target=sensor_loop, daemon=True).start()
    threading.Thread(target=oled_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=80, debug=False)
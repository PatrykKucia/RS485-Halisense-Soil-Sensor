import time
import sqlite3
import threading
import datetime
from flask import Flask, render_template, jsonify
import minimalmodbus
import serial

# --- KONFIGURACJA CZUJNIKA ---
PORT = '/dev/serial0'
SLAVE_ADDRESS = 1
BAUDRATE = 4800

# Nazwa bazy danych
DB_NAME = 'soil_data.db'

app = Flask(__name__)

# --- INICJALIZACJA BAZY DANYCH ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tworzymy tabelę jeśli nie istnieje
    c.execute('''CREATE TABLE IF NOT EXISTS readings 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp DATETIME, 
                  hum REAL, 
                  temp REAL, 
                  ec INTEGER, 
                  ph REAL)''')
    conn.commit()
    conn.close()

# --- SETUP CZUJNIKA (TWOJA FUNKCJA) ---
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
        print(f"Błąd inicjalizacji: {e}")
        return None

# --- WĄTEK ODCZYTU DANYCH (DZIAŁA W TLE) ---
def sensor_loop():
    sensor = setup_sensor()
    if not sensor:
        print("Nie udało się połączyć z czujnikiem. Wątek zatrzymany.")
        return

    while True:
        try:
            # Odczyt danych (zgodnie z Twoim kodem)
            hum = sensor.read_register(0, 1, functioncode=3)
            temp = sensor.read_register(1, 1, functioncode=3)
            ec = sensor.read_register(2, 0, functioncode=3)
            ph = sensor.read_register(3, 1, functioncode=3)
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"Zapis: {timestamp} | H:{hum}% T:{temp}C EC:{ec} pH:{ph}")

            # Zapis do bazy
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO readings (timestamp, hum, temp, ec, ph) VALUES (?, ?, ?, ?, ?)",
                      (timestamp, hum, temp, ec, ph))
            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Błąd odczytu w pętli: {e}")
        
        # Pomiar co 60 sekund (żeby nie zapchać bazy zbyt szybko, zmień jeśli chcesz częściej)
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
    # Pobierz ostatnie 100 pomiarów do wykresu
    c.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()
    
    # Formatowanie danych dla JSON
    data = [dict(row) for row in rows]
    # Odwracamy kolejność, żeby na wykresie czas szedł od lewej do prawej
    return jsonify(data[::-1])

if __name__ == '__main__':
    # Uruchomienie bazy
    init_db()
    
    # Uruchomienie wątku czujnika w tle
    t = threading.Thread(target=sensor_loop)
    t.daemon = True
    t.start()
    
    # Start serwera WWW na porcie 80 (standard HTTP)
    # host='0.0.0.0' sprawia, że jest widoczny w sieci
    app.run(host='0.0.0.0', port=80, debug=False)
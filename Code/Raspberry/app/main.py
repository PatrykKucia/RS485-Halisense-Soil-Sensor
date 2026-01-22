import time
import sqlite3
import threading
import datetime
import csv
import io
# DODANO: redirect, url_for
from flask import Flask, render_template, jsonify, send_file, make_response, redirect, url_for
import minimalmodbus
import serial

# --- KONFIGURACJA CZUJNIKA ---
PORT = '/dev/serial0'
SLAVE_ADDRESS = 1
BAUDRATE = 4800

DB_NAME = 'soil_data.db'

app = Flask(__name__)

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

def sensor_loop():
    sensor = setup_sensor()
    if not sensor:
        print("Nie udało się połączyć z czujnikiem. Wątek zatrzymany.")
        return

    while True:
        try:
            hum = sensor.read_register(0, 1, functioncode=3)
            temp = sensor.read_register(1, 1, functioncode=3)
            ec = sensor.read_register(2, 0, functioncode=3)
            ph = sensor.read_register(3, 1, functioncode=3)
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"Zapis: {timestamp} | H:{hum}% T:{temp}C EC:{ec} pH:{ph}")

            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO readings (timestamp, hum, temp, ec, ph) VALUES (?, ?, ?, ?, ?)",
                      (timestamp, hum, temp, ec, ph))
            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Błąd odczytu w pętli: {e}")
        
        time.sleep(10)

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
    data = [dict(row) for row in rows]
    return jsonify(data[::-1])

@app.route('/download_db')
def download_db():
    try:
        return send_file(DB_NAME, as_attachment=True)
    except Exception as e:
        return str(f"Błąd: {e}")

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
    cw.writerows(rows)
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=pomiary.csv"
    output.headers["Content-type"] = "text/csv"
    return output

# --- NOWA FUNKCJA: CZYSZCZENIE BAZY ---
@app.route('/reset_db')
def reset_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        # 1. Usuń wszystkie dane
        c.execute("DELETE FROM readings")
        # 2. Zresetuj licznik ID (żeby znów liczył od 1)
        c.execute("DELETE FROM sqlite_sequence WHERE name='readings'")
        conn.commit()
        conn.close()
        # Wróć na stronę główną
        return redirect(url_for('index'))
    except Exception as e:
        return str(f"Błąd resetowania: {e}")

if __name__ == '__main__':
    init_db()
    t = threading.Thread(target=sensor_loop)
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', port=80, debug=False)
import minimalmodbus
import serial
import time

# --- KONFIGURACJA ---
# Na Raspberry Pi z nakładką HAT port to zazwyczaj /dev/serial0
PORT = '/dev/serial0'

# Adres czujnika (fabrycznie to zazwyczaj 1)
SLAVE_ADDRESS = 1 

# Prędkość transmisji (W kodzie C++ ustawiłeś 4800 jako działającą)
BAUDRATE = 4800 

def setup_sensor():
    try:
        # Inicjalizacja instrumentu (czujnika)
        instrument = minimalmodbus.Instrument(PORT, SLAVE_ADDRESS)
        
        # Konfiguracja parametrów UART (RS485)
        instrument.serial.baudrate = BAUDRATE
        instrument.serial.bytesize = 8
        instrument.serial.parity   = serial.PARITY_NONE
        instrument.serial.stopbits = 1
        instrument.serial.timeout  = 1.0 # Czekamy max 1 sek na odpowiedź
        
        # Tryb RTU (standard dla RS485)
        instrument.mode = minimalmodbus.MODE_RTU
        
        # Czyścimy bufory przed każdym zapytaniem, żeby śmieci nie zakłócały
        instrument.clear_buffers_before_each_transaction = True
        
        print(f"Inicjalizacja na porcie {PORT} z prędkością {BAUDRATE} OK.")
        return instrument
    except Exception as e:
        print(f"Błąd inicjalizacji: {e}")
        return None

def main():
    sensor = setup_sensor()
    if not sensor:
        return

    print("Startuje odczyt (wersja BEZ NPK)...")
    
    while True:
        print("\n--- Nowy pomiar ---")
        
        # UWAGA: Adresy rejestrów (0, 1, 2, 3) to standard dla czujników JXBS-3001
        # Jeśli masz inny model, adresy mogą być inne, ale te są najczęstsze.

        # 1. Wilgotność (Rejestr 0)
        try:
            # functioncode 3 to odczyt rejestrów (Holding Registers)
            # decimals=1 oznacza, że wynik np. 123 zostanie zamieniony na 12.3
            hum = sensor.read_register(0, 1, functioncode=3)
            print(f"Wilgotność: {hum} %")
        except IOError:
            print("Błąd odczytu Wilgotności (brak odpowiedzi)")
        except ValueError:
            print("Błąd danych Wilgotności")

        # 2. Temperatura (Rejestr 1)
        try:
            temp = sensor.read_register(1, 1, functioncode=3)
            print(f"Temp:      {temp} °C")
        except IOError:
            print("Błąd odczytu Temperatury")

        # 3. EC / Przewodność (Rejestr 2)
        try:
            # EC zazwyczaj nie ma miejsca po przecinku (decimals=0)
            ec = sensor.read_register(2, 0, functioncode=3)
            print(f"EC:        {ec} uS/cm")
        except IOError:
            print("Błąd odczytu EC")

        # 4. pH (Rejestr 3)
        try:
            ph = sensor.read_register(3, 1, functioncode=3)
            print(f"pH:        {ph}")
        except IOError:
            print("Błąd odczytu pH")

        # Czekamy 3 sekundy (jak delay(3000) w C++)
        time.sleep(3)

if __name__ == "__main__":
    main()
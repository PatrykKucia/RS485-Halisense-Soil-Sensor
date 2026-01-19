#include <Arduino.h>
#include <SoilSensor.h>

// Ustawienia pinów (dla Twojego ESP32 ze zdjęcia)
#define RX_PIN 16 
#define TX_PIN 17 

SoilSensor soilSensor(Serial2);

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Startuje odczyt (wersja BEZ NPK)...");

  // KROK 1: ZMIANA PRĘDKOŚCI
  // Większość czujników bez NPK (3w1, 5w1) działa na 9600 lub 4800.
  // Spróbuj najpierw 9600. Jeśli nie zadziała, zmień na 4800.
  if (soilSensor.begin(4800)) { 
    Serial.println("Inicjalizacja OK (9600 baud).");
  } else {
    Serial.println("Błąd inicjalizacji (sprawdź kable).");
  }
}

void loop() {
  Serial.println("--- Nowy pomiar ---");

  // Zamiast readAllVariables(), czytamy każdy parametr osobno.
  // Dzięki temu brak NPK nie zablokuje odczytu temperatury czy wilgotności.

  // 1. Temperatura
  if (soilSensor.readTemperature()) {
    Serial.print("Temp: ");
    Serial.print(soilSensor.getTemperature());
    Serial.println(" °C");
  } else {
    Serial.println("Błąd odczytu Temperatury");
  }

  // 2. Wilgotność
  if (soilSensor.readHumidity()) {
    Serial.print("Wilgotność: ");
    Serial.print(soilSensor.getHumidity());
    Serial.println(" %");
  } else {
    Serial.println("Błąd odczytu Wilgotności");
  }

  // 3. EC (Przewodność)
  if (soilSensor.readEC()) {
    Serial.print("EC: ");
    Serial.print(soilSensor.getEC());
    Serial.println(" uS/cm");
  } else {
    Serial.println("Błąd odczytu EC");
  }

  // 4. pH (Jeśli Twój czujnik to 3w1, to też może nie działać - wtedy zakomentuj)
  if (soilSensor.readPH()) {
    Serial.print("pH: ");
    Serial.println(soilSensor.getPH());
  } else {
    Serial.println("Błąd odczytu pH (lub brak tej funkcji)");
  }
  
  // NPK (Azot, Fosfor, Potas) całkowicie pomijamy!

  delay(3000);
}
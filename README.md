# RS485-Halisense-Soil-Sensor

# Useful Links
- [Halisense Soil Sensor Library](https://registry.platformio.org/libraries/dvelaren/Halisense_SoilSensor)
- [RS485 Soil Sensor(Temperature&Humidity&EC&PH) Arduino WiKi- DFRobot](https://wiki.dfrobot.com/RS485_Soil_Sensor_Temperature_Humidity_EC_PH_SKU_SEN0604)
- [RS 485 CAN Pi Hat](https://www.waveshare.com/wiki/RS485_CAN_HAT#Documents)



# Frame
![alt text](image.png)

# Data
![alt text](image-1.png)

# Usefull info 
- default baud rate 4800!!!

# Usefull comands

sudo pip3 install flask minimalmodbus pyserial --break-system-packages

--break-system-packages - for pip install

sudo apt install network-manager
sudo systemctl enable NetworkManager
sudo systemctl start NetworkManager


[nmcli connection show] - schows all NetworkMenager hosts

[sudo nmcli connection delete "Hotspot"]

sudo nmcli device wifi hotspot ssid "MojMonitor" password "rolnik123" ifname wlan0

sudo nmcli connection modify "MojMonitor" connection.autoconnect yes

sudo nmcli connection modify "MojMonitor" connection.autoconnect-priority 100

## starup with system
sudo nano /etc/systemd/system/soilmonitor.service

[Unit]
Description=Soil Monitor Service
After=network.target network-online.target
Wants=network-online.target
```
[Service]
# Uruchamiamy jako root, żeby mieć dostęp do GPIO i portu 80
User=root
Group=root

# Tu wpisz ścieżkę do folderu, gdzie leży main.py i folder templates/
WorkingDirectory=/home/patita/RS485-Halisense-Soil-Sensor/Code/Raspberry/app

# Komenda uruchamiająca
ExecStart=/usr/bin/python3 /home/patita/RS485-Halisense-Soil-Sensor/Code/Raspberry/app/main.py

# Co robić jak się wywali? Wstań, Powstań!
Restart=always
RestartSec=10

# Przekierowanie logów (żebyś widział printy w systemie)
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

sudo systemctl daemon-reload
sudo systemctl enable soilmonitor.service
sudo systemctl start soilmonitor.service

sudo journalctl -u soilmonitor -f

# --- NOWA LINIA: Ustawia datę na sztywno przy każdym starcie ---
ExecStartPre=/bin/date -s "2025-01-01 00:00:00"
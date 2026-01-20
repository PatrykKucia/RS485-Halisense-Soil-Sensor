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
# PEF-OT23
Repositorio para códigos e información del PEF 
# Android App
## Front-End
Se utiliza Kivy para el diseño del UI. Cuenta con las siguientes features:
+ Botón de conexión a BLE
+ Switch con modo adaptivo para bicicleta
+ Slider para input de usuario en modo manual
+ Velocímetro
+ Display de batería
## Back-End
Entre los factores más importantes, se tiene el uso de las siguientes features:
+ Bleak - para establecimiento del protocolo BLE entre ESP32 y Android App. [Pueden verse las funciones programadas en BLE.py]
+ Asyncio - se une al uso de kivy para crear corutinas, teniendo así la aplicación y en el background la conexión BLE

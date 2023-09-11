#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

BLEServer* pServer = NULL;
BLECharacteristic* pCharacteristic = NULL;
bool deviceConnected = false;
bool oldDeviceConnected = false;
uint32_t value = 0;
std::string receivedValue = ""; // Declarar receivedValue aquí
bool dataSent = false; // Bandera para controlar si los datos se enviaron

// See the following for generating UUIDs:
// https://www.uuidgenerator.net/

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "00002A3D-0000-1000-8000-00805f9b34fb"

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
    }
};

class MyCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic* pCharacteristic) {
      receivedValue = pCharacteristic->getValue();
      Serial.print("Valor BLE recibido: ");
      Serial.println(receivedValue.c_str());
    }
};

void setup() {
  Serial.begin(115200);

  // Create the BLE Device
  BLEDevice::init("CYG");

  // Create the BLE Server
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create the BLE Service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Create a BLE Characteristic
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_WRITE  |
                      BLECharacteristic::PROPERTY_NOTIFY |
                      BLECharacteristic::PROPERTY_INDICATE
                    );

  // https://www.bluetooth.com/specifications/gatt/viewer?attributeXmlFile=org.bluetooth.descriptor.gatt.client_characteristic_configuration.xml
  // Create a BLE Descriptor
  pCharacteristic->addDescriptor(new BLE2902());

  // Assign the custom callback for writes
  pCharacteristic->setCallbacks(new MyCallbacks());

  // Start the service
  pService->start();

  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinPreferred(0x0);  // set value to 0x00 to not advertise this parameter
  BLEDevice::startAdvertising();
  Serial.println("Waiting a client connection to notify...");
}

void loop() {
    // notify changed value
    //if (deviceConnected) {
        //std::string message = "Hola";
        //pCharacteristic->setValue(message);
        //pCharacteristic->notify();
        //value++;
        //Serial.print("Valor BLE enviado: ");
        //Serial.println(message.c_str());
        //delay(1000); // bluetooth stack will go into congestion, if too many packets are sent, in 6 hours test i was able to go as low as 3ms
    //}
    
    // disconnecting
    if (!deviceConnected && oldDeviceConnected) {
        delay(500); // give the bluetooth stack the chance to get things ready
        pServer->startAdvertising(); // restart advertising
        Serial.println("start advertising");
        oldDeviceConnected = deviceConnected;
    }

    //if(deviceConnected){
      //Serial.println("Se realizó una conexión");
    //}
    //else{
      //Serial.println("No existe una conexión activa");
    //}
    // connecting
    if (deviceConnected && !oldDeviceConnected) {
        // do stuff here on connecting
        oldDeviceConnected = deviceConnected;
    }

// Leer lo que se escribió en el puerto serial y restablece la bandera dataSent cuando haya nuevos datos en el puerto serial 
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n'); // Leer hasta que se presione Enter
    std::string inputStd=input.c_str();
    Serial.print("Enviando por BLE: ");
    Serial.println(input);
    input="";
    receivedValue="";
    
    // Enviar por BLE
    pCharacteristic->setValue(inputStd);
    pCharacteristic->notify();

    // Flushear el puerto serial para asegurarse de que se envíe una sola vez
    Serial.flush();
    dataSent = true; // Establecer la bandera a true para evitar enviar datos nuevamente
  }
    
    // Leer el valor de la característica BLE solo si hay datos recibidos y restablece la bandera dataSent cuando se reciba un nuevo valor BLE
    if (deviceConnected && receivedValue.length() > 0) {
    Serial.print("*******");
    Serial.print("Valor BLE recibido: ");
    Serial.println(receivedValue.c_str());
    receivedValue = "";
    dataSent = false; // Restablecer la bandera para permitir un nuevo envío
}
}

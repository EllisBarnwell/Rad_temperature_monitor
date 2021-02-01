// Load Wi-Fi library
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>   // Include the WebServer library
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>

// get ssid details
#include "WS_TemperatureReading.h"

// GPIO where the DS18B20 is connected to
const int oneWireBus = 2; // D4 

const int sizePerJsonObject = 128;

// Setup a oneWire instance to communicate with any OneWire devices
OneWire oneWire(oneWireBus);

// Pass our oneWire reference to Dallas Temperature sensor 
DallasTemperature sensors(&oneWire);

// Temp sensor devices
int nDevices = 0;
DeviceAddress tempDeviceAddress;
char deviceAddressBuffer[17];


ESP8266WebServer server(80);    // Create a webserver object that listens for HTTP request on port 80

void handleRoot();              // function prototypes for HTTP handlers
void handleNotFound();

void setup() {
  Serial.begin(9600);

  delay(2000);
// commenting this out since I do the begin everytime I handle root
//  sensors.begin();

  // Connect to Wi-Fi network with SSID and password
#ifdef DEBUG
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
#endif
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
#ifdef DEBUG
    Serial.print(".");
#endif
  }
  
#ifdef DEBUG
  // Print local IP address  if in debug mode
  Serial.println("");
  Serial.println("WiFi connected.");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
#endif
 
  // and start web server
  server.on("/", handleRoot);               // Call the 'handleRoot' function when a client requests URI "/"
  server.onNotFound(handleNotFound);        // When a client requests an unknown URI (i.e. something other than "/"), call function "handleNotFound"
  server.begin();                           // Start the server
  
#ifdef DEBUG
  Serial.println("HTTP server started");
  Serial.println(ESP.getFreeHeap());
#endif
}

void loop(){
  server.handleClient();
}

String getAddressString(DeviceAddress deviceAddress, boolean serialPrint) {
  String addressStr = "";
  for (uint8_t i = 0; i < 8; i++){
    if (deviceAddress[i] < 16) {
      addressStr = addressStr + "0";
      if (serialPrint) Serial.print("0");
    }
    addressStr = addressStr + String(deviceAddress[i], HEX);
    if (serialPrint) Serial.print(deviceAddress[i], HEX);
  }
  return addressStr;
}

void handleRoot() {
// begin sensors everytime to handle the situation where somebody adds sensors
  sensors.begin();
// #ifdef DEBUG
  Serial.println(ESP.getFreeHeap());
// #endif
  nDevices = sensors.getDeviceCount();
// #ifdef DEBUG
  Serial.print("Number of sensors is ");
  Serial.println(nDevices);
// #endif
  if (0 == nDevices) {
    // if there are still no sensors say so
      server.send(404, "text/plain", "No Sensors found");
      return;
    }
  }

  sensors.requestTemperatures(); 

  DynamicJsonDocument arrayDoc(sizePerJsonObject * (nDevices));
  JsonArray sensorsJsonArray = arrayDoc.to<JsonArray>();

  for (int i = 0; i < nDevices; i++) {
    if(sensors.getAddress(tempDeviceAddress, i)) {
#ifdef DEBUG      
      Serial.print("Temperature for device with address: ");
      String deviceAddress = getAddressString(tempDeviceAddress, true);
      Serial.println("");
      float temperatureCByAddress = sensors.getTempC(tempDeviceAddress);
      Serial.print(temperatureCByAddress);
      Serial.println("ºC");
      Serial.println("");
#endif      
      DynamicJsonDocument objDoc(sizePerJsonObject * nDevices);

      JsonObject sensorInfo = objDoc.to<JsonObject>();

      sensorInfo["SensorID"] = deviceAddress;
      sensorInfo["TempDegC"] = temperatureCByAddress;
#ifdef DEBUG
       serializeJson(sensorInfo,Serial);
#endif
      sensorsJsonArray.add(sensorInfo);
    }
    
  }
 
  String serialisedJson;
  serializeJson(arrayDoc,serialisedJson);
#ifdef DEBUG
  serializeJson(arrayDoc,Serial);
#endif  
  // if somebody has uplugged the sensors 
  // set nunmber of sensors to zero and tell them so
  if (arrayDoc.size() == 0) {
    nDevices = 0;
    server.send(404, "text/plain", "No Sensors found");
    return;
  }

  
  server.send(200, "text/json", serialisedJson);   // Send HTTP status 200 (Ok) and send some text to the browser/client
}

void handleNotFound(){
  server.send(404, "text/plain", "404: Not found. Go to root to get temperatures"); // Send HTTP status 404 (Not Found) when there's no handler for the URI in the request
}

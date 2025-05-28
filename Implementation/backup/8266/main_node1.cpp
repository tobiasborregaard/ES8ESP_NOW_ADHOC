#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <espnow.h>
struct Payload
{
  int id;
  int rssi;
};
// Callback function declaration
void onReceive(uint8_t *mac, uint8_t *data, uint8_t len);

void setup()
{
  Serial.begin(9600);
  delay(100);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  if (esp_now_init() != 0)
  {
    Serial.println("ESP-NOW init failed");
    return;
  }

  esp_now_set_self_role(ESP_NOW_ROLE_SLAVE); // Required on ESP8266
  esp_now_register_recv_cb(onReceive);

  Serial.print("MAC Address: ");
  Serial.println(WiFi.macAddress());
}

void loop()
{
  // nothing here, we're just listening
}

void onReceive(uint8_t *mac, uint8_t *data, uint8_t len)
{
  char macStr[18];
  snprintf(macStr, sizeof(macStr),
           "%02X:%02X:%02X:%02X:%02X:%02X",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

  Serial.print("[ESP-NOW] Message from ");
  Serial.print(macStr);


  if (len == sizeof(int))
  {
    int rssiVal;
    memcpy(&rssiVal, data, sizeof(rssiVal));
    Serial.printf("Received RSSI: %d dBm\n", rssiVal);
  }
  else
  {
    Serial.printf("Unexpected payload (%d bytes): ", len);
    for (int i = 0; i < len; i++)
    {
      Serial.printf("0x%02X ", data[i]);
    }

    Serial.println();
  }
}

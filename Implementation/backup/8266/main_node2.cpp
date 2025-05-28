#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <espnow.h>
// E8:DB:84:ED:77:49
// Replace with MAC address of the receiving ESP8266
uint8_t peerAddress[] = {0xE8, 0xDB, 0x84, 0xED, 0x77, 0x49}; // <-- change this
uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
void onSent(uint8_t *mac_addr, uint8_t sendStatus)
{
  Serial.print("Send status: ");
  Serial.println(sendStatus == 0 ? "Success" : "Fail");
}

void setup()
{
  Serial.begin(9600);

  // Set device in STA mode
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(); // ESP-NOW doesn't need WiFi connection
  WiFi.setOutputPower(20);

  Serial.println("ESP8266 MAC: " + WiFi.macAddress());

  if (esp_now_init() != 0)
  {
    Serial.println("ESP-NOW init failed");
    return;
  }

  esp_now_set_self_role(ESP_NOW_ROLE_CONTROLLER); // sending only
  esp_now_register_send_cb(onSent);

  // Add peer (unicast target)
  esp_now_add_peer(peerAddress, ESP_NOW_ROLE_SLAVE, 1, NULL, 0); // channel 1, no encryption

  Serial.println("ESP-NOW init done");
}

void loop()
{
  // Simulate RSSI value
  int rssi = random(-90, -30); // realistic dBm range
  Serial.println("Sending RSSI: " + String(rssi));

  // // Send RSSI value as a single int (4 bytes)
  int result = esp_now_send(broadcastAddress, (uint8_t *)&rssi, sizeof(rssi));
  if (result != 0)
  {
    Serial.println("Send failed!");
  }

  delay(1000);
}

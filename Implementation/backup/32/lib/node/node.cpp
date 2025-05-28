#include "node.h"
#include <esp_now.h>
#include <esp_log.h>
#include <esp_random.h>
#include <esp_mac.h>
#include <esp_sleep.h>
#include <vector>
#include <cstring>
#include <algorithm>

static const char *TAG = "NODE";
static std::vector<NeighborInfo> neighbors;
static uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
Node nodeInstance;  // define globally
NeighborInfo* findNeighbor(const uint8_t mac[6]) {
  for (auto& n : neighbors) {
    if (memcmp(n.id, mac, 6) == 0)
      return &n;
  }
  return nullptr;
}

template <typename T>
void sendPacket(packetType type, const T& payload, const uint8_t *dest) {
  uint8_t buffer[1 + sizeof(T)];
  buffer[0] = type;
  memcpy(buffer + 1, &payload, sizeof(T));

  esp_err_t result = esp_now_send(dest, buffer, sizeof(buffer));
  if (result != ESP_OK) {
    ESP_LOGE(TAG, "Send failed: %s", esp_err_to_name(result));
  }
}

Node::Node() {}

void Node::init(std::string ssid, std::string psw) {
  self.Router_ssid = std::move(ssid);
  self.Router_psw = std::move(psw);
}

void Node::startESPNow() {
  if (esp_now_init() != ESP_OK) {
    ESP_LOGE(TAG, "ESP-NOW init failed!");
    return;
  }
esp_now_register_recv_cb([](const esp_now_recv_info_t *info, const uint8_t *data, int len) {
    nodeInstance.onReceive(info, data, len);
});


  ESP_LOGI(TAG, "ESP-NOW Ready");
}

void Node::sendHelloTask(void *param) {
  Node *self = static_cast<Node *>(param);
  vTaskDelay(pdMS_TO_TICKS(50 + (esp_random() % 851)));
  vTaskDelay(pdMS_TO_TICKS(self->getSendDelay()));

  if (!self->self.selfSent) {
    MsgHello msg{.RSSI = self->self.rssi_sr};
    sendPacket(MSG_HELLO, msg, broadcastAddress);
    self->self.selfSent = true;
  }

  vTaskDelete(NULL);
}

void Node::sense() {
  if (self.rssi_sr == 0) waitForRouterSignal();

  if (!self.selfSent) {
    xTaskCreate(sendHelloTask, "SendHello", 2048, this, 1, nullptr);
  }
}

void Node::waitForRouterSignal() {
  wifi_scan_config_t scanConfig = {
    .ssid = (uint8_t *)self.Router_ssid.c_str(),
    .bssid = nullptr,
    .channel = 0,
    .show_hidden = true,
    .scan_type = WIFI_SCAN_TYPE_PASSIVE,
  };

  int totalRSSI = 0;
  int validSamples = 0;

  for (int i = 0; i < 10; ++i) {
    esp_wifi_scan_start(&scanConfig, true);
    uint16_t num = 0;
    wifi_ap_record_t result[1];
    esp_wifi_scan_get_ap_num(&num);
    esp_wifi_scan_get_ap_records(&num, result);
    if (num > 0) {
      totalRSSI += result[0].rssi;
      ++validSamples;
    }
    vTaskDelay(pdMS_TO_TICKS(1000));
  }

  self.rssi_sr = (validSamples > 0) ? totalRSSI / validSamples : 0;
  ESP_LOGI(TAG, "Averaged RSSI to router: %d dBm", self.rssi_sr);
}

void Node::onReceive(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len < 1) return;

  int sn = info->rx_ctrl->rssi;
  uint8_t mac[6];
  memcpy(mac, info->src_addr, 6);

  packetType type = static_cast<packetType>(data[0]);

  switch (type) {
    case MSG_HELLO: {
      MsgHello msg;
      memcpy(&msg, data + 1, sizeof(MsgHello));
      NeighborInfo *neighbor = findNeighbor(mac);
      if (neighbor) {
        neighbor->rssi_nr = msg.RSSI;
        neighbor->rssi_sn = sn;
      } else {
        NeighborInfo newNeighbor;
        memcpy(newNeighbor.id, mac, 6);
        newNeighbor.rssi_nr = msg.RSSI;
        newNeighbor.rssi_sn = sn;
        neighbors.push_back(newNeighbor);
      }
      break;
    }
    case MSG_BATCH:
      // TODO
      break;
    default:
      break;
  }
}

void Node::update() {
  switch (self.global) {
    case NODE_IDLE:
      if (self.network == NET_NOT_FORMED) {
        ESP_LOGI("FSM", "IDLE → SENSING");
        self.global = NODE_SENSING;
      } else {
        ESP_LOGI("FSM", "IDLE → TRANSMITTING");
        self.global = NODE_TRANSMITTING;
      }
      break;

    case NODE_SENSING:
      ESP_LOGI("FSM", "SENSING...");
      sense();
      self.global = NODE_SLEEP;
      break;

    case NODE_TRANSMITTING:
      ESP_LOGI("FSM", "TRANSMITTING...");
      // Placeholder for real TX logic
      self.global = NODE_SLEEP;
      break;

    case NODE_SLEEP:
      ESP_LOGI("FSM", "SLEEPING 10s");
      esp_sleep_enable_timer_wakeup(10 * 1000000);
      esp_deep_sleep_start();  // never returns
      break;
  }
}

void Node::stopListening() {
  esp_now_unregister_recv_cb();
}

void Node::addSendDelay(int ms) {
  self.sendDelayMs = std::min(self.sendDelayMs + ms, 1000);
}

int Node::getSendDelay() const {
  return self.sendDelayMs;
}

void Node::fsmTask(void *param) {
  Node *self = static_cast<Node *>(param);
  while (true) {
    self->update();
    vTaskDelay(pdMS_TO_TICKS(200));
  }
}

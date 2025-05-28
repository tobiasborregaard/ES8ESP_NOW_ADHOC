#ifndef NODE_H
#define NODE_H

#include <esp_wifi.h>
#include <esp_now.h>
#include <string>

#define MAX_PENDING_MSGS 20
#define MAX_NEIGHBORS 8

struct NeighborInfo {
  uint8_t id[6];
  int rssi_sn;
  int rssi_nr;
};

enum packetType : uint8_t {
  MSG_HELLO,
  MSG_BATCH
};

struct MsgHello {
  int RSSI;
};

struct MsgData {
  int data;
  uint8_t id[6];
  uint8_t seq;
};

struct MsgBatch {
  uint8_t count;
  MsgData messages[MAX_PENDING_MSGS];
};

enum nGlobal { NODE_IDLE, NODE_SLEEP, NODE_SENSING, NODE_TRANSMITTING };
enum nMessage { MSG_IDLE, MSG_GOT_DATA };
enum nStatus { NET_NOT_FORMED, NET_FORMED };

struct nodeState {
  nGlobal global = NODE_IDLE;
  nMessage message = MSG_IDLE;
  nStatus network = NET_NOT_FORMED;
  bool selfSent = false;
  int rssi_sr = 0;
  int sendDelayMs = 0;
  std::string Router_ssid;
  std::string Router_psw;
};

class Node {
public:
  Node();
  void init(std::string ssid, std::string psw);
  void startESPNow();
  void update();
  void sense();
  void waitForRouterSignal();
  void stopListening();
  int getSendDelay() const;
  void addSendDelay(int ms);
  static void sendHelloTask(void *param);
  static void fsmTask(void *param);  // FSM as FreeRTOS task
  void onReceive(const esp_now_recv_info_t *recv_info, const uint8_t *data, int len);

private:
  nodeState self;
};

#endif
#ifndef NODE_H
#define NODE_H

#include <esp_wifi.h>
#include <esp_now.h>
#include <string>

#define MAX_PENDING_MSGS 20
#define MAX_NEIGHBORS 8

struct NeighborInfo
{
  uint8_t id[6];
  int32_t rssi_sn;
  int32_t rssi_nr;
  uint32_t score;
  int64_t lastSeen;
  bool via;
} __attribute__((packed));

enum packetType : uint8_t
{
  MSG_HELLO,
  MSG_BATCH,
  MSG_CORRECTION,
  MSG_SYNC,
  MSG_JOIN,
  MSG_JOIN_ACK,
};

enum nGlobal
{
  NODE_SLEEP,
  NODE_SENSING,
  NODE_TRANSMITTING
};
enum nMessage
{
  MSG_IDLE,
  MSG_GOT_DATA
};
enum nStatus
{
  NET_NOT_FORMED,
  NET_FORMED
};

struct Msgjoin
{
  int RSSI;
  uint32_t time_sent;
} __attribute__((packed));

struct MsgSync
{
  int64_t time_sent;
} __attribute__((packed));

struct MsgCorrection
{
  int32_t offset_suggested;
} __attribute__((packed));

struct MsgHello
{
  int32_t RSSI;
  uint32_t time_sent;
};

struct MsgData
{
  uint8_t id[6];
  uint8_t bestHop[6];
  int32_t RSSI;
};

struct MsgBatch
{
  uint8_t count;
  MsgData messages[MAX_PENDING_MSGS];
}__attribute__((packed));

struct MSG
{
  packetType type;
  union
  {
    MsgBatch batch;
    MsgCorrection correction;
    MsgHello hello;
    MsgSync sync;
  } __attribute__((packed));
};
#endif
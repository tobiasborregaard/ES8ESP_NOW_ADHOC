// cppcheck-suppress normalCheckLevelMaxBranches
#include <esp_wifi.h>
#include <esp_now.h>
#include <string>
#include <cstring>
#include <esp_log.h>
#include "node.h"
#include <vector>
#include <nvs_flash.h>
#include <esp_timer.h>
#include <nvs.h>
#include "driver/gpio.h"
#include <esp_sleep.h>
#include "esp_random.h"
#include "utilsESP.cpp"
#include <esp_system.h>

#define LED_PIN GPIO_NUM_2
#define NETWORK_SIZE 2

static std::vector<NeighborInfo> neighbors;
static std::vector<MsgData> msgQueue;
static uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

nGlobal global = NODE_SLEEP;

RTC_DATA_ATTR nMessage message = MSG_IDLE;
RTC_DATA_ATTR int32_t rssi_to_router = 0;
RTC_DATA_ATTR nStatus status = NET_NOT_FORMED;
RTC_DATA_ATTR int64_t time_offset = 0;
RTC_DATA_ATTR bool receivedSync = false;
RTC_DATA_ATTR bool sentSomething = false;
RTC_DATA_ATTR bool receivedMessage = false;
RTC_DATA_ATTR bool direct = false;
RTC_DATA_ATTR uint8_t largestid = 0;
RTC_DATA_ATTR uint8_t selfMac[6];
RTC_DATA_ATTR uint8_t bestHop[6];

// const char *SSID = "Linksys00159";
const char *SSID = "Kviknet-3E50";
const char *PASSWORD = "h8ztguppuj";
int64_t globalDelay = 0;

// Store data
void saveNeighbors()
{
    saveVectorToNVS("neighbors", "neighbor_count", neighbors);
}

void loadNeighbors()
{
    loadVectorFromNVS("neighbors", "neighbor_count", neighbors);
}

void saveMsgQueue()
{
    saveVectorToNVS("msg_queue", "msg_count", msgQueue);
}
void loadMsgQueue()
{
    loadVectorFromNVS("msg_queue", "msg_count", msgQueue);
}

void saveStates()
{
    saveState(global, message, status);
}
void loadStates()
{
    loadState(global, message, status);
    if (status != NET_FORMED && status != NET_NOT_FORMED)
    {
        status = NET_NOT_FORMED;
    }
}

NeighborInfo *findNeighbor(const uint8_t mac[6])
{
    if (!mac)
        return nullptr; // defensive check

    for (auto &n : neighbors)
    {
        // Optional: check if n.id is valid (paranoia check if loaded from flash)
        if (memcmp(n.id, mac, 6) == 0)
            return &n;
    }
    return nullptr;
}

// Parse Messages
// formNetwork task
void sendHello()
{

    MSG msg;
    msg.type = MSG_HELLO;
    msg.hello.RSSI = rssi_to_router;
    msg.hello.time_sent = esp_timer_get_time() - time_offset;
    esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *)&msg, sizeof(MSG));
    if (result == ESP_OK)
    {
        // printf("Hello sent\n");
    }
    else
    {
        printf("Send failed: %s\n", esp_err_to_name(result));
    }
    vTaskDelay(pdMS_TO_TICKS(100));
    sentSomething = true;
}

void sendJoin()
{

    MSG msg;
    msg.type = MSG_JOIN;
    msg.hello.RSSI = rssi_to_router;
    msg.hello.time_sent = esp_timer_get_time() - time_offset;
    esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *)&msg, sizeof(MSG));
    if (result == ESP_OK)
    {
        // printf("Hello sent\n");
    }
    else
    {
        // printf("Send failed: %s\n", esp_err_to_name(result));
    }
    vTaskDelay(pdMS_TO_TICKS(100));
}


void parseHello(uint8_t *mac, MsgHello &data, int32_t rssiN, int len)
{

    printf("Got message from: %02X:%02X:%02X:%02X:%02X:%02X, NR = %ld, RSSI = %ld\n",
           mac[0], mac[1], mac[2],
           mac[3], mac[4], mac[5], data.RSSI, rssiN);

    NeighborInfo *neighbor = findNeighbor(mac);
    if (neighbor)
    {
        neighbor->rssi_nr = data.RSSI;
        neighbor->rssi_sn = rssiN;
    }
    else
    {
        NeighborInfo newNeighbor;
        memcpy(newNeighbor.id, mac, 6);
        newNeighbor.rssi_nr = data.RSSI;
        newNeighbor.rssi_sn = rssiN;
        newNeighbor.lastSeen = data.time_sent;
        neighbors.push_back(newNeighbor);
        printf("Checking %zu neighbors for match\n", neighbors.size());
        sendHello();
    }
}

void ParseBatch(const uint8_t* data, int len)
{
    /* ── 1. Quick sanity: at least type + count ───────────────────────── */
    if (len < 2) return;

    const uint8_t count = data[1];           /* data[0] = type byte */
    if (count == 0 || count > MAX_PENDING_MSGS) {
        printf("[BATCH] Bad count field: %u\n", count);
        return;
    }

    /* ── 2. Validate packet length exactly ────────────────────────────── */
    const size_t expected = 1+ count * sizeof(MsgData);
    if (static_cast<size_t>(len) < expected) {
        printf("[BATCH] Invalid size: len = %d, expected = %zu, count = %u\n",
               len, expected, count);
        return;
    }

    /* ── 3. Interpret the payload safely ──────────────────────────────── */
    const MsgData* msgs =
        reinterpret_cast<const MsgData*>(data + 2);   /* past type+count */

    if (direct) {
        /* handle locally */
        for (uint8_t i = 0; i < count; ++i) {
            const MsgData& m = msgs[i];
            printf("From %02X:%02X:%02X:%02X:%02X:%02X via %02X:%02X:%02X:%02X:%02X:%02X  "
                   "RSSI = %ld\n",
                   m.id[0],  m.id[1],  m.id[2],
                   m.id[3],  m.id[4],  m.id[5],
                   m.bestHop[0], m.bestHop[1], m.bestHop[2],
                   m.bestHop[3], m.bestHop[4], m.bestHop[5],
                   m.RSSI);
        }
    } else {
        /* queue for forwarding */
        printf("[BATCH] Forwarding %u messages\n", count);
        msgQueue.insert(msgQueue.end(), msgs, msgs + count);
        saveMsgQueue();
        receivedMessage = true;
    }
}

void sendBatch()
{
    loadMsgQueue();

    /* ── 1. Inject “my-own” status message ───────────────────────────── */
    MsgData selfMsg{};
    memcpy(selfMsg.id,       selfMac,  6);
    memcpy(selfMsg.bestHop,  bestHop,  6);
    selfMsg.RSSI = rssi_to_router;
    msgQueue.push_back(selfMsg);

    /* ── 2. Build the packet ──────────────────────────────────────────── */
    MSG msg{};                           // zero-initialise → no pad junk
    msg.type        = MSG_BATCH;
    msg.batch.count = std::min<int>(msgQueue.size(), MAX_PENDING_MSGS);

    for (int i = 0; i < msg.batch.count; ++i)
        msg.batch.messages[i] = msgQueue[i];

    const size_t msgSize =
        1                        /* type  */
      + 1                        /* count */
      + msg.batch.count * sizeof(MsgData);

    /* ── 4. Send ──────────────────────────────────────────────────────── */
    esp_err_t err = esp_now_send(bestHop,
                                 reinterpret_cast<const uint8_t*>(&msg),
                                 msgSize);

    if (err == ESP_OK) {
        printf("[BATCH] Sent %d messages to %02X:%02X:%02X:%02X:%02X:%02X\n",
               msg.batch.count,
               bestHop[0], bestHop[1], bestHop[2],
               bestHop[3], bestHop[4], bestHop[5]);

        /* remove only what we actually sent */
        msgQueue.erase(msgQueue.begin(),
                       msgQueue.begin() + msg.batch.count);
        saveMsgQueue();
    } else {
        printf("[BATCH] Failed to send messages: %s\n",
               esp_err_to_name(err));
    }
}

void senseRouter()
{
    wifi_scan_config_t scanConfig = {
        .ssid = (uint8_t *)SSID, // SSID filter (optional — safe to leave in)
        .bssid = nullptr,
        .channel = 0,
        .show_hidden = true,
        .scan_type = WIFI_SCAN_TYPE_ACTIVE,
        .scan_time = {
            .active = {.min = 50, .max = 120}}};

    // printf("Starting Wi-Fi scan for SSID: %s\n", SSID);
    vTaskDelay(pdMS_TO_TICKS(100)); // Let Wi-Fi hardware settle

    if (esp_wifi_scan_start(&scanConfig, true) != ESP_OK)
    {
        // printf("Wi-Fi scan start failed\n");
        return;
    }

    uint16_t num = 0;
    esp_wifi_scan_get_ap_num(&num);
    if (num == 0)
    {
        // printf("No APs found\n");
        return;
    }

    wifi_ap_record_t *results = (wifi_ap_record_t *)malloc(num * sizeof(wifi_ap_record_t));
    if (!results)
    {
        // printf("Memory allocation failed\n");
        return;
    }

    if (esp_wifi_scan_get_ap_records(&num, results) != ESP_OK)
    {
        // printf("Failed to retrieve AP records\n");
        free(results);
        return;
    }

    int32_t strongest_rssi = -128; // initialize to very weak signal
    bool found = false;

    for (int i = 0; i < num; ++i)
    {
        if (strcmp((const char *)results[i].ssid, SSID) == 0)
        {
            // printf("Found match: %s, RSSI = %d\n", results[i].ssid, results[i].rssi);
            if (results[i].rssi > strongest_rssi)
            {
                strongest_rssi = results[i].rssi;
                found = true;
            }
        }
    }

    free(results);

    if (found)
    {
        rssi_to_router = strongest_rssi;
        status = NET_FORMED;
        printf("Selected strongest RSSI for '%s': %ld dBm\n", SSID, rssi_to_router);
    }
    else
    {
        // printf("No matching SSID '%s' found\n", SSID);
    }
}

// Routing decision: discard neighbor if farther or weaker than router, or link too weak.
// Score direct: PL1r + bias, score via neighbor: ½ × (PL1n + PLnr). Pick lower score.
void decideHop(void *pvParameters)
{
    int32_t bestScore = 100;
    bool sdirect = true;

    for (auto &n : neighbors)
    {
        if (memcmp(n.id, broadcastAddress, 6) == 0)
        {
            continue;
        }
        // printf("[HOP] Selected via neighbor: %02X:%02X:%02X:%02X:%02X:%02X\n sr: %ld, nr: %ld, sn: %ld   \n",
            //    n.id[0], n.id[1], n.id[2],
            //    n.id[3], n.id[4], n.id[5], rssi_to_router, n.rssi_nr, n.rssi_sn);

        if (rssi_to_router >= n.rssi_sn)
        {
            n.score = rssi_to_router;
            n.via = false;
        }
        else if (rssi_to_router >= n.rssi_nr)
        {
            n.score = rssi_to_router;
            n.via = false;
        }
        else if (n.rssi_sn <= -75)
        {
            n.score = rssi_to_router;
            n.via = false;
        }
        else
        {
            int32_t direct_score = std::abs(rssi_to_router) + 2;
            int32_t via_score = (std::abs(n.rssi_nr) + std::abs(n.rssi_sn)) * 0.5;
            // printf("[HOP] Direct Score %ld, Via Score %ld\n",
                //    direct_score, via_score);
            if (direct_score > via_score)
            {

                sdirect = false;
                if (bestScore > via_score)
                {
                    bestScore = via_score;
                    memcpy(bestHop, n.id, 6);
                    n.via = true;
                    n.score = via_score;
                }
            }
        }
    }

    if (!sdirect)
    {
        printf("[HOP] Selected via neighbor: %02X:%02X:%02X:%02X:%02X:%02X (score: %ld dBm)\n",
               bestHop[0], bestHop[1], bestHop[2],
               bestHop[3], bestHop[4], bestHop[5],
               bestScore);
        direct = false;
        if (memcmp(bestHop, broadcastAddress, 6) != 0)
        {
            if (!esp_now_is_peer_exist(bestHop))
            {
                esp_now_peer_info_t unicastPeer = {};
                memcpy(unicastPeer.peer_addr, bestHop, 6);
                unicastPeer.channel = 0; // use current channel
                unicastPeer.ifidx = WIFI_IF_STA;
                unicastPeer.encrypt = false;

                esp_err_t result = esp_now_add_peer(&unicastPeer);
                if (result != ESP_OK)
                {
                    // printf("Failed to add bestHop peer: %s\n", esp_err_to_name(result));
                }
                else
                {
                    // printf("Unicast peer added for %02X:%02X:%02X:%02X:%02X:%02X\n",
                        //    bestHop[0], bestHop[1], bestHop[2], bestHop[3], bestHop[4], bestHop[5]);
                }
            }
        }
    }
    else
    {
        direct = true;
        printf("[HOP] Selected direct to router (RSSI: %ld dBm)\n", rssi_to_router);
    }
    saveNeighbors();

    vTaskDelete(NULL);
}
static void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len)
{
    int64_t recv_time_us = esp_timer_get_time();
    uint8_t payloadType = data[0];
    // printf("Payload type: %u\n", payloadType);

    uint8_t mac[6];
    if (!info || !info->rx_ctrl)
        return;
    memcpy(mac, info->src_addr, 6);
    int32_t rissin = info->rx_ctrl->rssi;

    if (memcmp(info->src_addr, selfMac, 6) == 0)
    {
        return;
    }
    switch (payloadType)
    {

    case MSG_HELLO:
    {
        MsgHello msg;
        memcpy(&msg, data + 1, sizeof(MsgHello));
        uint8_t id = info->src_addr[5];
        if (id >= largestid)
        {
            largestid = id;
            int64_t now_time = esp_timer_get_time();
            time_offset = now_time - msg.time_sent;
        }
        parseHello(mac, msg, rissin, len);
        break;
    }

    case MSG_BATCH:
        ParseBatch(data, len);

        break;
    case MSG_JOIN:
    {
        MsgHello msg;
        memcpy(&msg, data + 1, sizeof(MsgHello));
        uint8_t id = info->src_addr[5];
        if (id >= largestid)
        {
            largestid = id;
            int64_t now_time = esp_timer_get_time();
            time_offset = now_time - msg.time_sent;
        }

        parseHello(mac, msg, rissin, len);

        sendHello();

        xTaskCreate(decideHop, "HOP", 2048, NULL, 1, NULL);

        break;
    }

    case MSG_SYNC:
    {
        MsgSync sync;
        memcpy(&sync, data + 1, sizeof(MsgSync));
        uint8_t id = info->src_addr[5];
        time_offset = recv_time_us - sync.time_sent;
        // printf("Timeoffset %lld\n", time_offset);
        receivedSync = true;
        break;
    }
    default:
        break;
    }
}

// stuff
void idleTask(void *pvParameters)
{
    while (true)
    {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
void ledPower(bool onOff)
{
    gpio_config_t io_conf = {};
    io_conf.intr_type = GPIO_INTR_DISABLE;
    io_conf.mode = GPIO_MODE_OUTPUT;
    io_conf.pin_bit_mask = (1ULL << LED_PIN);
    gpio_config(&io_conf);

    gpio_set_level(LED_PIN, onOff); // ON
}

void bootESP()
{

    esp_event_loop_create_default();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_start();
    esp_wifi_get_mac(WIFI_IF_STA, selfMac);
    largestid = selfMac[5];

    if (esp_now_init() != ESP_OK)
    {
        return;
    }

    esp_now_register_recv_cb(onRecv);

    // ADD broadcast address
    esp_now_peer_info_t peer = {};
    memcpy(peer.peer_addr, broadcastAddress, 6);
    peer.channel = 0; 
    peer.ifidx = WIFI_IF_STA;
    peer.encrypt = false;

    if (!esp_now_is_peer_exist(broadcastAddress))
    {
        esp_err_t result = esp_now_add_peer(&peer);
        if (result != ESP_OK)
        {
            printf("Failed to add broadcast peer: %s\n", esp_err_to_name(result));
        }
    }
    if (memcmp(bestHop, broadcastAddress, 6) != 0)
    {
        if (!esp_now_is_peer_exist(bestHop))
        {
            esp_now_peer_info_t unicastPeer = {};
            memcpy(unicastPeer.peer_addr, bestHop, 6);
            unicastPeer.channel = 0; // use current channel
            unicastPeer.ifidx = WIFI_IF_STA;
            unicastPeer.encrypt = false;

            esp_err_t result = esp_now_add_peer(&unicastPeer);
            if (result != ESP_OK)
            {
                printf("Failed to add bestHop peer: %s\n", esp_err_to_name(result));
            }
            else
            {
                printf("Unicast peer added for %02X:%02X:%02X:%02X:%02X:%02X\n",
                       bestHop[0], bestHop[1], bestHop[2], bestHop[3], bestHop[4], bestHop[5]);
            }
        }
    }
}
#define SYNC_INTERVAL_MS 10000 // 20-second nominal period
#define SYNC_INTERVAL_US (SYNC_INTERVAL_MS * 1000LL)
void syncTimerTask(void *pvParameters)
{
    size_t attempts = 0;

    while (true)
    {
        int64_t now_us = esp_timer_get_time();
        int64_t net_time_us = now_us - time_offset;

        if (largestid == selfMac[5])
        {
            // printf("[SYNC] Net Time = %" PRId64 " µs | Attempt %zu\n", net_time_us, attempts);
            if (attempts % 2 == 0)
            {
                MSG msg{};
                msg.type = MSG_SYNC;
                msg.sync.time_sent = net_time_us;
                esp_now_send(broadcastAddress, (uint8_t *)&msg, sizeof(msg));
            }
        }
        else
        {
            // printf("[SYNC] Net Time = %" PRId64 " µs | Attempt %zu\n", net_time_us, attempts);
        }

        attempts++;

        // Wait until next SYNC-aligned interval
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
void transmitMessage(void *pvParameter)
{
    if (direct)
    {
    }
    else
    {
        int rand = 1000+ esp_random() % 3000;

        vTaskDelay(pdMS_TO_TICKS(rand));

        if (receivedMessage)
        {
            vTaskDelay(3000);
        }

        sendBatch();
    }
    vTaskDelete(NULL);
}

extern "C" void app_main()
{
    esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
    nvs_flash_init();
    bootESP();
    vTaskDelay(pdMS_TO_TICKS(100));

    if (wakeup_reason == ESP_SLEEP_WAKEUP_TIMER)
    {
        loadNeighbors();
        ledPower(true);
    }

    if (status == NET_NOT_FORMED)
    {
        for (int i = 0; i < 5 && status != NET_FORMED; ++i)
            senseRouter();

        for (int attempt = 0; attempt < 6 && neighbors.size() < NETWORK_SIZE; ++attempt)
        {
            sendHello();
            vTaskDelay(pdMS_TO_TICKS(1000 + (esp_random() % 800)));
        }

        if (neighbors.size() < NETWORK_SIZE)
        {
            for (int attempt = 0; attempt < 6 && neighbors.size() < NETWORK_SIZE; ++attempt)
            {
                sendJoin();
                vTaskDelay(pdMS_TO_TICKS(1000 + (esp_random() % 800)));
            }
        }

        xTaskCreate(decideHop, "Hop", 2096, NULL, 1, NULL);
    }

    if (xTaskCreate(syncTimerTask, "SyncTimer", 4096, NULL, 1, NULL) != pdPASS)
    {
        printf("Failed to create SyncTimer task\n");
    }
    else
    {
        printf("SyncTimer task running\n");
    }

    xTaskCreate(transmitMessage, "transmessage", 8096, NULL, 1, NULL);

    // Wait one full sync cycle before sleeping
    vTaskDelay(pdMS_TO_TICKS(SYNC_INTERVAL_MS));
    int64_t now_us = esp_timer_get_time();
    int64_t net_time_us = now_us - time_offset;

    int64_t next_sync_net_us = ((net_time_us / SYNC_INTERVAL_US) + 1) * SYNC_INTERVAL_US;
    int64_t next_sync_local_us = next_sync_net_us + time_offset;
    globalDelay = next_sync_local_us - now_us;

    if (globalDelay < 1000)
        globalDelay = 1000;


    printf("Sleeping for %lld us\n", globalDelay);
    esp_sleep_enable_timer_wakeup(globalDelay);
    esp_deep_sleep_start();
}

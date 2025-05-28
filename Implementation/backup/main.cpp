#include <string.h>
#include <stdio.h>
#include "esp_now.h"
#include "esp_wifi.h"
#include "esp_system.h"
#include "nvs_flash.h"
#include "esp_event.h"
#include "esp_mac.h"

extern "C" void app_main()
{
    nvs_flash_init();
    esp_event_loop_create_default();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_start();

    if (esp_now_init() != ESP_OK) {
        printf("ESP-NOW init failed\n");
        return;
    }

    // Print own MAC address
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    printf("My MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    // Register receive callback
    esp_now_register_recv_cb([](const esp_now_recv_info_t* info, const uint8_t* data, int len) {
        printf("Got message from: %02X:%02X:%02X:%02X:%02X:%02X, len=%d RSSI=%d\n ",
               info->src_addr[0], info->src_addr[1], info->src_addr[2],
               info->src_addr[3], info->src_addr[4], info->src_addr[5], len, info->rx_ctrl->rssi);

        printf("\n");
    });
}

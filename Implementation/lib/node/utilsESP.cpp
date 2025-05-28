#include <esp_wifi.h>
#include <esp_now.h>
#include <string>
#include <cstring>

#include "node.h"
#include <vector>
#include <nvs_flash.h>
#include <nvs.h>


bool saveVariable(const char* key, const void* data, size_t size) {
    nvs_handle_t handle;
    if (nvs_open("storage", NVS_READWRITE, &handle) != ESP_OK) return false;

    esp_err_t err = nvs_set_blob(handle, key, data, size);
    if (err == ESP_OK) nvs_commit(handle);

    nvs_close(handle);
    return (err == ESP_OK);
}

bool loadVariable(const char* key, void* data, size_t max_size) {
    nvs_handle_t handle;
    if (nvs_open("storage", NVS_READONLY, &handle) != ESP_OK) return false;

    size_t actual_size = 0;
    if (nvs_get_blob(handle, key, nullptr, &actual_size) != ESP_OK || actual_size > max_size) {
        nvs_close(handle);
        return false;
    }

    esp_err_t err = nvs_get_blob(handle, key, data, &actual_size);
    nvs_close(handle);
    return (err == ESP_OK);
}

void saveState(nGlobal global, nMessage message, nStatus status)
{
    nvs_handle_t handle;
    if (nvs_open("storage", NVS_READWRITE, &handle) != ESP_OK)
        return;

    nvs_set_i32(handle, "nGlobal", static_cast<int32_t>(global));
    nvs_set_i32(handle, "nMessage", static_cast<int32_t>(message));
    nvs_set_i32(handle, "nStatus", static_cast<int32_t>(status));

    nvs_commit(handle);
    nvs_close(handle);
}
void loadState(nGlobal &global, nMessage &message, nStatus &status)
{
    nvs_handle_t handle;
    if (nvs_open("storage", NVS_READONLY, &handle) != ESP_OK)
        return;

    int32_t g, m, s;
    if (nvs_get_i32(handle, "nGlobal", &g) == ESP_OK) global = static_cast<nGlobal>(g);
    if (nvs_get_i32(handle, "nMessage", &m) == ESP_OK) message = static_cast<nMessage>(m);
    if (nvs_get_i32(handle, "nStatus", &s) == ESP_OK)  status = static_cast<nStatus>(s);

    nvs_close(handle);
}

template <typename T>
void saveVectorToNVS(const char* blobKey, const char* countKey, const std::vector<T>& vec) {
    nvs_handle_t handle;
    if (nvs_open("storage", NVS_READWRITE, &handle) != ESP_OK)
        return;

    uint32_t count = vec.size();
    nvs_set_u32(handle, countKey, count);

    if (count > 0) {
        nvs_set_blob(handle, blobKey, vec.data(), count * sizeof(T));
    }

    nvs_commit(handle);
    nvs_close(handle);
}
template <typename T>
void loadVectorFromNVS(const char* blobKey, const char* countKey, std::vector<T>& vec) {
    nvs_handle_t handle;
    if (nvs_open("storage", NVS_READONLY, &handle) != ESP_OK)
        return;

    uint32_t count = 0;
    if (nvs_get_u32(handle, countKey, &count) != ESP_OK || count == 0) {
        nvs_close(handle);
        return;
    }

    vec.resize(count);
    size_t required_size = count * sizeof(T);
    if (nvs_get_blob(handle, blobKey, vec.data(), &required_size) != ESP_OK) {
        vec.clear();
    }

    nvs_close(handle);
}




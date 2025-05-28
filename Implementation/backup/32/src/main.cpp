#include "node.h"
#include "esp_log.h"


extern "C" void app_main() {
  nodeInstance.init("RouterSSID", "RouterPassword");
  nodeInstance.startESPNow();
  xTaskCreate(Node::fsmTask, "FSM", 4096, &nodeInstance, 1, nullptr);
}

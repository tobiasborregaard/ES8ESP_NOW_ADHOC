import cv2
import numpy as np
import json
import os

# --- File paths ---
room_path = "images/appartment.png"  # This seems to be your main image
bg_path = "images/apartment.png"     # Optional background blend (may not exist)
output_path = "images/sensor_overlay.png"
json_path = "json/sensorNodes.json"

# --- Load base image (room map) ---
room_map = cv2.imread(room_path)
if room_map is None:
    raise FileNotFoundError(f"Could not read room image: {room_path}")

# Try to load background image (optional)
use_blend = os.path.exists(bg_path)
if use_blend:
    background = cv2.imread(bg_path)
    if background is None:
        raise FileNotFoundError(f"Could not read background image: {bg_path}")

    # Resize if needed
    if room_map.shape[:2] != background.shape[:2]:
        room_map = cv2.resize(room_map, (background.shape[1], background.shape[0]))

    # Blend background with room overlay
    overlay = cv2.addWeighted(background, 0.6, room_map, 0.4, 0)
else:
    overlay = room_map.copy()

# --- Load sensor nodes ---
with open(json_path, "r") as f:
    sensor_nodes = json.load(f)

for node in sensor_nodes:
    x, y = node["x"], node["y"]
    label = node["room"]
    node_type = node.get("type", "sensor").lower()

    if node_type == "router":
        cv2.circle(overlay, (x, y), 8, (0, 255, 0), 2)  # Green ring
        cv2.putText(overlay, label, (x +15, y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    else:
        cv2.circle(overlay, (x, y), 6, (0, 0, 255), -1)  # Red dot
        cv2.putText(overlay, label, (x - 10, y + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

# --- Save result ---
cv2.imwrite(output_path, overlay)
print(f"[INFO] Sensor overlay saved to {output_path}")

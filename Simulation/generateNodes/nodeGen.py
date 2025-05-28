import cv2
import numpy as np
import json

# Load base image and room map
background = cv2.imread("images/appartment.png")               # Your original architectural plan
# print(np.shape(background))
room_map = cv2.imread("images/appartment.png")              # Color-filled room segmentation
# print(np.shape(room_map))
nodes = json.load(open("json/fire_nodes.json"))

# Invert the room map for better overlay visibility
room_map_inv = cv2.bitwise_not(room_map)

# Resize room_map to match background if needed
if room_map.shape[:2] != background.shape[:2]:
    room_map_inv = cv2.resize(room_map_inv, (background.shape[1], background.shape[0]))

# Overlay room map onto background
overlay = cv2.addWeighted(background, 0.6, room_map_inv, 0.4, 0)

# # Draw detector nodes
# for node in nodes:
#     x, y = node["x"], node["y"]
#     cv2.circle(overlay, (x, y), 6, (0, 0, 255), -1)  # Red filled circle
#     cv2.putText(overlay, node["room"], (x + 8, y - 8),
#                 cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

# Save overlay
cv2.imwrite("overlay2.png", overlay)

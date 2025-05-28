import json
import cv2
import numpy as np

# Load JSON
json_path = "json/fire_nodes.json"
with open(json_path, "r") as f:
    node_data = json.load(f)

# Load image
bg = cv2.imread("images/appartment.png")
bg_display = bg.copy()

selected_idx = None

def draw_nodes(img, nodes, selected=None):
    display = img.copy()
    for i, node in enumerate(nodes):
        pos = (node["x"], node["y"])
        color = (0, 0, 255) if i == selected else (0, 165, 255)
        cv2.circle(display, pos, 10, color, -1)
        cv2.putText(display, node["room"], (pos[0] + 10, pos[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return display

def click_event(event, x, y, flags, param):
    global selected_idx, bg_display
    if event == cv2.EVENT_LBUTTONDOWN:
        min_dist = float("inf")
        selected = None
        for i, node in enumerate(node_data):
            dist = np.linalg.norm(np.array([node["x"], node["y"]]) - np.array([x, y]))
            if dist < 20:
                if dist < min_dist:
                    min_dist = dist
                    selected = i
        selected_idx = selected
        bg_display = draw_nodes(bg, node_data, selected_idx)

    elif event == cv2.EVENT_MOUSEMOVE and flags == cv2.EVENT_FLAG_LBUTTON and selected_idx is not None:
        node_data[selected_idx]["x"] = x
        node_data[selected_idx]["y"] = y
        bg_display = draw_nodes(bg, node_data, selected_idx)

# Create a window that fits the image exactly
cv2.namedWindow("Edit Nodes", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Edit Nodes", bg.shape[1], bg.shape[0])
cv2.setMouseCallback("Edit Nodes", click_event)

bg_display = draw_nodes(bg, node_data)

while True:
    cv2.imshow("Edit Nodes", bg_display)
    key = cv2.waitKey(10) & 0xFF
    if key == 27:  # ESC to quit
        break
    elif key == ord("s"):
        with open("fire_nodes_edited.json", "w") as f:
            json.dump(node_data, f, indent=2)
        print("Saved to fire_nodes_edited.json")

cv2.destroyAllWindows()

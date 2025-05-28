import cv2
import numpy as np

# Load RGBA image and extract alpha
img = cv2.imread("images/floorplan_binary_mask_ALPHA.png", cv2.IMREAD_UNCHANGED)
alpha = img[:, :, 3]
print("Unique alpha values:", np.unique(alpha))  # should show 0, 245, 255

# Create masks
WALL_VAL = 255
DOOR_VAL = 245

# Binary masks
wall_mask = (alpha == WALL_VAL).astype(np.uint8)
door_mask = (alpha == DOOR_VAL).astype(np.uint8)
free_space_mask = ((alpha == 0) | (alpha == DOOR_VAL)).astype(np.uint8) * 255

# Step 1: Close doors temporarily for room segmentation
mask_closed = free_space_mask.copy()

# Optional: morphological close to help with noise/gaps
kernel = np.ones((7, 7), np.uint8)
mask_closed = cv2.morphologyEx(mask_closed, cv2.MORPH_CLOSE, kernel)

# Step 2: Remove exterior space using flood fill
filled = mask_closed.copy()
h, w = filled.shape
cv2.floodFill(filled, np.zeros((h + 2, w + 2), np.uint8), (5, 5), 0)

# Step 3: Detect room contours
contours, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Step 4: Generate outputs
room_vis = cv2.cvtColor(free_space_mask, cv2.COLOR_GRAY2BGR)
room_ids = np.zeros_like(free_space_mask, dtype=np.uint8)

room_id = 1
for cnt in contours:
    area = cv2.contourArea(cnt)
    if area > 2000:
        color = tuple(np.random.randint(100, 255, 3).tolist())
        cv2.drawContours(room_vis, [cnt], -1, color, -1)
        cv2.drawContours(room_ids, [cnt], -1, room_id, -1)
        print(f"Detected room {room_id} (area: {int(area)})")
        room_id += 1


cv2.imwrite("images/debug_free_space_mask.png", free_space_mask)

cv2.imshow("Rooms", room_vis)
cv2.waitKey(0)
cv2.destroyAllWindows()

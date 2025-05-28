import cv2
import numpy as np
import json
from math import ceil
from collections import defaultdict

# Load inputs
room_map = cv2.imread("images/appartment.png")
with open("json/fire_nodes.json", "r") as f:
    seed_nodes = json.load(f)

# Build room ID map from unique RGBs
pixels = room_map.reshape(-1, 3)
unique_colors, inverse_indices = np.unique(pixels, axis=0, return_inverse=True)
room_id_map = (inverse_indices + 1).reshape(room_map.shape[:2]).astype(np.uint16)

# Define constants
scale_m_per_px = 15.01 / 867               # meters per pixel (from garage width)
area_per_px_m2 = scale_m_per_px ** 2       # m² per pixel
spacing_margin_px = int(1 / scale_m_per_px)
area_per_detector_m2 = 10

# Match room labels to room_id
room_label_map = defaultdict(list)
for node in seed_nodes:
    x, y = node["x"], node["y"]
    if 0 <= x < room_id_map.shape[1] and 0 <= y < room_id_map.shape[0]:
        room_id = int(room_id_map[y, x])
        room_label_map[room_id].append((node["room"], (x, y)))

# Place detectors
sensor_nodes = []

for room_id, labels in room_label_map.items():
    mask = (room_id_map == room_id).astype(np.uint8) * 255
    if cv2.countNonZero(mask) == 0:
        continue

    # Calculate area before erosion
    room_area_px = np.count_nonzero(mask)
    room_area_m2 = room_area_px * area_per_px_m2
    total_detectors = max(1, ceil(room_area_m2 / area_per_detector_m2))
    detectors_per_label = max(1, total_detectors // len(labels))

    # Try safe zone erosion
    erosion_kernel = np.ones((spacing_margin_px, spacing_margin_px), np.uint8)
    safe_mask = cv2.erode(mask, erosion_kernel)
    safe_pts = np.argwhere(safe_mask == 255)

    # Fallback if too small
    if len(safe_pts) == 0:
        print(f"⚠️ Room '{labels[0][0]}' (ID {room_id}) too small after erosion — using full mask.")
        safe_pts = np.argwhere(mask == 255)

    for label, (lx, ly) in labels:
        selected = []
        used_mask = np.zeros(len(safe_pts), dtype=bool)

        # Start with the label point (closest safe point)
        dists = np.linalg.norm(safe_pts - np.array([ly, lx]), axis=1)
        first_idx = np.argmin(dists)
        selected.append(safe_pts[first_idx])
        used_mask[first_idx] = True

        # Add more detectors by farthest point sampling
        while len(selected) < detectors_per_label:
            # Distance to nearest selected point for all candidates
            dists_to_selected = np.min([
                np.linalg.norm(safe_pts - np.array([pt[0], pt[1]]), axis=1)
                for pt in selected
            ], axis=0)

            # Exclude already used points
            dists_to_selected[used_mask] = -1

            # Select the point farthest from any already selected
            next_idx = np.argmax(dists_to_selected)
            if dists_to_selected[next_idx] <= 0:
                break  # no usable new points

            selected.append(safe_pts[next_idx])
            used_mask[next_idx] = True

        # Record selected points
        for pt in selected:
            y, x = int(pt[0]), int(pt[1])
            sensor_nodes.append({
                "id": f"{label}_{x}_{y}",
                "room": label,
                "x": x,
                "y": y,
                "room_id": room_id,
                "room_area_m2": round(room_area_m2, 2),
                "type": "sensor"
            })

# Save
with open("json/sensorNodes.json", "w") as f:
    json.dump(sensor_nodes, f, indent=2)

print("✅ sensorNodes.json created with", len(sensor_nodes), "nodes.")

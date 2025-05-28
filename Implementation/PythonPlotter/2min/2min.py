import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import os

# Define log file paths
# Base directory to store logs
movefolder = "/home/borregaard/Documents/projekts/es8/ESP8266-RSSI-Test/timeMeas/"
# Find the next folder number
existing = [int(f) for f in os.listdir(movefolder) if f.isdigit()]
next_folder_num = max(existing) if existing else 1
folder_path = os.path.join(movefolder, str(next_folder_num))

log_paths = {
    "Node1": os.path.join(folder_path, "node1_log.txt"),
    "Node2": os.path.join(folder_path, "node2_log.txt"),
    "Node3": os.path.join(folder_path, "node3_log.txt")
}

# Function to parse attempts from log files
def parse_attempts(file_path):
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+).*Attempt (\d+)")
    timestamps = []
    attempts = []
    with open(file_path, "r") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                timestamps.append(datetime.fromisoformat(match.group(1)))
                attempts.append(int(match.group(2)))
    return list(zip(timestamps, attempts))

# Parse all node logs
attempt_data = {node: parse_attempts(path) for node, path in log_paths.items()}

# Detect reset in Node1 (where attempt decreases)
reset_time = None
for i in range(1, len(attempt_data["Node1"])):
    if attempt_data["Node1"][i][1] < attempt_data["Node1"][i - 1][1]:
        reset_time = attempt_data["Node1"][i][0]
        break

# Define expanded time window
start_time = reset_time - timedelta(minutes=3)
end_time = reset_time + timedelta(minutes=3)

# Trim and plot
plt.figure(figsize=(14, 6))
colors = {"Node1": "dodgerblue", "Node2": "orange", "Node3": "limegreen"}
guide_lines = [ts for ts, _ in attempt_data["Node1"] if reset_time <= ts <= reset_time + timedelta(minutes=3)]


for node, data in attempt_data.items():
    filtered = [(ts, val) for ts, val in data if start_time <= ts <= end_time]
    if filtered:
        ts_list, val_list = zip(*filtered)
        plt.plot(ts_list, val_list, marker='o', linestyle='-', label=node, color=colors[node])

# Add vertical guide lines
for guide_ts in guide_lines:
    plt.axvline(x=guide_ts, color='red', linestyle='--', linewidth=0.8)

plt.xlabel("Real Time")
plt.ylabel("Attempt Count")
plt.title("SYNC Attempt Count Over Time (±3 min around Node 1 Reset)")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.xticks(rotation=45)

plt.show()

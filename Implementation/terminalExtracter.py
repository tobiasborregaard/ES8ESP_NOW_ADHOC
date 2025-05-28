import serial
import time
import re
from datetime import datetime
from threading import Thread
import os

# Serial port mapping
ports = {
    "node1": "/dev/ttyUSB0",
    "node2": "/dev/ttyUSB1",
    "node3": "/dev/ttyUSB2",
}

# Base directory to store logs
movefolder = "/home/borregaard/Documents/projekts/es8/ESP8266-RSSI-Test/timeMeas/"

# Find the next folder number
existing = [int(f) for f in os.listdir(movefolder) if f.isdigit()]
next_folder_num = max(existing) + 1 if existing else 1
folder_path = os.path.join(movefolder, str(next_folder_num))
os.makedirs(folder_path)

# Compile pattern to filter lines
KEEP = re.compile(r"\[SYNC\]\s+Net Time", re.IGNORECASE)

# Serial reader thread per node
def reader(node, port):
    try:
        ser = serial.Serial(port, 115200, timeout=1)
    except serial.SerialException as e:
        print(f"Failed to open {port}: {e}")
        return

    filepath = os.path.join(folder_path, f"{node}_log.txt")
    with open(filepath, "w") as f:
        while True:
            raw = ser.readline()
            if not raw:
                continue
            try:
                line = raw.decode(errors="ignore").strip()
            except UnicodeDecodeError:
                continue

            if KEEP.search(line):
                timestamp = datetime.now().isoformat()
                f.write(f"{timestamp} [{node}] {line}\n")
                f.flush()

# Start a thread for each node
for node, port in ports.items():
    Thread(target=reader, args=(node, port), daemon=True).start()

# Idle forever
while True:
    time.sleep(60)

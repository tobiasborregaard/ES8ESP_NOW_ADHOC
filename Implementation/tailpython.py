#!/usr/bin/env python3
"""
Build a ladder / swim-lane plot from the nodeX_log.txt files that contain
lines like

  2025-05-24T22:47:06.087185 [node1] [SYNC] Net Time = 296930344 µs | Attempt 30
"""
import re
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt

# --------------------------------------------------------------------------- #
# 1.  Gather all log lines                                                    #
# --------------------------------------------------------------------------- #
log_files = sorted(Path('.').glob('node*_log.txt'))          # node1_log.txt ...

# Example line regexp  (timestamp) (node)             (rest)
PAT = re.compile(r'^(?P<ts>[\dT:\.\-]+)\s+\[(?P<node>[^]]+)\].*\[SYNC\]')

records = []                                                 # (sec_from_start, node)

for lf in log_files:
    with lf.open() as f:
        for line in f:
            m = PAT.match(line)
            if m:
                ts_iso  = m['ts']
                node    = m['node']
                dt      = datetime.fromisoformat(ts_iso)
                records.append((dt, node))

if not records:
    raise SystemExit("No SYNC lines found!")

# --------------------------------------------------------------------------- #
# 2.  Normalise timestamps to seconds from the beginning                      #
# --------------------------------------------------------------------------- #
records.sort(key=lambda r: r[0])           # earliest first
t0 = records[0][0]                         # reference time

lane_map = {name: idx for idx, name in enumerate(sorted({r[1] for r in records}))}
# lane_map  ->  {'node1': 0, 'node2': 1, ...}

xs, ys = [], []
for dt, node in records:
    xs.append((dt - t0).total_seconds())
    ys.append(lane_map[node])

# --------------------------------------------------------------------------- #
# 3.  Draw ladder                                                             #
# --------------------------------------------------------------------------- #
fig, ax = plt.subplots(figsize=(10, 4))

# horizontal lanes
for node, lane in lane_map.items():
    ax.hlines(lane, xmin=0, xmax=max(xs) * 1.05, color='lightgrey', lw=1)
    ax.text(-0.5, lane, node, va='center', ha='right', fontsize=10, fontweight='bold')

# event markers
ax.scatter(xs, ys, s=18, c='tab:blue')

ax.set_xlabel("Seconds since first log line")
ax.set_ylabel("Node")
ax.set_yticks([])                           # we placed labels ourselves
ax.set_title("ESP-NOW SYNC events (ladder view)")
ax.grid(axis='x', linestyle='--', alpha=0.3)

plt.tight_layout()
plt.show()

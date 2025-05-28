#!/bin/bash

# Upload and/or monitor the specified node using PlatformIO
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

upload_and_monitor_node() {
    local NODE=$1
    local MONITOR_ONLY=$2

    if ! [[ "$NODE" =~ ^node[123]$ ]]; then
        echo "Invalid node: $NODE. Must be node1, node2, or node3."
        return 1
    fi

    if [ "$MONITOR_ONLY" = false ]; then
        echo "Uploading $NODE..."
        pio run -e "$NODE" --target upload
        if [ $? -ne 0 ]; then
            echo "Upload failed for $NODE."
            return 1
        fi
    fi

    echo "Monitoring $NODE..."
    pio device monitor -e "$NODE"
}
if [[ "$1" == "-a" ]]; then
    MONITOR_ONLY=false
    if [[ "$2" == "-m" ]]; then
        MONITOR_ONLY=true
    fi

    SESSION="0"
    if tmux has-session -t "$SESSION" 2>/dev/null; then
        echo "Killing existing tmux session '$SESSION'..."
        tmux kill-session -t "$SESSION"
    fi

    echo "Launching node1, node2, and node3 in vertical split..."

    CMD1="pio device monitor -e node1"
    CMD2="pio device monitor -e node2"
    CMD3="pio device monitor -e node3"
    CMD4="pio device monitor -e node4"
    if [ "$MONITOR_ONLY" = false ]; then
        CMD1="pio run -e node1 --target upload && $CMD1"
        CMD2="pio run -e node2 --target upload && $CMD2"
        CMD3="pio run -e node3 --target upload && $CMD3"
        CMD4="pio run -e node3 --target upload && $CMD4"
    fi

    tmux new-session -d -s "$SESSION" "$CMD1"
    tmux split-window -v -t "$SESSION:0.0" "$CMD2"
    tmux split-window -v -t "$SESSION:0.1" "$CMD3"
     tmux split-window -v -t "$SESSION:0.2" "$CMD4"
    tmux select-layout -t "$SESSION" even-vertical
    tmux attach-session -t "$SESSION"
    exit 0
fi


# Regular single-node mode
if [ $# -lt 1 ]; then
    echo "Usage: $0 <node number: 1, 2, or 3> [-m] | -a"
    exit 1
fi

NODE="node$1"
MONITOR_ONLY=false

if [[ "$2" == "-m" ]]; then
    MONITOR_ONLY=true
fi

upload_and_monitor_node "$NODE" "$MONITOR_ONLY"

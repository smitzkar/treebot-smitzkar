#!/bin/bash
echo "Starting main.py..."
source /home/treebot/talking-treebot/treebot-env/bin/activate
#python /home/treebot/talking-treebot/main.py &
python /home/treebot/talking-treebot/2026-01-16_karl-main.py &
echo $! > main_pid.txt  # Store the PID of the Python script
echo "main.py script finished"

## 2026-03-08: I don't think this is the one that was actually running on the pi
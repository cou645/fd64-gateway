#!/bin/sh
ps -o pid,pri,comm 2>/dev/null | head -1
for pid in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
    [ -r /proc/$pid/stat ] || continue
    policy=$(cat /proc/$pid/stat 2>/dev/null | cut -d' ' -f42)
    rtprio=$(cat /proc/$pid/stat 2>/dev/null | cut -d' ' -f40)
    [ "$policy" != "0" ] && [ "$rtprio" != "0" ] || continue
    cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' | head -c 60)
    echo "$pid policy=$policy rtprio=$rtprio $cmd"
done
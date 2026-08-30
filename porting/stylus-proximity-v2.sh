#!/bin/bash

# Monitor stylus proximity events and disable touchscreen when stylus is near

TOUCHSCREEN_ID="ELAN90FC:00 04F3:2D73"
STYLUS_ID="ELAN90FC:00 04F3:2D73 Stylus Pen (0x1)"

# Function to enable touchscreen
enable_touchscreen() {
    echo "$(date): Enabling touchscreen"
    xinput enable "$TOUCHSCREEN_ID"
}

# Function to disable touchscreen
disable_touchscreen() {
    echo "$(date): Disabling touchscreen"
    xinput disable "$TOUCHSCREEN_ID"
}

# Initial state
LAST_STATE=""

# Monitor for stylus proximity events using xinput test
xinput test "$STYLUS_ID" | while read -r line; do
    # Look for proximity events
    if [[ "$line" == *"proximity"* ]]; then
        if [[ "$line" == *"in"* ]]; then
            # Stylus is in proximity
            if [[ "$LAST_STATE" != "in" ]]; then
                echo "$(date): Stylus in proximity"
                disable_touchscreen
                LAST_STATE="in"
            fi
        elif [[ "$line" == *"out"* ]]; then
            # Stylus is out of proximity
            if [[ "$LAST_STATE" != "out" ]]; then
                echo "$(date): Stylus out of proximity"
                enable_touchscreen
                LAST_STATE="out"
            fi
        fi
    fi
done

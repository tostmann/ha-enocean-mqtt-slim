#!/bin/bash

echo "[Standalone] Starting EnOcean MQTT Gateway..."

# Defaults setzen, falls in docker-compose vergessen
if [ -z "$SERIAL_PORT" ]; then
    echo "[Warn] SERIAL_PORT not set. Defaulting to /dev/ttyUSB0"
    export SERIAL_PORT="/dev/ttyUSB0"
fi

# Info-Ausgabe
echo "Configuration:"
echo "  - Interface: $SERIAL_PORT"
echo "  - MQTT Host: ${MQTT_HOST:-localhost}"
echo "  - Log Level: ${LOG_LEVEL:-INFO}"

# Start
cd /app
exec python3 main.py

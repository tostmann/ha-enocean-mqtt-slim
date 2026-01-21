#!/usr/bin/env bash

# Erkennen, ob wir im Home Assistant Modus sind
if command -v bashio >/dev/null 2>&1; then
    MODE="HA"
elif [ -f "/usr/lib/bashio/bashio" ]; then
    source /usr/lib/bashio/bashio
    MODE="HA"
else
    MODE="STANDALONE"
fi

# Helfer-Funktion für Configs
get_config() {
    if [ "$MODE" = "HA" ]; then
        if bashio::config.has_value "$1"; then bashio::config "$1"; fi
    else
        # Im Standalone-Mode nehmen wir ENV-Vars direkt (werden von Python gelesen)
        echo "" 
    fi
}

echo "[$(date +'%T')] Starting in $MODE mode..."

# --- 1. Verbindungswahl ---
# Im Standalone-Betrieb wird SERIAL_PORT direkt per ENV gesetzt.
# Im HA-Betrieb müssen wir es aus der JSON-Config parsen.

if [ "$MODE" = "HA" ]; then
    # Werte aus HA Config holen
    HA_TCP=$(bashio::config 'tcp_address')
    HA_SERIAL=$(bashio::config 'serial_device')
    
    if [ -n "$HA_TCP" ]; then
        export SERIAL_PORT="$HA_TCP"
        echo "Using TCP Address from HA Config: $HA_TCP"
    elif [ -n "$HA_SERIAL" ] && [ "$HA_SERIAL" != "null" ]; then
        export SERIAL_PORT="$HA_SERIAL"
        echo "Using Serial Device from HA Config: $HA_SERIAL"
    else
        echo "Warning: No device configured in HA. Defaulting to /dev/ttyUSB0"
        export SERIAL_PORT="/dev/ttyUSB0"
    fi
    
    # Weitere HA-Configs exportieren
    export LOG_LEVEL=$(bashio::config 'log_level')
    export MQTT_HOST=$(bashio::services mqtt "host")
    export MQTT_PORT=$(bashio::services mqtt "port")
    export MQTT_USER=$(bashio::services mqtt "username")
    export MQTT_PASSWORD=$(bashio::services mqtt "password")
    export RESTORE_STATE=$(bashio::config 'restore_state')
fi

# Fallback/Defaults für Standalone, falls Variablen leer sind
export SERIAL_PORT="${SERIAL_PORT:-/dev/ttyUSB0}"
export MQTT_HOST="${MQTT_HOST:-localhost}"
export MQTT_PORT="${MQTT_PORT:-1883}"

echo "Target Interface: $SERIAL_PORT"
echo "MQTT Broker: $MQTT_HOST:$MQTT_PORT"

# --- 2. Start ---
cd /app
exec python3 main.py

#!/usr/bin/with-contenv bashio

# ------------------------------------------------------------------------------
# EnOcean MQTT TCP - Startup Script
# ------------------------------------------------------------------------------

# 1. Version automatisch ermitteln und EXPORTIEREN
ADDON_VERSION="$(bashio::addon.version)"
export ADDON_VERSION

bashio::log.info "---------------------------------------------------"
bashio::log.info "Starting EnOcean MQTT TCP..."
bashio::log.info "Add-on Version: ${ADDON_VERSION}"
bashio::log.info "---------------------------------------------------"

# 2. Konfiguration prüfen
if bashio::config.has_value 'serial_port'; then
    SERIAL_PORT=$(bashio::config 'serial_port')
    export SERIAL_PORT
    bashio::log.info "Using Serial Port: ${SERIAL_PORT}"
else
    bashio::log.warning "No serial port configured! Running in simulation/view-only mode."
fi

# MQTT Config
export MQTT_HOST=$(bashio::config 'mqtt_host')
export MQTT_PORT=$(bashio::config 'mqtt_port')
export MQTT_USER=$(bashio::config 'mqtt_user')
export MQTT_PASSWORD=$(bashio::config 'mqtt_password')

# State Restore Config
export RESTORE_STATE=$(bashio::config 'restore_state')
export RESTORE_DELAY=$(bashio::config 'restore_delay')

# 3. Python App starten
cd /app
source venv/bin/activate

# Uvicorn wird direkt im Python-Skript gestartet
python3 main.py

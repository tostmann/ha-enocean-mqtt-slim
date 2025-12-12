#!/usr/bin/with-contenv bashio

# Get configuration
SERIAL_PORT=$(bashio::config 'serial_port')
LOG_LEVEL=$(bashio::config 'log_level')

# Export environment variables
export SERIAL_PORT="${SERIAL_PORT}"
export LOG_LEVEL="${LOG_LEVEL}"
export MQTT_HOST=$(bashio::services mqtt "host")
export MQTT_PORT=$(bashio::services mqtt "port")
export MQTT_USER=$(bashio::services mqtt "username")
export MQTT_PASSWORD=$(bashio::services mqtt "password")

# Log startup
bashio::log.info "Starting EnOcean MQTT Slim..."
bashio::log.info "Serial Port: ${SERIAL_PORT}"
bashio::log.info "Log Level: ${LOG_LEVEL}"
bashio::log.info "MQTT Broker: ${MQTT_HOST}:${MQTT_PORT}"

# Start the application
cd /app
exec python3 main.py

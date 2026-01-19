#!/usr/bin/with-contenv bashio

# Get configuration
# We check if a custom address (TCP) is provided first
if bashio::config.has_value 'custom_address'; then
    SERIAL_PORT=$(bashio::config 'custom_address')
    bashio::log.info "Using Custom/TCP Address: ${SERIAL_PORT}"
elif bashio::config.has_value 'serial_device'; then
    SERIAL_PORT=$(bashio::config 'serial_device')
    bashio::log.info "Using Serial Device: ${SERIAL_PORT}"
else
    # Fallback/Error if nothing is configured
    bashio::log.warning "No serial device or custom address configured!"
    SERIAL_PORT=""
fi

LOG_LEVEL=$(bashio::config 'log_level')

# Export environment variables for the Python app
export SERIAL_PORT="${SERIAL_PORT}"
export LOG_LEVEL="${LOG_LEVEL}"
export MQTT_HOST=$(bashio::services mqtt "host")
export MQTT_PORT=$(bashio::services mqtt "port")
export MQTT_USER=$(bashio::services mqtt "username")
export MQTT_PASSWORD=$(bashio::services mqtt "password")
export RESTORE_STATE=$(bashio::config 'restore_state')
export RESTORE_DELAY=$(bashio::config 'restore_delay')

# Log startup
bashio::log.info "Starting EnOcean MQTT Slim..."
bashio::log.info "Target Interface: ${SERIAL_PORT}"
bashio::log.info "Log Level: ${LOG_LEVEL}"
bashio::log.info "MQTT Broker: ${MQTT_HOST}:${MQTT_PORT}"

# Start the application
cd /app
exec python3 main.py

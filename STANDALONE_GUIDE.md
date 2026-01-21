# Standalone Installation Guide (Docker)

This guide describes how to run the **EnOcean MQTT Gateway** as a standalone Docker container, independent of Home Assistant Supervisor. This is ideal for users of Zigbee2MQTT, Home Assistant Core, or other home automation systems (OpenHAB, ioBroker, etc.).

## Prerequisites

* **Docker** & **Docker Compose** installed on your system.
* An **EnOcean Transceiver** (USB Stick or TCP Bridge).

## Quick Start

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/tostmann/ha-enocean-mqtt-busware.git](https://github.com/tostmann/ha-enocean-mqtt-busware.git)
    cd ha-enocean-mqtt-busware
    ```

2.  **Configuration**
    Edit the `docker-compose.yml` file to match your environment.
    
    * **Serial Port:** Set `SERIAL_PORT` to your USB device (e.g., `/dev/ttyUSB0`) or TCP bridge address.
    * **MQTT:** Configure your broker credentials.
    
    **Example:**
    ```yaml
    environment:
      - SERIAL_PORT=/dev/ttyUSB0
      - MQTT_HOST=192.168.1.50
    ```

3.  **Run**
    ```bash
    docker-compose up -d --build
    ```

4.  **Access Dashboard**
    Open your browser and navigate to:
    
    👉 **http://YOUR_SERVER_IP:8099**

## Configuration Reference

The container is configured entirely via environment variables.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SERIAL_PORT` | Device path (`/dev/ttyUSB0`) or TCP URL (`tcp://ip:port`) | required |
| `MQTT_HOST` | Hostname/IP of MQTT Broker | `localhost` |
| `MQTT_PORT` | MQTT Port | `1883` |
| `MQTT_USER` | MQTT Username | - |
| `MQTT_PASSWORD` | MQTT Password | - |
| `LOG_LEVEL` | Logging verbosity (`INFO`, `DEBUG`, `WARNING`) | `INFO` |
| `RESTORE_STATE` | Restore last known device states on startup | `true` |

## Troubleshooting

* **USB Permission Denied:**
    If the container cannot access `/dev/ttyUSB0`, you may need to add your user to the `dialout` group or run the container with `privileged: true` (not recommended for production).
    
* **Web UI not reachable:**
    Check if port `8099` is blocked by a firewall. You can change the external port in `docker-compose.yml`:
    ```yaml
    ports:
      - "9000:8099" # Accessible via Port 9000
    ```

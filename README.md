# EnOcean MQTT Slim - Home Assistant Addon

A lightweight, user-friendly EnOcean to MQTT bridge for Home Assistant with a built-in web UI for device management.

## Features

✅ **Zero Configuration Files** - Everything managed through web UI  
✅ **150+ Built-in EEP Profiles** - Including Kessel Staufix Control (MV-01-01)  
✅ **Auto-Discovery** - Teach-in mode with automatic device detection  
✅ **Web-Based Management** - Add, edit, and monitor devices via browser  
✅ **MQTT Auto-Discovery** - Entities appear automatically in Home Assistant  
✅ **Better USB Communication** - Direct Python serial implementation  
✅ **MIT Licensed** - Free for commercial and personal use  

## Installation

### Step 1: Add Repository

1. Open Home Assistant
2. Go to **Settings** → **Add-ons** → **Add-on Store**
3. Click the three dots menu (⋮) in the top right
4. Select **Repositories**
5. Add this URL: `https://github.com/ESDN83/ha-enocean-mqtt-slim`
6. Click **Add**

### Step 2: Install Addon

1. Find "EnOcean MQTT Slim" in the Add-on Store
2. Click **Install**
3. Wait for installation to complete

### Step 3: Configure

1. Go to the **Configuration** tab
2. Select your serial port (e.g., `/dev/ttyUSB0`)
3. Click **Save**
4. Start the addon

### Step 4: Add Devices

1. Click **Open Web UI** in the addon page
2. Click **Add Device**
3. Choose **Teach-In Mode** or **Manual Entry**
4. For teach-in: Click "Start Teach-In" and trigger your device
5. Device appears automatically in Home Assistant!

## Supported Devices

This addon includes 150+ EEP profiles for various EnOcean devices:

- **Kessel Staufix Control** (MV-01-01) - Backwater alarm
- **Temperature Sensors** (A5-02-xx)
- **Rocker Switches** (F6-02-xx)
- **Occupancy Sensors** (A5-07-xx)
- **Window Contacts** (D5-00-01)
- **LED Controllers** (D2-01-xx)
- And many more...

## Web UI Features

### Dashboard
- View all devices at a glance
- See online/offline status
- Monitor signal strength (RSSI)
- Quick access to device actions

### Device Management
- **Teach-In Mode** - Automatic device detection
- **Manual Entry** - Add devices by ID
- **Edit Devices** - Change names, EEP profiles
- **Delete Devices** - Remove unwanted devices

### EEP Browser
- Browse 150+ built-in profiles
- Search by name or EEP code
- View profile details

### Settings
- Gateway information
- Serial port configuration
- MQTT status
- System diagnostics

## Example: Kessel Staufix Control

The Kessel Staufix Control backwater alarm is fully supported:

1. **Add Device** via teach-in or manual entry
2. **Device ID**: Your device's EnOcean ID (e.g., `05834fa4`)
3. **EEP Profile**: MV-01-01 (Kessel Staufix Control)
4. **Entity Created**: `binary_sensor.staufix_control_alarm`
5. **Device Class**: `problem` (shows as alert in HA)

The alarm entity will automatically update when water is detected!

## Architecture

```
EnOcean Device → USB Stick → Serial → ESP3 Parser → 
EEP Matcher → Data Extractor → MQTT → HA Discovery → HA Entities
```

## Technology Stack

- **Python 3.11+** - Core application
- **FastAPI** - Web UI backend
- **SQLite** - Device database
- **pyserial** - Serial communication
- **paho-mqtt** - MQTT client
- **Bootstrap 5** - Responsive UI

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `serial_port` | USB stick device path | Auto-detect |
| `log_level` | Logging verbosity | `info` |

That's it! No complex YAML files needed.

## Troubleshooting

### Device Not Detected

1. Check serial port is correct
2. Ensure USB stick is connected
3. Try teach-in mode again
4. Check addon logs

### Entities Not Appearing in HA

1. Verify MQTT broker is running
2. Check MQTT integration is configured
3. Restart Home Assistant
4. Check web UI shows device as online

### USB Stick Not Found

1. Go to **Settings** → **System** → **Hardware**
2. Find your EnOcean USB stick path
3. Update serial port in addon configuration

## Development

This addon is built from scratch with:
- Clean, maintainable Python code
- Comprehensive EEP library
- User-friendly web interface
- No licensing restrictions (MIT)

## Credits

- EEP profile structure inspired by [ioBroker.enocean](https://github.com/Jey-Cee/ioBroker.enocean)
- Built for the Home Assistant community
- Developed by ESDN83

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Support

For issues and feature requests:
- GitHub Issues: https://github.com/ESDN83/ha-enocean-mqtt-slim/issues
- Home Assistant Community: [Link to forum thread]

## Changelog

### Version 1.0.0 (Initial Release)
- Web UI for device management
- 150+ built-in EEP profiles
- Auto-discovery via teach-in
- MQTT auto-discovery for HA
- SQLite device database
- Kessel Staufix Control support (MV-01-01)

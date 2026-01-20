import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DeviceManager:
    def __init__(self, storage_path=None):
        if storage_path:
            self.storage_path = storage_path
        else:
            if os.path.exists('/data') and os.access('/data', os.W_OK):
                self.storage_path = '/data/devices.json'
            else:
                self.storage_path = os.path.join(os.getcwd(), 'devices.json')
                logger.info(f"Running locally. Using storage path: {self.storage_path}")

        self.devices = {}
        self.load_devices()

    def load_devices(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    self.devices = json.load(f)
            except Exception as e:
                logger.error(f"Error loading devices: {e}")
                self.devices = {}
        else:
            self.devices = {}

    def save_devices(self):
        try:
            directory = os.path.dirname(self.storage_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(self.devices, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving devices: {e}")

    def list_devices(self):
        return list(self.devices.values())

    def get_device(self, device_id):
        return self.devices.get(device_id)

    # NEU: parameter provisioning_data
    def add_device(self, device_id, name, eep, manufacturer="EnOcean", provisioning_data=None):
        if device_id in self.devices and self.devices[device_id].get('eep') != 'pending':
            return False
            
        self.devices[device_id] = {
            "id": device_id,
            "name": name,
            "eep": eep,
            "manufacturer": manufacturer,
            "enabled": True,
            "last_seen": datetime.now().isoformat(),
            "provisioning_options": provisioning_data # Save options
        }
        self.save_devices()
        return True

    def update_device(self, device_id, data):
        if device_id not in self.devices: return False
        device = self.devices[device_id]
        
        for key in ['name', 'eep', 'manufacturer', 'enabled', 'rorg']:
            if key in data: device[key] = data[key]
            
        self.save_devices()
        return True

    def remove_device(self, device_id):
        if device_id in self.devices:
            del self.devices[device_id]
            self.save_devices()
            return True
        return False
        
    def update_last_seen(self, device_id, rssi):
        if device_id in self.devices:
            self.devices[device_id]['rssi'] = rssi
            self.devices[device_id]['last_seen'] = datetime.now().isoformat()
            # No save to disk for perf

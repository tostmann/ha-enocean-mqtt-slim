import os
import json
import logging
from glob import glob

logger = logging.getLogger(__name__)

class EEPProfile:
    """Wrapper class for profile data"""
    def __init__(self, data):
        self.data = data
        self.eep = data.get('eep')
        self.title = data.get('type_title', 'Unknown')
        self.rorg = data.get('rorg_number')

    def get_entities(self):
        """Extracts HA entities definition from profile"""
        entities = []
        objects = self.data.get('objects', {})
        
        for key, config in objects.items():
            entity = config.copy()
            entity['key'] = key
            # Default Component fallback
            if 'component' not in entity:
                entity['component'] = 'sensor'
            entities.append(entity)
        return entities

class EEPLoader:
    def __init__(self, base_path):
        self.base_path = base_path
        self.profiles = {}
        self.load_profiles() # Initial load

    def load_profiles(self):
        """Loads or reloads all JSON profiles from disk"""
        self.profiles = {}
        # Wir suchen rekursiv nach JSON Dateien
        pattern = os.path.join(self.base_path, '**', '*.json')
        files = glob(pattern, recursive=True)
        
        count = 0
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'eep' in data:
                        # Profile speichern
                        # Falls mehrere Dateien das gleiche EEP haben, gewinnt das letzte (Custom überschreibt Built-in)
                        self.profiles[data['eep']] = EEPProfile(data)
                        count += 1
            except Exception as e:
                logger.error(f"Error loading EEP from {file_path}: {e}")
        
        logger.info(f"Loaded {count} EEP profiles from {self.base_path}")

    def get_profile(self, eep_name):
        return self.profiles.get(eep_name)

    def list_profiles(self):
        """Returns list of dicts for UI"""
        result = []
        for p in self.profiles.values():
            result.append({
                'eep': p.eep,
                'title': p.title,
                'rorg': p.rorg
            })
        return result

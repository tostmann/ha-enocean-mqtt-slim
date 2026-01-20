#!/usr/bin/env python3
"""
Smart EEP Downloader & Converter v8 (Cover & Climate Support)
- Lädt EEPs von ioBroker
- Löst 'preDefined' Kürzel auf
- Erkennt Dimmer (light) und Relais (switch)
- Erkennt Rollläden (cover) bei D2-05
- Macht Sollwerte (Setpoints) und Ventile steuerbar (number)
- Markiert RSSI, Last Seen, Error als 'diagnostic'
- Erkennt Batterien korrekt (device_class: battery)
"""
import json
import os
import re
import urllib.request
import zipfile
from pathlib import Path

# ==============================================================================
# KONFIGURATION
# ==============================================================================
GITHUB_URL = "https://github.com/Jey-Cee/ioBroker.enocean/archive/refs/heads/master.zip"
ZIP_INTERNAL_PATH = "ioBroker.enocean-master/lib/definitions/eep"
DEST_DIR = Path("addon/rootfs/app/eep/definitions")

# ==============================================================================
# DEFINITIONEN & MAPPINGS
# ==============================================================================

def sensor_conf(dev_class, unit, icon=None, state_class="measurement", category=None):
    c = {
        "component": "sensor",
        "device_class": dev_class,
        "state_class": state_class,
        "unit": unit
    }
    if icon: c["icon"] = icon
    if category: c["entity_category"] = category
    return c

PREDEFINED_MAPPING = {
    "TMP": sensor_conf("temperature", "°C", "mdi:thermometer"),
    "HUM": sensor_conf("humidity", "%", "mdi:water-percent"),
    "ILLU": sensor_conf("illuminance", "lx", "mdi:brightness-6"),
    "WND": sensor_conf("wind_speed", "m/s", "mdi:weather-windy"),
    "SUN": sensor_conf("irradiance", "W/m²", "mdi:solar-power"),
    "CO2": sensor_conf("carbon_dioxide", "ppm", "mdi:molecule-co2"),
    
    # Binäre Typen
    "PIR": {"component": "binary_sensor", "device_class": "motion", "icon": "mdi:motion-sensor"},
    "BTN": {"component": "binary_sensor", "icon": "mdi:gesture-tap-button"}
}

# Regex für automatische Erkennung
SEMANTIC_MAPPING = [
    # WICHTIG: Batterien & Config zuerst
    (r'(?i)^(bat|battery|charge|storage|level)', sensor_conf("battery", "%", "mdi:battery", category="diagnostic")),
    (r'(?i)^(interv|cycle|wake|period)', {"component": "number", "entity_category": "config", "icon": "mdi:timer-cog"}),
    
    # Climate Controls (Sollwerte steuerbar machen)
    (r'(?i)^(setpoint|sollwert|target)', {"component": "number", "device_class": "temperature", "unit": "°C", "icon": "mdi:thermostat"}),
    (r'(?i)^(valve|ventil|pos)', {"component": "number", "icon": "mdi:pipe-valve", "unit": "%"}), # Ventilöffnung 0-100%
    (r'(?i)^(fan|speed|stufe|geblaese)', {"component": "number", "icon": "mdi:fan"}),

    # Sensoren
    (r'(?i)^(tmp|temp|temperature)', sensor_conf("temperature", "°C", "mdi:thermometer")),
    (r'(?i)^(hum|humidity)', sensor_conf("humidity", "%", "mdi:water-percent")),
    (r'(?i)^(illu|illumination|brightness)', sensor_conf("illuminance", "lx", "mdi:brightness-6")),
    (r'(?i)^(volt|voltage)', sensor_conf("voltage", "V", "mdi:lightning-bolt")),
    (r'(?i)^(curr|current)', sensor_conf("current", "A", "mdi:current-ac")),
    (r'(?i)^(pwr|power)', sensor_conf("power", "W", "mdi:flash")),
    (r'(?i)^(energy)', {"component": "sensor", "device_class": "energy", "state_class": "total_increasing", "unit": "kWh", "icon": "mdi:counter"}),
    (r'(?i)^(co2|carbon)', sensor_conf("carbon_dioxide", "ppm", "mdi:molecule-co2")),
    
    # Diagnose
    (r'(?i)^(rssi|signal)', sensor_conf("signal_strength", "dBm", "mdi:wifi", category="diagnostic")),
    (r'(?i)^(err|error|fail|failure|alarm|warn)', {"component": "binary_sensor", "device_class": "problem", "entity_category": "diagnostic"}),

    # Binäre Typen
    (r'(?i)^(contact|window|door|closed|open)', {"component": "binary_sensor", "device_class": "window", "icon": "mdi:window-closed"}),
    (r'(?i)^(motion|pir|occ|occupancy)', {"component": "binary_sensor", "device_class": "motion", "icon": "mdi:motion-sensor"}),
    (r'(?i)^(btn|button|sw|switch)', {"component": "binary_sensor", "icon": "mdi:gesture-tap-button"}),
]

def apply_family_rules(eep_code, obj_key, obj_data):
    eep = eep_code.upper()
    name_lower = obj_key.lower()

    if obj_data.get("unit") and obj_data.get("component") != "number": 
        return # Analoge Sensoren behalten (außer wir haben sie oben schon als 'number' erkannt)

    # Rollläden / Jalousien (Cover)
    if eep.startswith("D2-05"):
        # Position oder Angle -> Cover
        if any(x in name_lower for x in ['pos', 'angle', 'level']):
            obj_data["component"] = "cover"
            obj_data["device_class"] = "shutter" # oder 'blind'
            return

    # Taster
    if eep.startswith("F6-02") or eep.startswith("F6-01"):
        obj_data["component"] = "binary_sensor"
        obj_data["icon"] = "mdi:light-switch"
        return
    
    # Fensterkontakte
    if eep.startswith("D5-00"):
        obj_data["component"] = "binary_sensor"
        if "contact" in name_lower: obj_data["device_class"] = "window"
        return
    
    # Fenstergriffe
    if eep.startswith("F6-10") and "handle" in name_lower:
        obj_data["component"] = "sensor"
        obj_data["icon"] = "mdi:window-open-variant"
        return
    
    # Aktoren (Light vs Switch)
    if eep.startswith("D2-01") or eep.startswith("A5-38"):
        if any(x in name_lower for x in ['channel', 'output', 'switch', 'relay']) and not obj_data.get("unit"):
             obj_data["component"] = "switch"
             obj_data["device_class"] = "outlet"
        elif "dim" in name_lower:
            obj_data["component"] = "light"
            obj_data["icon"] = "mdi:lightbulb"

    # Thermostate / Raumcontroller (A5-10, A5-20)
    # Hier stellen wir sicher, dass Sollwerte 'number' sind
    if eep.startswith("A5-10") or eep.startswith("A5-20"):
        if any(x in name_lower for x in ['setpoint', 'sollwert']):
            obj_data["component"] = "number"
            obj_data["device_class"] = "temperature"
            obj_data["icon"] = "mdi:thermostat"

# ==============================================================================
# LOGIK (Werte Korrektur)
# ==============================================================================

def enforce_binary_values(profile_data):
    """Zwingt binary_sensor, switch und light dazu, "ON"/"OFF" zurückzugeben."""
    target_shortcuts = []
    
    if "objects" in profile_data:
        for key, obj in profile_data["objects"].items():
            # Units (außer %) ignorieren wir meist, aber sicherheitshalber:
            # Wenn es eine Number ist (Setpoint), darf es NICHT binary sein.
            if obj.get("component") == "number": continue
            
            # Nur binäre Komponenten anfassen
            if obj.get("component") in ["binary_sensor", "switch", "light"]:
                # Ausnahme: Dimmer (light) mit Unit % ist analog!
                if obj.get("component") == "light" and obj.get("unit") == "%":
                    continue
                target_shortcuts.append(key)
    
    if not target_shortcuts or "case" not in profile_data:
        return profile_data

    for case in profile_data["case"]:
        if "datafield" in case:
            for field in case["datafield"]:
                if field.get("shortcut") in target_shortcuts and "value" in field:
                    original_logic = field["value"]
                    is_already_wrapped = False
                    if isinstance(original_logic, dict) and "if" in original_logic:
                        args = original_logic["if"]
                        if len(args) == 3 and args[1] == "ON" and args[2] == "OFF":
                            is_already_wrapped = True
                    
                    if not is_already_wrapped:
                        field["value"] = {"if": [original_logic, "ON", "OFF"]}
    return profile_data

def enhance_profile(profile_data):
    eep_code = profile_data.get("eep", "UNKNOWN")
    if "objects" not in profile_data: profile_data["objects"] = {}

    if "preDefined" in profile_data["objects"]:
        pre_def_list = profile_data["objects"]["preDefined"]
        if isinstance(pre_def_list, list):
            for item in pre_def_list:
                if item in PREDEFINED_MAPPING:
                    new_obj = PREDEFINED_MAPPING[item].copy()
                    new_obj["shortcut"] = item
                    if item not in profile_data["objects"]:
                        profile_data["objects"][item] = new_obj
        del profile_data["objects"]["preDefined"]

    # Diagnostics
    profile_data["objects"]["rssi"] = {
        "name": "RSSI", "component": "sensor", "device_class": "signal_strength", 
        "state_class": "measurement", "entity_category": "diagnostic",
        "unit": "dBm", "icon": "mdi:wifi", "description": "Signal strength"
    }
    profile_data["objects"]["last_seen"] = {
        "name": "Last Seen", "component": "sensor", "device_class": "timestamp", 
        "entity_category": "diagnostic",
        "icon": "mdi:clock-outline", "description": "Last telegram received"
    }

    for obj_key in list(profile_data["objects"].keys()):
        obj_data = profile_data["objects"][obj_key]
        if not isinstance(obj_data, dict): continue
        if obj_key in ["rssi", "last_seen"]: continue
        
        # 1. Regex Mapping (hier werden auch Setpoints zu 'number')
        for pattern, attributes in SEMANTIC_MAPPING:
            if re.search(pattern, obj_key):
                for k, v in attributes.items():
                    if k not in obj_data: obj_data[k] = v
                break
        
        # 2. Familien Regeln (hier werden Blinds zu 'cover')
        apply_family_rules(eep_code, obj_key, obj_data)
        
        # 3. Fallback
        if "component" not in obj_data:
            obj_data["component"] = "sensor"
            if obj_data.get("unit") == "%": obj_data["icon"] = "mdi:percent"

    profile_data = enforce_binary_values(profile_data)
    return profile_data

def download_and_process():
    print(f"ℹ️  Nutze relatives Zielverzeichnis: {DEST_DIR}")
    print(f"⬇️  Lade Repository von GitHub...\n    {GITHUB_URL}")
    try:
        zip_path, _ = urllib.request.urlretrieve(GITHUB_URL)
        print("📦 Extrahiere und verarbeite Dateien...")
        count = 0
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.filename.startswith(ZIP_INTERNAL_PATH) and file_info.filename.endswith(".json"):
                    with zip_ref.open(file_info) as f:
                        try: data = json.load(f)
                        except json.JSONDecodeError: continue
                    try: enhanced_data = enhance_profile(data)
                    except Exception as e:
                        print(f"⚠️  Fehler bei {file_info.filename}: {e}"); continue
                    
                    rel_path = file_info.filename.replace(ZIP_INTERNAL_PATH + "/", "")
                    target_file = DEST_DIR / rel_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(target_file, 'w', encoding='utf-8') as f:
                        json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
                    count += 1
                    if count % 10 == 0: print(f"   ... {count} Dateien verarbeitet", end="\r")
        os.remove(zip_path)
        print(f"\n🎉 Fertig! {count} Profile konvertiert (v8: Cover, Climate Controls, Fixes).")
    except Exception as e: print(f"\n❌ FEHLER: {e}")

if __name__ == "__main__":
    download_and_process()

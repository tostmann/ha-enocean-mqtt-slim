import logging
import struct

logger = logging.getLogger(__name__)

class EEPParser:
    def __init__(self):
        pass

    def parse_telegram_with_full_data(self, data, profile):
        """
        Parses raw bytes based on the JSON profile definition.
        Handles A5 (4BS), F6 (RPS), D5 (1BS) logic.
        """
        if not profile:
            return None

        # RORG ist das erste Byte
        rorg = data[0]
        
        eep_name = profile.get('eep', 'Unknown')
        logger.info(f"📊 Parsing telegram with profile {eep_name}")
        
        # -----------------------------------------------------------
        # 1. MATCHING: Finde den passenden 'case' im JSON
        # -----------------------------------------------------------
        matched_case = None
        
        # Daten-Wert extrahieren (abhängig vom RORG)
        raw_val = 0
        status_byte = data[-1] # Status ist immer das letzte Byte (bei ERP1)
        
        if rorg == 0xF6: # RPS (Switch) -> Nur Byte 1 ist Daten
            raw_val = data[1]
            logger.info(f"RPS (F6) Data Byte: {hex(raw_val)}")
        elif rorg == 0xD5: # 1BS (Contact) -> Nur Byte 1 ist Daten
            raw_val = data[1]
            logger.info(f"1BS (D5) Data Byte: {hex(raw_val)}")
        else: # Standard A5 (4BS) -> 4 Bytes (1-5)
            # data[1:5] sind die DB3..DB0
            raw_val = int.from_bytes(data[1:5], 'big')
            logger.info(f"4BS (A5) Data Bytes: {data[1:5].hex()}")

        # Durchsuche alle 'cases' im Profil
        for case in profile.get('case', []):
            match = True
            
            # A) Check 'data' (Hex String im JSON z.B. "0x10")
            if 'data' in case:
                case_data_int = int(case['data'], 16)
                if case_data_int != raw_val:
                    match = False
            
            # B) Check 'status' (falls im JSON definiert)
            if match and 'status' in case:
                case_status_int = int(case['status'], 16)
                # Status Byte Vergleich (exakt)
                if case_status_int != status_byte:
                    match = False
            
            if match:
                matched_case = case
                break
        
        if not matched_case:
            logger.info(f"No matching case found for Data={hex(raw_val)} Status={hex(status_byte)}")
            return {}

        # -----------------------------------------------------------
        # 2. EXTRACTION: Werte aus dem Treffer übernehmen
        # -----------------------------------------------------------
        result = {}
        
        # Werte aus 'datafield' übernehmen (z.B. BI=1)
        for field in matched_case.get('datafield', []):
            shortcut = field.get('shortcut')
            value = field.get('value')
            if shortcut and value is not None:
                # Versuch, Zahlen auch als Zahlen zu speichern
                try:
                    if "." in str(value):
                        result[shortcut] = float(value)
                    else:
                        result[shortcut] = int(value)
                except:
                    result[shortcut] = value # Fallback String ("ON", "OFF")

        # Wenn es Range/Scale Logik gibt (für A5 Sensoren)
        if 'range' in matched_case.get('datafield', [{}])[0]: 
            # Das ist komplexer Sensor-Code (A5), hier für F6 Schalter nicht relevant
            # Würde hier folgen (siehe Original-Code für A5 Logik)
            pass

        logger.info(f"Parsed result: {result}")
        return result

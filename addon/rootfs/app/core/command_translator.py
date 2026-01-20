"""
Command Translator
Translates MQTT commands to EnOcean telegrams based on EEP profiles
"""
import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class CommandTranslator:
    """Translate MQTT commands to EnOcean telegrams"""
    
    def __init__(self, eep_loader):
        """
        Initialize command translator
        Args:
            eep_loader: EEP profile loader instance
        """
        self.eep_loader = eep_loader
    
    def translate_switch_command(self, device: Dict[str, Any], state: str) -> Optional[Tuple[int, bytes]]:
        """Translate switch ON/OFF command"""
        eep = device.get('eep', '')
        
        # A5-38-08: Central Command (Gateway)
        if eep == 'A5-38-08':
            if state.upper() == 'ON':
                return (0xA5, bytes([0x02, 0x00, 0x64, 0x09]))
            else:
                return (0xA5, bytes([0x02, 0x00, 0x00, 0x08]))
        
        # D2-01-xx: Electronic switches
        elif eep.startswith('D2-01'):
            if state.upper() == 'ON':
                return (0xD2, bytes([0x01, 0x01, 0x64, 0x00])) # CMD 1, Ch 1, 100%
            else:
                return (0xD2, bytes([0x01, 0x01, 0x00, 0x00])) # CMD 1, Ch 1, 0%
        
        # Eltako Actuators (F6-02-01 special handling via RPS)
        elif eep == 'F6-02-01-actuator':
            return None # Handled via RPS fallback in translate_command
            
        logger.warning(f"Switch command not supported for EEP {eep}")
        return None
    
    def translate_dim_command(self, device: Dict[str, Any], brightness: int) -> Optional[Tuple[int, bytes]]:
        """Translate dimming command (0-255)"""
        eep = device.get('eep', '')
        
        # A5-38-08: Central Command
        if eep == 'A5-38-08':
            dim_value = int((brightness / 255.0) * 100)
            return (0xA5, bytes([0x02, 0x00, dim_value, 0x09]))
            
        # D2-01-xx: Dimmer
        elif eep.startswith('D2-01'):
            dim_value = int((brightness / 255.0) * 100)
            return (0xD2, bytes([0x01, 0x01, dim_value, 0x00]))

        logger.warning(f"Dim command not supported for EEP {eep}")
        return None
    
    def translate_cover_command(self, device: Dict[str, Any], position: int = None, cmd: str = None) -> Optional[Tuple[int, bytes]]:
        """
        Translate cover command (position 0-100 or open/close/stop)
        Note: HA uses 100=Open, 0=Closed. EnOcean usually 0=Open/Top, 100=Closed/Bottom.
        We invert the value here to match standard EnOcean actuators (like NodOn/Eltako).
        """
        eep = device.get('eep', '')
        
        # D2-05-xx: Blinds/Shutters
        if eep.startswith('D2-05'):
            # VLD Telegram D2-05-00
            # CMD 1: GoTo Position (Byte 0=0x01)
            # CMD 0: Stop (Byte 0=0x00)
            
            if cmd == "stop":
                # Stop command
                return (0xD2, bytes([0x00, 0x00, 0x00, 0x00]))
            
            # Position calculation
            target_pos = 0
            if position is not None:
                # Invert HA (100=Open) to EnOcean (0=Open)
                target_pos = 100 - position
            elif cmd == "open":
                target_pos = 0   # EnOcean 0% = Open
            elif cmd == "close":
                target_pos = 100 # EnOcean 100% = Closed
                
            # CMD 1: GoTo Position | Pos | Angle | Flags
            return (0xD2, bytes([0x01, target_pos, 0x00, 0x00]))
        
        logger.warning(f"Cover command not supported for EEP {eep}")
        return None

    def translate_number_command(self, device: Dict[str, Any], value: float) -> Optional[Tuple[int, bytes]]:
        """Translate numeric value command (e.g. Valve Position or Setpoint)"""
        eep = device.get('eep', '')
        
        # A5-20-xx: HVAC Components (Battery Valves)
        if eep.startswith('A5-20'):
            # 4BS Telegram: Set Valve Position
            # DB3: Valve Pos 0-100%
            # DB0: 0x08 (Data Telegram, not Teach-in)
            # DB1 Bit 2 is usually 0 for "Valve Position" (1 for Setpoint Temp)
            
            val_int = int(max(0, min(100, value))) # Clamp 0-100
            
            # Telegram: [DB3, DB2, DB1, DB0]
            # DB3=Value, DB0=0x08
            return (0xA5, bytes([val_int, 0x00, 0x00, 0x08]))

        # A5-10-xx: Room Operating Panel (Simulate Setpoint)
        elif eep.startswith('A5-10'):
            # This depends heavily on the specific device/receiver logic.
            # Assuming linear mapping 0-255 for now or 0-40C mapped to 0-255
            # Simplified: Just send raw value in DB1 or DB2? 
            # Without specific target logic, A5-10 sending is tricky.
            # But for A5-20 (Valves), the above logic is standard.
            pass

        logger.warning(f"Number command not supported for EEP {eep}")
        return None

    def translate_rps_button(self, button: str) -> Optional[int]:
        """Translate button name to RPS button code"""
        button_map = {
            'A0': 0x10, 'AI': 0x10,
            'A1': 0x30, 'AO': 0x30,
            'B0': 0x50, 'BI': 0x50,
            'B1': 0x70, 'BO': 0x70,
        }
        return button_map.get(button.upper())
    
    def translate_command(self, device: Dict[str, Any], entity: str, command: Dict[str, Any]) -> Optional[Tuple[str, int, bytes]]:
        """
        Translate generic MQTT command to EnOcean telegram
        Returns: (command_type, rorg, data_bytes)
        """
        eep = device.get('eep', '')
        logger.info(f"Translating {eep} ({entity}): {command}")
        
        # 1. Switch (ON/OFF)
        if 'state' in command and entity in ['switch', 'light']:
            res = self.translate_switch_command(device, command['state'])
            if res: return ('telegram', res[0], res[1])
            
            # Fallback RPS
            if eep.startswith('F6-02'):
                code = 0x10 if command['state'].upper() == 'ON' else 0x30
                return ('rps', code, bytes())

        # 2. Dimmer (Brightness)
        if 'brightness' in command:
            res = self.translate_dim_command(device, command['brightness'])
            if res: return ('telegram', res[0], res[1])

        # 3. Cover (Position/Open/Close/Stop)
        if entity == 'cover':
            cmd_type = command.get('command') # open, close, stop
            pos = command.get('position')     # 0-100
            res = self.translate_cover_command(device, position=pos, cmd=cmd_type)
            if res: return ('telegram', res[0], res[1])

        # 4. Number / Climate (Value)
        if 'value' in command:
            res = self.translate_number_command(device, float(command['value']))
            if res: return ('telegram', res[0], res[1])

        # 5. Buttons
        if 'button' in command:
            code = self.translate_rps_button(command['button'])
            if code: return ('rps', code, bytes())
        
        return None
    
    def get_supported_commands(self, eep: str) -> Dict[str, list]:
        """Get list of supported commands for an EEP"""
        commands = {}
        
        if eep == 'A5-38-08':
            commands['switch'] = ['state']
            commands['light'] = ['state', 'brightness']
        elif eep.startswith('F6-02'):
            commands['button'] = ['button']
            commands['switch'] = ['state'] # Virtual
        elif eep.startswith('D2-01'):
            commands['switch'] = ['state']
            commands['light'] = ['state', 'brightness']
        elif eep.startswith('D2-05'):
            commands['cover'] = ['position', 'open', 'close', 'stop']
        elif eep.startswith('A5-20'):
            commands['number'] = ['value'] # Valve position
            
        return commands
    
    def is_controllable(self, eep: str) -> bool:
        """Check if profile supports sending"""
        controllable = ['A5-38', 'D2-01', 'D2-05', 'F6-02', 'A5-20']
        return any(eep.startswith(p) for p in controllable)

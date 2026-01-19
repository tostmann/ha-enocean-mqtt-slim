"""
Connection Handler for EnOcean Gateway
Refactored: Separates Transport Layer (TCP/Serial) from Protocol Layer (ESP3)
Includes Retry-Logic for Base ID fetching.
"""
import asyncio
import logging
import serial
import socket
import time
import urllib.parse
from abc import ABC, abstractmethod
from typing import Optional, Callable, Union
from .esp3_protocol import ESP3Packet

logger = logging.getLogger(__name__)


# ==============================================================================
# TRANSPORT LAYER (Abstract & Implementations)
# ==============================================================================

class BaseTransport(ABC):
    """Abstract Base Class for Connection Transports"""
    
    def __init__(self):
        self.connected = False
        self.connection_info = "Unknown"

    @abstractmethod
    def open(self) -> bool:
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def read(self, count: int) -> bytes:
        pass

    @abstractmethod
    def write(self, data: bytes) -> bool:
        pass
        
    @abstractmethod
    def flush_input(self):
        pass
    
    def is_open(self) -> bool:
        return self.connected


class SerialTransport(BaseTransport):
    """Transport implementation for Physical Serial Ports"""
    
    def __init__(self, port: str, baudrate: int = 57600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        self.connection_info = f"Serial({port}@{baudrate})"

    def open(self) -> bool:
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.5
            )
            self.connected = True
            logger.info(f"Opened serial port {self.port}")
            self.flush_input()
            return True
        except Exception as e:
            logger.error(f"Failed to open serial port {self.port}: {e}")
            self.connected = False
            return False

    def close(self):
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
            except Exception:
                pass
        self.serial = None
        self.connected = False
        logger.info(f"Closed serial port {self.port}")

    def read(self, count: int) -> bytes:
        if not self.serial or not self.serial.is_open:
            return b''
        try:
            return self.serial.read(count)
        except Exception as e:
            logger.error(f"Serial read error: {e}")
            self.close()
            return b''

    def write(self, data: bytes) -> bool:
        if not self.serial or not self.serial.is_open:
            return False
        try:
            self.serial.write(data)
            return True
        except Exception as e:
            logger.error(f"Serial write error: {e}")
            self.close()
            return False

    def flush_input(self):
        if self.serial and self.serial.is_open:
            self.serial.reset_input_buffer()


class TcpTransport(BaseTransport):
    """Transport implementation for TCP Sockets"""
    
    def __init__(self, host: str, port: int):
        super().__init__()
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connection_info = f"TCP({host}:{port})"

    def open(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            try:
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
            except (AttributeError, OSError):
                pass 

            self.socket.settimeout(5.0) 
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(0.5)
            
            self.connected = True
            logger.info(f"Connected to TCP {self.host}:{self.port}")
            self.flush_input()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.host}:{self.port}: {e}")
            self.connected = False
            return False

    def close(self):
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
        self.socket = None
        self.connected = False
        logger.info(f"Closed TCP connection {self.host}:{self.port}")

    def read(self, count: int) -> bytes:
        if not self.socket: return b''
        data = b''
        try:
            while len(data) < count:
                chunk = self.socket.recv(count - len(data))
                if not chunk: 
                    logger.warning("TCP connection closed by remote host (EOF)")
                    self.close()
                    break
                data += chunk
            return data
        except socket.timeout:
            return data 
        except Exception as e:
            logger.error(f"Socket read error: {e}")
            self.close()
            return b''

    def write(self, data: bytes) -> bool:
        if not self.socket: return False
        try:
            self.socket.sendall(data)
            return True
        except Exception as e:
            logger.error(f"Socket write error: {e}")
            self.close()
            return False

    def flush_input(self):
        if not self.socket: return
        self.socket.setblocking(0)
        try:
            while True:
                data = self.socket.recv(4096)
                if not data: break
        except (BlockingIOError, Exception):
            pass
        finally:
            self.socket.setblocking(1)
            self.socket.settimeout(0.5)


# ==============================================================================
# LOGIC LAYER (Protocol Handling)
# ==============================================================================

class SerialHandler:
    """
    Handle communication with EnOcean gateway.
    Uses a Transport instance to be agnostic of Serial vs TCP.
    """
    
    def __init__(self, connection_string: str, baudrate: int = 57600):
        self.connection_string = connection_string
        self.baudrate = baudrate
        self.running = False
        self.base_id = None
        self.version_info = None
        self.last_data_received = 0.0
        self._last_info_fetch_attempt = 0.0
        
        if connection_string.lower().startswith('tcp://'):
            parsed = urllib.parse.urlparse(connection_string)
            if not parsed.port:
                raise ValueError("Port missing in TCP connection string")
            self.transport = TcpTransport(parsed.hostname, parsed.port)
        else:
            self.transport = SerialTransport(connection_string, baudrate)
        
    def open(self) -> bool:
        success = self.transport.open()
        if success:
            self.last_data_received = time.time()
        return success
    
    def close(self):
        self.transport.close()
    
    def is_open(self) -> bool:
        return self.transport.is_open()

    async def read_packet(self) -> Optional[ESP3Packet]:
        if not self.is_open():
            return None
        
        try:
            byte = await asyncio.get_event_loop().run_in_executor(
                None, self.transport.read, 1
            )
            
            if not byte: return None 
            
            self.last_data_received = time.time()
            
            if byte[0] != ESP3Packet.SYNC_BYTE:
                return None
            
            logger.debug("Found sync byte 0x55, reading header...")

            header = await asyncio.get_event_loop().run_in_executor(
                None, self.transport.read, 4
            )
            if len(header) != 4:
                logger.warning("Incomplete header received")
                return None
            
            data_length = int.from_bytes(header[0:2], 'big')
            optional_length = header[2]
            
            header_crc = await asyncio.get_event_loop().run_in_executor(
                None, self.transport.read, 1
            )
            if len(header_crc) != 1:
                logger.warning("Missing header CRC")
                return None
            
            total_data_length = data_length + optional_length + 1
            data_block = await asyncio.get_event_loop().run_in_executor(
                None, self.transport.read, total_data_length
            )
            if len(data_block) != total_data_length:
                logger.warning(f"Incomplete data block: {len(data_block)}/{total_data_length}")
                return None
            
            raw_packet = bytes([ESP3Packet.SYNC_BYTE]) + header + header_crc + data_block
            packet = ESP3Packet(raw_packet)
            logger.debug(f"Received packet: {packet}")
            return packet
            
        except Exception as e:
            logger.error(f"Error reading packet: {e}")
            if isinstance(self.transport, TcpTransport):
                self.close()
            return None
    
    async def write_packet(self, packet: ESP3Packet) -> bool:
        if not self.is_open():
            return False
        try:
            raw_data = packet.build()
            success = await asyncio.get_event_loop().run_in_executor(
                None, self.transport.write, raw_data
            )
            if success:
                logger.debug(f"Sent packet: {packet}")
            return success
        except Exception as e:
            logger.error(f"Error writing packet: {e}")
            return False

    async def send_ping(self) -> bool:
        logger.info("⏳ Connection idle > 30s. Sending KeepAlive Ping...")
        try:
            ping_packet = ESP3Packet.create_read_version()
            return await self.write_packet(ping_packet)
        except Exception as e:
            logger.error(f"Failed to send Ping: {e}")
            return False

    async def send_command_and_wait_response(self, command_packet: ESP3Packet, timeout: float = 2.0) -> Optional[ESP3Packet]:
        if not await self.write_packet(command_packet):
            return None
        
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            packet = await self.read_packet()
            if packet and packet.packet_type == ESP3Packet.PACKET_TYPE_RESPONSE:
                return packet
            await asyncio.sleep(0.01)
        return None

    async def get_base_id(self) -> Optional[str]:
        if self.base_id: return self.base_id
        command = ESP3Packet.create_read_base_id()
        response = await self.send_command_and_wait_response(command)
        if response and len(response.data) >= 5 and response.data[0] == 0:
            self.base_id = response.data[1:5].hex()
            logger.info(f"Gateway Base ID: {self.base_id}")
            return self.base_id
        return None
    
    async def get_version_info(self) -> Optional[dict]:
        if self.version_info: return self.version_info
        command = ESP3Packet.create_read_version()
        response = await self.send_command_and_wait_response(command)
        if response and len(response.data) >= 33 and response.data[0] == 0:
            self.version_info = {
                'app_version': '.'.join(str(b) for b in response.data[1:5]),
                'chip_id': response.data[9:13].hex(),
                'app_description': response.data[17:33].decode('ascii', errors='ignore').strip('\x00')
            }
            logger.info(f"Gateway Version: {self.version_info}")
            return self.version_info
        return None

    async def start_reading(self, callback: Callable[[ESP3Packet], None]):
        """Start reading loop with Reconnect, KeepAlive and Info-Retry logic"""
        self.running = True
        logger.info(f"Started reading loop for {self.transport.connection_info}")
        logger.info("=" * 80)
        logger.info("🎧 LISTENING FOR ENOCEAN TELEGRAMS (KeepAlive Enabled)")
        logger.info("=" * 80)
        
        PING_INTERVAL = 30.0
        PING_TIMEOUT = 10.0
        
        self.last_data_received = time.time()
        
        while self.running:
            try:
                # 1. Auto-Reconnect
                if not self.is_open():
                    logger.warning(f"Connection lost. Reconnecting to {self.transport.connection_info} in 5s...")
                    await asyncio.sleep(5)
                    if self.open():
                        logger.info("Connection re-established")
                        self.last_data_received = time.time()
                    continue

                # 2. RETRY INFO FETCH (Fix for "Status Connected but No ID")
                # If connected but missing info, try fetching every 10s
                if self.is_open() and (not self.base_id or not self.version_info):
                    if time.time() - self._last_info_fetch_attempt > 10.0:
                        self._last_info_fetch_attempt = time.time()
                        if not self.base_id: 
                            logger.info("Retrying fetch Base ID...")
                            await self.get_base_id()
                        if not self.version_info: 
                            await self.get_version_info()

                # 3. Read Packet
                packet = await self.read_packet()
                
                if packet:
                    if packet.packet_type == ESP3Packet.PACKET_TYPE_RADIO_ERP1:
                        await callback(packet)
                    elif packet.packet_type == ESP3Packet.PACKET_TYPE_RESPONSE:
                        logger.debug("Received Ping/Response")
                    continue 
                
                # 4. Idle / KeepAlive Logic
                now = time.time()
                time_since_data = now - self.last_data_received
                
                if time_since_data > (PING_INTERVAL + PING_TIMEOUT):
                     logger.warning(f"❌ Connection dead! No data for {time_since_data:.1f}s. Closing...")
                     self.close()
                     continue

                if time_since_data > PING_INTERVAL:
                    if int(time_since_data) % 5 == 0: 
                        if not await self.send_ping():
                            logger.warning("Failed to send Ping. Closing connection.")
                            self.close()
                
            except Exception as e:
                logger.error(f"Error in read loop: {e}")
                await asyncio.sleep(1)
    
    def stop_reading(self):
        self.running = False

    async def send_telegram(self, destination_id: str, rorg: int, data_bytes: bytes, status: int = 0x00) -> bool:
        if not self.base_id: await self.get_base_id()
        packet = ESP3Packet.create_radio_packet(self.base_id, destination_id, rorg, data_bytes, status)
        logger.info(f"📤 Sending telegram to {destination_id}: RORG={hex(rorg)}")
        return await self.write_packet(packet)
    
    async def send_rps_command(self, destination_id: str, button_code: int, press_duration: float = 0.1) -> bool:
        if not self.base_id: await self.get_base_id()
        logger.info(f"📤 Sending RPS command to {destination_id}: button={hex(button_code)}")
        packet_press = ESP3Packet.create_rps_packet(self.base_id, destination_id, button_code, pressed=True)
        if await self.write_packet(packet_press):
            await asyncio.sleep(press_duration)
            packet_release = ESP3Packet.create_rps_packet(self.base_id, destination_id, button_code, pressed=False)
            return await self.write_packet(packet_release)
        return False

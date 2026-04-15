"""
Serial Console - Consola serial para captura de bootlog y interacción
"""

import serial
import serial.tools.list_ports
import threading
import time
import queue
from typing import Optional, Callable, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SerialMessage:
    """Mensaje de la consola serial"""
    timestamp: float
    data: bytes
    is_command: bool = False


class SerialConsole:
    """
    Consola serial para comunicación con dispositivos Allwinner.
    Soporta captura de bootlog y envío de comandos interactivos.
    """
    
    DEFAULT_BAUDRATE = 115200
    DEFAULT_TIMEOUT = 0.1
    
    def __init__(self, 
                 port: Optional[str] = None,
                 baudrate: int = DEFAULT_BAUDRATE,
                 on_data: Optional[Callable[[str], None]] = None):
        self.port = port
        self.baudrate = baudrate
        self.on_data = on_data
        self.serial_conn: Optional[serial.Serial] = None
        self.reading = False
        self.read_thread: Optional[threading.Thread] = None
        self.message_queue: queue.Queue = queue.Queue()
        self.buffer = ""
        
    @staticmethod
    def list_ports() -> List[dict]:
        """Lista todos los puertos serial disponibles"""
        ports = []
        for p in serial.tools.list_ports.comports():
            ports.append({
                "device": p.device,
                "name": p.name,
                "description": p.description,
                "hwid": p.hwid,
                "vid": p.vid,
                "pid": p.pid
            })
        return ports
    
    @staticmethod
    def list_usb_serial() -> List[dict]:
        """Lista solo puertos seriales USB"""
        ports = []
        for p in serial.tools.list_ports.comports():
            if "USB" in p.name or "USB" in p.description or "CH340" in p.description:
                ports.append({
                    "device": p.device,
                    "name": p.name,
                    "description": p.description
                })
        return ports
        
    def connect(self, port: Optional[str] = None, 
                baudrate: Optional[int] = None) -> bool:
        """
        Conecta al puerto serial.
        
        Args:
            port: Puerto serie (ej: /dev/ttyUSB0)
            baudrate: Velocidad en baudios
            
        Returns:
            True si la conexión fue exitosa
        """
        if port:
            self.port = port
        if baudrate:
            self.baudrate = baudrate
            
        if not self.port:
            logger.error("No port specified")
            return False
            
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            # Limpiar buffers
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()
            time.sleep(0.5)
            
            logger.info(f"Connected to {self.port} @ {self.baudrate}")
            return True
            
        except serial.SerialException as e:
            logger.error(f"Serial connection error: {e}")
            return False
            
    def disconnect(self):
        """Desconecta del puerto serial"""
        self.stop_reading()
        
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("Serial disconnected")
            
        self.serial_conn = None
        
    def start_reading(self):
        """Inicia lectura en segundo plano"""
        if self.reading:
            return
            
        self.reading = True
        self.read_thread = threading.Thread(
            target=self._read_loop,
            daemon=True
        )
        self.read_thread.start()
        logger.info("Serial reading started")
        
    def stop_reading(self):
        """Detiene lectura en segundo plano"""
        self.reading = False
        if self.read_thread:
            self.read_thread.join(timeout=2)
        logger.info("Serial reading stopped")
        
    def _read_loop(self):
        """Loop de lectura de datos serial"""
        while self.reading:
            try:
                if self.serial_conn and self.serial_conn.in_waiting:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    
                    if data:
                        # Decodificar y notificar
                        text = data.decode('utf-8', errors='replace')
                        
                        if self.on_data:
                            self.on_data(text)
                            
                        # Guardar en queue
                        self.message_queue.put(SerialMessage(
                            timestamp=time.time(),
                            data=data,
                            is_command=False
                        ))
                        
                        # Acumular buffer
                        self.buffer += text
                        
            except Exception as e:
                logger.error(f"Read error: {e}")
                
            time.sleep(0.01)
            
    def send(self, data: str, wait_response: bool = False, 
             timeout: float = 2.0) -> Optional[str]:
        """
        Envía datos por el puerto serial.
        
        Args:
            data: Datos a enviar
            wait_response: Esperar respuesta
            timeout: Tiempo de espera en segundos
            
        Returns:
            Respuesta si wait_response=True
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            logger.error("Not connected")
            return None
            
        try:
            # Enviar datos
            self.serial_conn.write(data.encode('utf-8'))
            logger.debug(f"Sent: {data.strip()}")
            
            # Guardar en queue
            self.message_queue.put(SerialMessage(
                timestamp=time.time(),
                data=data.encode('utf-8'),
                is_command=True
            ))
            
            if wait_response:
                return self._wait_for_response(timeout)
                
            return None
            
        except Exception as e:
            logger.error(f"Send error: {e}")
            return None
            
    def send_command(self, command: str, wait: float = 1.0) -> Optional[str]:
        """Envía un comando y espera respuesta"""
        response = self.send(command + "\r\n", wait_response=True, timeout=wait)
        return response
        
    def _wait_for_response(self, timeout: float) -> Optional[str]:
        """Espera respuesta del dispositivo"""
        start_time = time.time()
        response = ""
        
        while time.time() - start_time < timeout:
            if self.serial_conn and self.serial_conn.in_waiting:
                data = self.serial_conn.read(self.serial_conn.in_waiting)
                response += data.decode('utf-8', errors='replace')
                
                # Detener si hay prompt o nueva línea
                if "> " in response or "\r\n" in response[-10:]:
                    break
                    
            time.sleep(0.05)
            
        return response if response else None
        
    def wait_for_pattern(self, pattern: str, timeout: float = 60.0) -> bool:
        """
        Espera hasta que aparezca un patrón en la salida.
        
        Args:
            pattern: Patrón a buscar
            timeout: Tiempo máximo de espera
            
        Returns:
            True si el patrón fue encontrado
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if pattern in self.buffer:
                return True
            time.sleep(0.1)
            
        return False
        
    def capture_bootlog(self, duration: float = 30.0, 
                        stop_pattern: Optional[str] = None) -> str:
        """
        Captura bootlog durante un tiempo determinado.
        
        Args:
            duration: Duración de la captura en segundos
            stop_pattern: Patrón que detiene la captura
            
        Returns:
            Bootlog capturado
        """
        self.buffer = ""  # Limpiar buffer
        start_time = time.time()
        
        self.start_reading()
        
        while time.time() - start_time < duration:
            if stop_pattern and stop_pattern in self.buffer:
                break
            time.sleep(0.1)
            
        self.stop_reading()
        
        return self.buffer
        
    def interrupt_boot(self) -> bool:
        """
        Intenta interrumpir el autoboot enviando caracteres.
        
        Returns:
            True si se detuvo el boot
        """
        # Enviar caracteres para interrumpir
        for _ in range(10):
            self.send("\r\n")
            time.sleep(0.3)
            
            if self.wait_for_pattern("=>", timeout=1):
                logger.info("Boot interrupted successfully")
                return True
                
        return False
        
    def get_messages(self, clear: bool = True) -> List[SerialMessage]:
        """Obtiene todos los mensajes de la cola"""
        messages = []
        
        while not self.message_queue.empty():
            try:
                messages.append(self.message_queue.get_nowait())
            except queue.Empty:
                break
                
        return messages
        
    @property
    def is_connected(self) -> bool:
        """Verifica si está conectado"""
        return self.serial_conn is not None and self.serial_conn.is_open
        
    def clear_buffer(self):
        """Limpia el buffer de entrada"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.reset_input_buffer()
        self.buffer = ""

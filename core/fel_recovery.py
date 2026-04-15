"""
FEL Recovery Module - Recuperación via modo FEL

Este módulo automatiza el proceso de recuperación mediante FEL mode.
FEL permite escribir a RAM pero NO directamente a eMMC.
La solución es cargar un bootloader con driver eMMC a RAM y ejecutarlo.
"""

import os
import subprocess
import time
import struct
from typing import Optional, Callable, Tuple, Dict, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FELState(Enum):
    """Estados de conexión FEL"""
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    UNSTABLE = "unstable"
    ERROR = "error"


@dataclass
class FELDeviceInfo:
    """Información del dispositivo FEL"""
    soc_id: str = ""
    soc_type: str = ""
    fel_version: str = ""
    dram_base: int = 0x40000000
    dram_size: int = 0
    boot0_base: int = 0
    uboot_base: int = 0
    state: FELState = FELState.DISCONNECTED


class FELProtocol:
    """Constantes y utilidades del protocolo FEL"""
    
    # Comandos FEL
    FEL_DEV_ID = 0x01010007
    FEL_VERSION = 0x01010001
    
    #魔法值 (Magic)
    FEL_MAGIC = 0x5F4C4547
    
    # Direcciones de memoria comunes
    DRAM_BASE_H3 = 0x40000000
    DRAM_BASE_H616 = 0x40000000
    DRAM_BASE_A64 = 0x40000000
    
    # Tamaños de chunks para escritura
    CHUNK_SIZE = 4 * 1024 * 1024  # 4MB


class FELRecovery:
    """
    Manejador de recuperación via FEL.
    
    Proceso de recuperación:
    1. Detectar dispositivo en modo FEL
    2. Identificar SOC y configuración de memoria
    3. Cargar bootloader (boot0) a RAM
    4. Ejecutar bootloader desde RAM (tiene driver eMMC)
    5. Escribir firmware a eMMC via bootloader
    """
    
    def __init__(self):
        self.device_info = FELDeviceInfo()
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_progress: Optional[Callable[[str, int], None]] = None
        self._cancelled = False
        
    def cancel(self):
        """Cancela la operación"""
        self._cancelled = True
        
    def _log(self, message: str):
        """Registra mensaje"""
        logger.info(message)
        if self.on_log:
            self.on_log(message)
            
    def _progress(self, step: str, percent: int):
        """Reporta progreso"""
        if self.on_progress:
            self.on_progress(step, percent)
            
    def check_connection(self) -> bool:
        """Verifica conexión FEL"""
        try:
            result = subprocess.run(
                ["sunxi-fel", "ver"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0 and "Allwinner" in result.stdout
        except:
            return False
            
    def detect_device(self) -> Optional[FELDeviceInfo]:
        """
        Detecta dispositivo FEL y obtiene información.
        
        Returns:
            FELDeviceInfo o None si no hay dispositivo
        """
        self._log("Detectando dispositivo FEL...")
        self._progress("Detectando FEL", 0)
        
        if not self.check_connection():
            self._log("No se detectó dispositivo FEL")
            self.device_info.state = FELState.DISCONNECTED
            return None
            
        try:
            result = subprocess.run(
                ["sunxi-fel", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self._parse_fel_output(result.stdout)
                self.device_info.state = FELState.CONNECTED
                self._log(f"✓ FEL conectado: {self.device_info.soc_type}")
                self._progress("FEL detectado", 100)
                return self.device_info
                
        except Exception as e:
            self._log(f"Error detectando: {e}")
            self.device_info.state = FELState.ERROR
            
        return None
        
    def _parse_fel_output(self, output: str):
        """Extrae información del output de sunxi-fel"""
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            
            if "Allwinner" in line:
                parts = line.split()
                if len(parts) >= 2:
                    self.device_info.fel_version = parts[2] if len(parts) > 2 else "unknown"
                    
            if "sun50i" in line.lower() or "h616" in line.lower() or "h313" in line.lower():
                self.device_info.soc_type = line.strip()
                
            if "0x1823" in line or "0x1610" in line:
                self.device_info.soc_id = line.strip()
                
    def reload_usb_driver(self) -> bool:
        """Recarga el driver USB de Allwinner"""
        self._log("Recargando driver USB...")
        
        try:
            subprocess.run(["sudo", "modprobe", "-r", "aw_usb"], timeout=5)
            time.sleep(1)
            result = subprocess.run(["sudo", "modprobe", "aw_usb"], timeout=5)
            
            if result.returncode == 0:
                self._log("✓ Driver USB recargado")
                time.sleep(2)
                return True
        except Exception as e:
            self._log(f"Error recargando driver: {e}")
            
        return False
        
    def reset_usb_port(self, port_path: str) -> bool:
        """Resetea un puerto USB específico via sysfs"""
        try:
            with open(f"{port_path}/unbind", "w") as f:
                f.write(port_path.split('/')[-1])
            time.sleep(1)
            
            with open(f"{port_path}/bind", "w") as f:
                f.write(port_path.split('/')[-1])
                
            time.sleep(2)
            return True
        except:
            return False
            
    def load_boot0_to_ram(self, boot0_path: str) -> Tuple[bool, str]:
        """
        Carga boot0 a la dirección de memoria base.
        
        Args:
            boot0_path: Ruta al archivo boot0
            
        Returns:
            Tuple de (éxito, mensaje)
        """
        if not os.path.exists(boot0_path):
            return False, f"Archivo no encontrado: {boot0_path}"
            
        self._log(f"Cargando boot0 a RAM: {boot0_path}")
        self._progress("Cargando boot0", 20)
        
        try:
            result = subprocess.run(
                ["sunxi-fel", "write", hex(self.device_info.dram_base), boot0_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                self._log("✓ boot0 cargado a RAM")
                self._progress("boot0 en RAM", 40)
                return True, "boot0 cargado exitosamente"
            else:
                return False, result.stderr
                
        except Exception as e:
            return False, str(e)
            
    def execute_boot0(self) -> Tuple[bool, str]:
        """
        Ejecuta boot0 desde RAM.
        
        Returns:
            Tuple de (éxito, mensaje)
        """
        self._log("Ejecutando boot0 desde RAM...")
        self._progress("Ejecutando boot0", 50)
        
        try:
            result = subprocess.run(
                ["sunxi-fel", "exec", hex(self.device_info.dram_base)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self._log("✓ boot0 ejecutándose")
                return True, "Boot0 ejecutado"
            else:
                return False, result.stderr
                
        except Exception as e:
            return False, str(e)
            
    def write_to_ram(self, file_path: str, address: int = None) -> Tuple[bool, str]:
        """
        Escribe archivo a RAM en chunks.
        
        Args:
            file_path: Ruta al archivo
            address: Dirección de memoria (default: DRAM_BASE)
            
        Returns:
            Tuple de (éxito, mensaje)
        """
        if address is None:
            address = self.device_info.dram_base
            
        if not os.path.exists(file_path):
            return False, f"Archivo no encontrado: {file_path}"
            
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        self._log(f"Escribiendo {file_size_mb:.2f} MB a RAM @ {hex(address)}")
        
        temp_chunks = []
        chunk_num = 0
        current_addr = address
        
        try:
            with open(file_path, "rb") as f:
                while True:
                    if self._cancelled:
                        return False, "Cancelado por usuario"
                        
                    chunk_data = f.read(FELProtocol.CHUNK_SIZE)
                    if not chunk_data:
                        break
                        
                    chunk_path = f"/tmp/fel_chunk_{chunk_num}.bin"
                    with open(chunk_path, "wb") as chunk_file:
                        chunk_file.write(chunk_data)
                    temp_chunks.append(chunk_path)
                    
                    self._log(f"Escribiendo chunk {chunk_num+1} @ {hex(current_addr)}")
                    
                    result = subprocess.run(
                        ["sunxi-fel", "write", hex(current_addr), chunk_path],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    if result.returncode != 0:
                        self._cleanup_chunks(temp_chunks)
                        return False, f"Error en chunk {chunk_num}: {result.stderr}"
                        
                    current_addr += len(chunk_data)
                    chunk_num += 1
                    
                    progress = int((chunk_num * FELProtocol.CHUNK_SIZE / file_size) * 100)
                    self._progress(f"Escribiendo {chunk_num} chunks...", progress)
                    
            self._cleanup_chunks(temp_chunks)
            self._log(f"✓ {chunk_num} chunks escritos a RAM")
            self._progress("Escritura a RAM completada", 100)
            
            return True, f"{chunk_num} chunks escritos"
            
        except Exception as e:
            self._cleanup_chunks(temp_chunks)
            return False, str(e)
            
    def write_to_ram_pipe(self, file_path: str, address: int = None) -> Tuple[bool, str]:
        """
        Escribe archivo a RAM usando método pipe (más rápido).
        
        Args:
            file_path: Ruta al archivo
            address: Dirección de memoria
            
        Returns:
            Tuple de (éxito, mensaje)
        """
        if address is None:
            address = self.device_info.dram_base
            
        if not os.path.exists(file_path):
            return False, f"Archivo no encontrado: {file_path}"
            
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        self._log(f"Metodo pipe: {file_size_mb:.2f} MB a {hex(address)}")
        
        try:
            with open(file_path, "rb") as f:
                chunk_num = 0
                current_addr = address
                bytes_written = 0
                
                while True:
                    if self._cancelled:
                        return False, "Cancelado"
                        
                    chunk = f.read(FELProtocol.CHUNK_SIZE)
                    if not chunk:
                        break
                        
                    chunk_path = f"/tmp/fel_pipe_chunk_{chunk_num}.bin"
                    with open(chunk_path, "wb") as cf:
                        cf.write(chunk)
                        
                    process = subprocess.Popen(
                        ["sunxi-fel", "write", hex(current_addr), chunk_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    stdout, stderr = process.communicate(timeout=60)
                    
                    if process.returncode != 0:
                        os.remove(chunk_path)
                        return False, f"Error chunk {chunk_num}"
                        
                    os.remove(chunk_path)
                    
                    current_addr += len(chunk)
                    bytes_written += len(chunk)
                    chunk_num += 1
                    
                    progress = int((bytes_written / file_size) * 100)
                    if chunk_num % 10 == 0:
                        self._log(f"Pipe: {chunk_num} chunks ({progress}%)")
                        self._progress(f"Escribiendo... {progress}%", progress)
                        
            self._log(f"✓ Pipe: {chunk_num} chunks completados")
            return True, "Pipe completado"
            
        except Exception as e:
            return False, str(e)
            
    def _cleanup_chunks(self, chunks: List[str]):
        """Limpia archivos temporales de chunks"""
        for chunk in chunks:
            try:
                if os.path.exists(chunk):
                    os.remove(chunk)
            except:
                pass
                
    def flash_firmware_via_loader(self, 
                                   loader_path: str,
                                   firmware_path: str) -> Tuple[bool, str]:
        """
        Flashea firmware usando un loader que tenga driver eMMC.
        
        Args:
            loader_path: Ruta al loader/boot0
            firmware_path: Ruta al firmware
            
        Returns:
            Tuple de (éxito, mensaje)
        """
        self._log("=== FLASHEO VIA LOADER ===")
        
        if not self.check_connection():
            return False, "No hay conexión FEL"
            
        self._progress("Iniciando flasheo", 10)
        
        success, msg = self.write_to_ram(firmware_path)
        if not success:
            return False, f"Error escribiendo firmware: {msg}"
            
        self._progress("Firmware en RAM", 30)
        
        if not os.path.exists(loader_path):
            return False, f"Loader no encontrado: {loader_path}"
            
        self._log("Cargando loader con driver eMMC...")
        success, msg = self.load_boot0_to_ram(loader_path)
        if not success:
            return False, f"Error cargando loader: {msg}"
            
        self._progress("Loader en RAM", 60)
        
        self._log("Ejecutando loader...")
        success, msg = self.execute_boot0()
        if not success:
            return False, f"Error ejecutando loader: {msg}"
            
        self._progress("Flasheando eMMC...", 80)
        
        self._log("Loader ejecutándose, firmware en RAM listo")
        self._log("El dispositivo debería iniciar el flasheo automáticamente")
        
        return True, "Firmware y loader cargados. Verificar serial console."
        
    def full_fel_recovery(self,
                         firmware_path: str,
                         boot0_path: Optional[str] = None,
                         method: str = "pipe") -> Tuple[bool, str]:
        """
        Recuperación completa via FEL.
        
        Args:
            firmware_path: Ruta al firmware
            boot0_path: Ruta al boot0 (opcional)
            method: Método de escritura ('pipe' o 'chunk')
            
        Returns:
            Tuple de (éxito, mensaje)
        """
        self._cancelled = False
        self._log("=== INICIANDO RECUPERACIÓN FEL ===")
        
        self._progress("Detectando dispositivo", 0)
        
        if not self.detect_device():
            return False, "No se detectó dispositivo FEL"
            
        self._progress("Dispositivo detectado", 20)
        
        if method == "pipe":
            success, msg = self.write_to_ram_pipe(firmware_path)
        else:
            success, msg = self.write_to_ram(firmware_path)
            
        if not success:
            return False, f"Error escribiendo firmware: {msg}"
            
        self._progress("Firmware en RAM", 70)
        
        if boot0_path:
            self._log("Cargando bootloader...")
            success, msg = self.load_boot0_to_ram(boot0_path)
            if success:
                self._progress("Loader en RAM", 90)
                self.execute_boot0()
                
        self._progress("Completado", 100)
        self._log("=== RECUPERACIÓN FEL COMPLETADA ===")
        self._log("Firmware escrito a RAM. Usar serial para escribir a eMMC.")
        
        return True, "Firmware en RAM listo para flasheo"


class FELBootloader:
    """Gestor de bootloaders para FEL"""
    
    COMMON_BOOTLOADERS = {
        "h616": {
            "base": 0x40000000,
            "spl": "/usr/local/share/sunxi-fel/h616/sp-boot0.bin",
            "description": "H616/H313 Boot0"
        },
        "h3": {
            "base": 0x40000000,
            "spl": "/usr/local/share/sunxi-fel/h3/sunxi-pack_h3.bin",
            "description": "H3 Boot0"
        },
        "a64": {
            "base": 0x40000000,
            "spl": "/usr/local/share/sunxi-fel/a64/pine64-pack.bin",
            "description": "A64 Boot0"
        }
    }
    
    def find_bootloader(self, soc_type: str) -> Optional[Dict]:
        """Busca bootloader para SOC"""
        soc_lower = soc_type.lower()
        
        for key, bootloader in self.COMMON_BOOTLOADERS.items():
            if key in soc_lower:
                if os.path.exists(bootloader["spl"]):
                    return bootloader
                    
        return None
        
    def list_available_bootloaders(self) -> List[Dict]:
        """Lista bootloaders disponibles"""
        available = []
        
        for key, bl in self.COMMON_BOOTLOADERS.items():
            bl_copy = bl.copy()
            bl_copy["key"] = key
            bl_copy["exists"] = os.path.exists(bl["spl"])
            available.append(bl_copy)
            
        return available

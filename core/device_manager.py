"""
Device Manager - Detección y gestión de dispositivos Allwinner
"""

import subprocess
import time
import threading
from typing import Optional, Callable, Dict, List, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DeviceState(Enum):
    """Estados del dispositivo"""
    DISCONNECTED = "disconnected"
    FEL_MODE = "fel_mode"
    SERIAL_ONLY = "serial_only"
    BOOTING = "booting"
    ANDROID = "android"
    RECOVERY = "recovery"
    UNKNOWN = "unknown"


@dataclass
class DeviceInfo:
    """Información del dispositivo"""
    bus: str
    device_num: str
    vendor_id: str
    product_id: str
    description: str
    state: DeviceState
    soc_type: str = ""
    soc_id: str = ""
    fel_version: str = ""
    scratchpad: str = ""
    dram_size: str = ""
    emmc_size: str = ""
    bootlog: str = ""


class DeviceManager:
    """
    Gestor de dispositivos Allwinner.
    Detecta automáticamente dispositivos en modo FEL y serial.
    """
    
    VENDOR_ID = "1f3a"
    PRODUCT_ID_FEL = "efe8"
    
    def __init__(self, on_device_change: Optional[Callable] = None):
        self.on_device_change = on_device_change
        self.current_device: Optional[DeviceInfo] = None
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self._fel_available = True
        
    def check_fel_availability(self) -> bool:
        """Verifica si sunxi-fel está disponible"""
        try:
            result = subprocess.run(
                ["which", "sunxi-fel"],
                capture_output=True,
                text=True
            )
            self._fel_available = result.returncode == 0
            return self._fel_available
        except Exception as e:
            logger.error(f"Error checking sunxi-fel: {e}")
            return False
    
    def detect_devices(self) -> List[DeviceInfo]:
        """Detecta todos los dispositivos Allwinner conectados"""
        devices = []
        
        try:
            # Detectar via lsusb
            result = subprocess.run(
                ["lsusb", "-d", self.VENDOR_ID],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                    
                parts = line.split()
                if len(parts) >= 6:
                    bus = parts[1]
                    device_num = parts[3].strip(":")
                    ids = parts[5].split(":")
                    vendor_id = ids[0]
                    product_id = ids[1]
                    
                    device = DeviceInfo(
                        bus=bus,
                        device_num=device_num,
                        vendor_id=vendor_id,
                        product_id=product_id,
                        description=" ".join(parts[6:]),
                        state=DeviceState.FEL_MODE if product_id == self.PRODUCT_ID_FEL else DeviceState.UNKNOWN
                    )
                    devices.append(device)
                    
        except Exception as e:
            logger.error(f"Error detecting devices: {e}")
            
        return devices
    
    def get_device_info(self) -> Optional[DeviceInfo]:
        """Obtiene información detallada del dispositivo FEL"""
        if not self.check_fel_availability():
            return None
            
        try:
            result = subprocess.run(
                ["sg", "sunxi-fel", "-c", "sunxi-fel ver"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            output = result.stdout + result.stderr
            
            if "AWUSBFEX" in output:
                # Parsear información
                device = DeviceInfo(
                    bus="",
                    device_num="",
                    vendor_id=self.VENDOR_ID,
                    product_id=self.PRODUCT_ID_FEL,
                    description="Allwinner FEL Device",
                    state=DeviceState.FEL_MODE
                )
                
                # Extraer SOC
                soc_line = [l for l in output.split("\n") if "soc=" in l]
                if soc_line:
                    soc_parts = soc_line[0].split("soc=")[1].split()[0].split("(")
                    device.soc_id = soc_parts[0]
                    device.soc_type = soc_parts[1].rstrip(")") if len(soc_parts) > 1 else "unknown"
                    
                # Extraer versión
                ver_line = [l for l in output.split("\n") if "ver=" in l]
                if ver_line:
                    device.fel_version = ver_line[0].split("ver=")[1].split()[0]
                    
                # Extraer scratchpad
                scratch_line = [l for l in output.split("\n") if "scratchpad=" in l]
                if scratch_line:
                    device.scratchpad = scratch_line[0].split("scratchpad=")[1].split()[0]
                    
                self.current_device = device
                return device
                
        except subprocess.TimeoutExpired:
            logger.warning("FEL command timed out")
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            
        return None
    
    def start_monitoring(self, interval: float = 2.0):
        """Inicia monitoreo de dispositivos"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("Device monitoring started")
        
    def stop_monitoring(self):
        """Detiene monitoreo de dispositivos"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Device monitoring stopped")
        
    def _monitor_loop(self, interval: float):
        """Loop de monitoreo"""
        last_state = None
        
        while self.monitoring:
            try:
                devices = self.detect_devices()
                current_state = DeviceState.FEL_MODE if devices else DeviceState.DISCONNECTED
                
                if current_state != last_state:
                    if self.on_device_change:
                        self.on_device_change(current_state, devices)
                    last_state = current_state
                    
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                
            time.sleep(interval)
    
    def reload_usb_driver(self) -> bool:
        """Recarga el driver awusb"""
        try:
            subprocess.run(["sudo", "modprobe", "-r", "awusb"], check=True)
            time.sleep(1)
            subprocess.run(["sudo", "modprobe", "awusb"], check=True)
            time.sleep(2)
            logger.info("USB driver reloaded")
            return True
        except Exception as e:
            logger.error(f"Error reloading driver: {e}")
            return False
            
    def reset_usb_device(self, bus: str, port: str) -> bool:
        """Resetea un dispositivo USB específico"""
        try:
            device_path = f"{bus}-{port}"
            subprocess.run(
                ["sudo", "bash", "-c", f'echo "{device_path}" > /sys/bus/usb/drivers/usb/unbind'],
                check=True
            )
            time.sleep(1)
            subprocess.run(
                ["sudo", "bash", "-c", f'echo "{device_path}" > /sys/bus/usb/drivers/usb/bind'],
                check=True
            )
            time.sleep(2)
            logger.info(f"USB device {device_path} reset")
            return True
        except Exception as e:
            logger.error(f"Error resetting USB device: {e}")
            return False

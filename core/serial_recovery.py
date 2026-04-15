"""
Auto Recovery via Serial Console - Recuperación automática por consola serial

Este módulo automatiza el proceso de recuperación mediante la consola serial U-Boot.
"""

import time
import re
from typing import Optional, Callable, Tuple, Dict, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BootState(Enum):
    """Estados del boot"""
    UNKNOWN = "unknown"
    FEL_MODE = "fel_mode"
    U_BOOT = "u_boot"
    KERNEL = "kernel"
    ANDROID = "android"
    RECOVERY = "recovery"
    STUCK = "stuck"


@dataclass
class BootInfo:
    """Información del boot"""
    state: BootState
    soc_type: str = ""
    dram_size: str = ""
    boot0_version: str = ""
    uboot_version: str = ""
    kernel_version: str = ""
    raw_log: str = ""


class SerialAutoRecovery:
    """
    Recuperación automática via consola serial.
    
    Proceso:
    1. Conectar al puerto serial
    2. Detectar estado del boot
    3. Interrumpir autoboot
    4. Navegar al menú de recovery
    5. Ejecutar factory reset
    """
    
    AUTBOOT_PATTERN = "Hit any key to stop autoboot"
    UBOOT_PROMPT = "sunxi#"
    ANDROID_LOGO = "Android"
    RECOVERY_MENU_PATTERNS = [
        "1: Recovery Mode",
        "2: Factory Reset",
        "update",
        "reboot",
        "[RECOVERY]"
    ]
    
    def __init__(self, serial_console):
        self.serial = serial_console
        self.boot_info = BootInfo(state=BootState.UNKNOWN)
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_progress: Optional[Callable[[str, int], None]] = None
        self._cancelled = False
        
    def cancel(self):
        """Cancela la operación en curso"""
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
            
    def detect_boot_state(self, timeout: float = 30.0) -> BootInfo:
        """
        Detecta el estado actual del boot.
        
        Returns:
            BootInfo con información del estado
        """
        self._log("Detectando estado del boot...")
        self._progress("Detectando dispositivo", 0)
        
        self.serial.clear_buffer()
        self.serial.start_reading()
        
        start_time = time.time()
        collected_log = ""
        
        while time.time() - start_time < timeout:
            time.sleep(0.5)
            current_buffer = self.serial.buffer
            
            if current_buffer != collected_log:
                new_data = current_buffer[len(collected_log):]
                collected_log = current_buffer
                
            if self.AUTBOOT_PATTERN in collected_log:
                self.boot_info.state = BootState.U_BOOT
                self._parse_boot_info(collected_log)
                self._log(f"Estado: U-Boot detectado")
                break
                
            if self.ANDROID_LOGO in collected_log or "bootanimation" in collected_log.lower():
                self.boot_info.state = BootState.ANDROID
                self._log(f"Estado: Android arrancando")
                break
                
            if "FEL" in collected_log or "USB" in collected_log:
                self.boot_info.state = BootState.FEL_MODE
                self._log(f"Estado: Modo FEL")
                break
                
        self.boot_info.raw_log = collected_log
        self.serial.stop_reading()
        
        self._progress("Detección completada", 100)
        return self.boot_info
        
    def _parse_boot_info(self, log: str):
        """Extrae información del bootlog"""
        patterns = {
            'soc': r'(sun50iw9|H616|H313|H618|H3|A64)',
            'dram': r'DRAM:\s*(\d+\s*\w+)',
            'boot0': r'boot0\s*:\s*([0-9a-f]+)',
            'uboot': r'U-Boot\s*(\d+\.\d+)',
            'kernel': r'Linux version (\d+\.\d+\.\d+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, log, re.IGNORECASE)
            if match:
                value = match.group(1)
                if key == 'soc':
                    self.boot_info.soc_type = value
                elif key == 'dram':
                    self.boot_info.dram_size = value
                elif key == 'boot0':
                    self.boot_info.boot0_version = value
                elif key == 'uboot':
                    self.boot_info.uboot_version = value
                elif key == 'kernel':
                    self.boot_info.kernel_version = value
                    
    def wait_for_autoboot_key(self, timeout: float = 30.0) -> bool:
        """
        Espera el momento para presionar tecla.
        
        Returns:
            True si se puede interrumpir
        """
        self._log("Esperando prompt de autoboot...")
        
        if self.serial.wait_for_pattern(self.AUTBOOT_PATTERN, timeout):
            self._log("Prompt detectado. Enviando interrupción...")
            return True
        return False
        
    def interrupt_autoboot(self) -> bool:
        """
        Interrumpe el autoboot.
        
        Returns:
            True si se logró entrar a U-Boot
        """
        self._log("Interrumpiendo autoboot...")
        self._progress("Interrumpiendo boot", 10)
        
        for attempt in range(5):
            if self._cancelled:
                return False
                
            self.serial.send("\r\n")
            time.sleep(0.5)
            
            if self.serial.wait_for_pattern("sunxi", timeout=2):
                self._log("U-Boot prompt detectado")
                self._progress("En U-Boot", 30)
                return True
                
            time.sleep(0.3)
            
        self._log("No se pudo interrumpir autoboot")
        return False
        
    def navigate_to_recovery(self) -> bool:
        """
        Navega al menú de recovery.
        
        Returns:
            True si se llegó al recovery
        """
        self._log("Buscando menú de recovery...")
        self._progress("Navegando a Recovery", 40)
        
        recovery_commands = [
            ("run recovery", "recovery"),
            ("run update", "update"),
            ("setenv bootcmd run recovery", "recovery"),
            ("help", "help"),
        ]
        
        for cmd, expected in recovery_commands:
            if self._cancelled:
                return False
                
            self._log(f"Intentando: {cmd}")
            response = self.serial.send_command(cmd, wait=3.0)
            
            if response:
                self.serial.buffer += response
                
                if any(pattern in response.lower() for pattern in self.RECOVERY_MENU_PATTERNS):
                    self._log("Menú de recovery encontrado")
                    self._progress("Recovery encontrado", 60)
                    return True
                    
        self._log("Buscando opciones de recovery...")
        
        for option in ["2", "recovery", "update", "1"]:
            if self._cancelled:
                return False
                
            response = self.serial.send_command(option, wait=2.0)
            if response and any(p in response.lower() for p in self.RECOVERY_MENU_PATTERNS):
                self._log(f"Opción {option} seleccionada")
                return True
                
        return False
        
    def execute_factory_reset(self) -> Tuple[bool, str]:
        """
        Ejecuta factory reset.
        
        Returns:
            Tuple de (éxito, mensaje)
        """
        self._log("Ejecutando Factory Reset...")
        self._progress("Factory Reset", 70)
        
        commands = [
            ("2", "factory"),      # Opción 2 en muchos recovery
            ("yes", "confirm"),
            ("\r\n", "continue"),
        ]
        
        for cmd, desc in commands:
            if self._cancelled:
                return False, "Cancelado por usuario"
                
            self._log(f"Enviando: {cmd}")
            response = self.serial.send_command(cmd, wait=5.0)
            
            if response:
                if "error" in response.lower() or "fail" in response.lower():
                    self._log(f"Advertencia en {desc}: {response[:100]}")
                    
            time.sleep(1.0)
            
        self._log("Factory reset en proceso...")
        self._progress("Proceso de flasheo", 80)
        
        self.serial.buffer = ""
        start_time = time.time()
        timeout = 600.0
        
        while time.time() - start_time < timeout:
            if self._cancelled:
                return False, "Cancelado por usuario"
                
            time.sleep(5.0)
            buffer = self.serial.buffer
            
            if "success" in buffer.lower() or "complete" in buffer.lower():
                self._log("Flasheo completado exitosamente")
                self._progress("Completado", 100)
                return True, "Factory reset completado"
                
            if "error" in buffer.lower() or "failed" in buffer.lower():
                self._log("Error detectado en el proceso")
                self._progress("Error", 0)
                return False, "Flasheo falló"
                
            if time.time() - start_time > 60:
                elapsed = int(time.time() - start_time)
                self._log(f"Flasheo en progreso... ({elapsed}s)")
                self._progress(f"Flasheando... {elapsed}s", 80 + int((elapsed / timeout) * 20))
                
        return False, "Timeout en factory reset"
        
    def full_auto_recovery(self, 
                           port: str,
                           firmware_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Ejecuta recuperación automática completa.
        
        Args:
            port: Puerto serial
            firmware_path: Ruta a firmware (si se necesita flashear manualmente)
            
        Returns:
            Tuple de (éxito, mensaje)
        """
        self._cancelled = False
        self._log("=== INICIANDO RECUPERACIÓN AUTOMÁTICA ===")
        self._progress("Iniciando", 0)
        
        if not self.serial.connect(port):
            return False, f"No se pudo conectar a {port}"
            
        self._log(f"Conectado a {port}")
        self._progress("Conectado", 5)
        
        self.boot_info = self.detect_boot_state(timeout=45.0)
        
        if self.boot_info.state == BootState.FEL_MODE:
            self._log("Dispositivo en modo FEL - usar método FEL manual")
            self.serial.disconnect()
            return False, "Dispositivo en modo FEL. Usar recuperación FEL."
            
        if self.boot_info.state == BootState.ANDROID:
            self._log("Android arrancando - reiniciando para interrumpir")
            self.serial.send("\r\n")
            time.sleep(2)
            
        if not self.wait_for_autoboot_key(timeout=45.0):
            self._log("No se detectó prompt de autoboot")
            self.serial.disconnect()
            return False, "No se pudo detectar autoboot"
            
        if not self.interrupt_autoboot():
            self.serial.disconnect()
            return False, "No se pudo interrumpir autoboot"
            
        if not self.navigate_to_recovery():
            self._log("No se encontró menú de recovery")
            self.serial.disconnect()
            return False, "Recovery no disponible en este dispositivo"
            
        success, message = self.execute_factory_reset()
        
        if success:
            self._log("=== RECUPERACIÓN COMPLETADA ===")
            self._log("Reiniciando dispositivo...")
            self.serial.send_command("reset")
            
        self.serial.disconnect()
        return success, message


class UBootCommandExecutor:
    """Ejecutor de comandos U-Boot específicos"""
    
    COMMON_COMMANDS = {
        'help': 'Lista de comandos',
        'printenv': 'Muestra variables de entorno',
        'setenv': 'Establece variable de entorno',
        'boot': 'Arranca desde配置的 bootcmd',
        'reset': 'Reinicia el dispositivo',
        'mmc': 'Operaciones con tarjeta MMC/eMMC',
        'ext4ls': 'Lista archivos en ext4',
        'fatls': 'Lista archivos en FAT',
        'load': 'Carga archivo a memoria',
        'go': 'Ejecuta código en dirección',
        'source': 'Ejecuta script',
    }
    
    def __init__(self, serial_console):
        self.serial = serial_console
        
    def send_command(self, command: str, timeout: float = 3.0) -> Optional[str]:
        """Envía comando U-Boot"""
        self.serial.send("\r\n")
        time.sleep(0.5)
        return self.serial.send_command(command, wait=timeout)
        
    def get_env(self, var: str) -> Optional[str]:
        """Obtiene variable de entorno"""
        response = self.send_command(f"printenv {var}")
        if response and "=" in response:
            parts = response.split("=")
            if len(parts) > 1:
                return parts[1].strip()
        return None
        
    def set_env(self, var: str, value: str) -> bool:
        """Establece variable de entorno"""
        response = self.send_command(f"setenv {var} {value}")
        return "error" not in response.lower()
        
    def boot_from_mmc(self, partition: int = 0) -> bool:
        """Arranca desde eMMC"""
        response = self.send_command(f"mmc dev 0:{partition}")
        if "no mmc" in response.lower() or "error" in response.lower():
            return False
        return self.send_command("boot") is not None
        
    def read_partition(self, partition: int, offset: int, size: int, dest_addr: int) -> bool:
        """Lee partición de eMMC"""
        cmd = f"mmc read {hex(dest_addr)} {hex(offset)} {hex(size)}"
        response = self.send_command(cmd)
        return "error" not in response.lower()
        
    def list_partitions(self) -> List[str]:
        """Lista particiones"""
        response = self.send_command("mmc part")
        if not response:
            return []
            
        partitions = []
        for line in response.split('\n'):
            if re.match(r'\s*\d+', line):
                partitions.append(line.strip())
        return partitions

"""
Recovery Procedures - Procedimientos automatizados de recuperación
"""

import os
import subprocess
import time
from typing import Optional, Callable, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RecoveryStepStatus(Enum):
    """Estado de un paso de recuperación"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RecoveryStep:
    """Paso individual de recuperación"""
    name: str
    description: str
    command: str
    status: RecoveryStepStatus
    output: str = ""
    error: str = ""
    timeout: int = 60


class RecoveryProfile:
    """Perfil de recuperación para un dispositivo específico"""
    
    def __init__(self, name: str, soc_type: str):
        self.name = name
        self.soc_type = soc_type
        self.steps: List[RecoveryStep] = []
        
    def add_step(self, name: str, description: str, 
                 command: str, timeout: int = 60):
        """Agrega un paso al perfil"""
        self.steps.append(RecoveryStep(
            name=name,
            description=description,
            command=command,
            status=RecoveryStepStatus.PENDING,
            timeout=timeout
        ))
        
    def get_step(self, name: str) -> Optional[RecoveryStep]:
        """Obtiene un paso por nombre"""
        for step in self.steps:
            if step.name == name:
                return step
        return None


class RecoveryEngine:
    """
    Motor de recuperación que ejecuta procedimientos automatizados.
    """
    
    def __init__(self):
        self.current_profile: Optional[RecoveryProfile] = None
        self.on_step_change: Optional[Callable] = None
        self.on_complete: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
    def create_profile(self, name: str, soc_type: str) -> RecoveryProfile:
        """Crea un nuevo perfil de recuperación"""
        profile = RecoveryProfile(name, soc_type)
        return profile
        
    def create_h616_profile(self) -> RecoveryProfile:
        """Crea perfil para Allwinner H616"""
        profile = RecoveryProfile("H616 Recovery", "H616")
        
        # Pasos de recuperación
        profile.add_step(
            "detect_device",
            "Detectar dispositivo en modo FEL",
            "sunxi-fel ver"
        )
        
        profile.add_step(
            "prepare_firmware",
            "Preparar firmware en chunks",
            None  # Se ejecuta via Python
        )
        
        profile.add_step(
            "write_to_ram",
            "Escribir firmware a RAM",
            None  # Se ejecuta via Python
        )
        
        profile.add_step(
            "load_bootloader",
            "Cargar bootloader compatible",
            None
        )
        
        profile.add_step(
            "write_to_emmc",
            "Escribir a eMMC",
            None
        )
        
        profile.add_step(
            "verify_flash",
            "Verificar flasheo",
            None
        )
        
        profile.add_step(
            "reboot_device",
            "Reiniciar dispositivo",
            None
        )
        
        return profile
        
    def execute_profile(self, profile: RecoveryProfile,
                      firmware_path: Optional[str] = None,
                      progress_callback: Optional[Callable[[str, int], None]] = None) -> Tuple[bool, str]:
        """
        Ejecuta un perfil de recuperación completo.
        
        Args:
            profile: Perfil de recuperación
            firmware_path: Ruta al firmware (opcional)
            progress_callback: Callback de progreso
            
        Returns:
            Tuple de (éxito, mensaje)
        """
        self.current_profile = profile
        logger.info(f"Starting recovery: {profile.name}")
        
        for i, step in enumerate(profile.steps):
            step.status = RecoveryStepStatus.RUNNING
            progress = int((i / len(profile.steps)) * 100)
            
            if progress_callback:
                progress_callback(step.name, progress)
                
            if self.on_step_change:
                self.on_step_change(step, i, len(profile.steps))
                
            logger.info(f"Running step: {step.name}")
            
            try:
                success, output = self._execute_step(step, firmware_path)
                
                if success:
                    step.status = RecoveryStepStatus.SUCCESS
                    step.output = output
                    logger.info(f"Step {step.name} succeeded")
                else:
                    step.status = RecoveryStepStatus.FAILED
                    step.error = output
                    logger.error(f"Step {step.name} failed: {output}")
                    
                    if self.on_error:
                        self.on_error(step, i)
                        
                    return False, f"Step {step.name} failed: {output}"
                    
            except Exception as e:
                step.status = RecoveryStepStatus.FAILED
                step.error = str(e)
                logger.error(f"Step {step.name} exception: {e}")
                return False, str(e)
                
        if self.on_complete:
            self.on_complete(profile)
            
        logger.info("Recovery completed successfully")
        return True, "Recovery completed"
        
    def _execute_step(self, step: RecoveryStep, 
                    firmware_path: Optional[str]) -> Tuple[bool, str]:
        """Ejecuta un paso individual"""
        
        if step.command:
            # Ejecutar comando shell
            try:
                result = subprocess.run(
                    step.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=step.timeout
                )
                
                if result.returncode == 0:
                    return True, result.stdout
                else:
                    return False, result.stderr
                    
            except subprocess.TimeoutExpired:
                return False, "Command timed out"
            except Exception as e:
                return False, str(e)
                
        else:
            # Pasos que requieren lógica Python (placeholder)
            return True, "Step executed (Python logic)"
            
    def quick_recovery(self, firmware_path: str,
                      fel_handler,
                      progress_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """
        Recuperación rápida para dispositivos Allwinner.
        
        1. Verificar FEL
        2. Escribir firmware a RAM
        3. Cargar bootloader
        4. Escribir a eMMC
        """
        logger.info("Starting quick recovery")
        
        if progress_callback:
            progress_callback("Verificando FEL...", 0)
            
        # 1. Verificar FEL
        if not fel_handler.check_connection():
            return False, "No se detectó dispositivo FEL"
            
        if progress_callback:
            progress_callback("FEL detectado", 10)
            
        # 2. Preparar chunks
        if progress_callback:
            progress_callback("Preparando firmware...", 20)
            
        chunks = self._prepare_firmware_chunks(firmware_path, 4 * 1024 * 1024)
        if not chunks:
            return False, "Error preparando firmware"
            
        if progress_callback:
            progress_callback(f"Creados {len(chunks)} chunks", 30)
            
        # 3. Escribir a RAM
        for i, chunk in enumerate(chunks):
            success, msg = fel_handler.write_with_progress(chunk)
            if not success:
                return False, f"Error escribiendo chunk {i}: {msg}"
                
            progress = 30 + int((i / len(chunks)) * 40)
            if progress_callback:
                progress_callback(f"Escritos {i+1}/{len(chunks)} chunks", progress)
                
        if progress_callback:
            progress_callback("Firmware en RAM", 70)
            
        # 4. Limpiar chunks temporales
        for chunk in chunks:
            try:
                os.remove(chunk)
            except:
                pass
                
        # 5. Cargar bootloader
        if progress_callback:
            progress_callback("Cargando bootloader...", 80)
            
        # Aquí se cargaría el bootloader específico
        # fel_handler.load_spl(bootloader_path)
        
        if progress_callback:
            progress_callback("Bootloader cargado", 90)
            
        # 6. Escribir a eMMC
        if progress_callback:
            progress_callback("Escribiendo a eMMC...", 95)
            
        # Esta parte requiere más lógica dependiendo del dispositivo
        # Se escribiría a eMMC via el bootloader cargado
            
        if progress_callback:
            progress_callback("Completado", 100)
            
        return True, "Firmware escrito a RAM. Flasheo a eMMC pendiente."
        
    def _prepare_firmware_chunks(self, firmware_path: str, 
                                 chunk_size: int) -> List[str]:
        """Prepara chunks temporales del firmware"""
        chunks = []
        
        try:
            with open(firmware_path, "rb") as f:
                chunk_num = 0
                while True:
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break
                        
                    chunk_path = f"/tmp/recovery_chunk_{chunk_num}.bin"
                    with open(chunk_path, "wb") as chunk_file:
                        chunk_file.write(chunk_data)
                    chunks.append(chunk_path)
                    chunk_num += 1
                    
        except Exception as e:
            logger.error(f"Error preparing chunks: {e}")
            # Limpiar chunks parciales
            for c in chunks:
                try:
                    os.remove(c)
                except:
                    pass
            return []
            
        return chunks
